"""
Free B2B prospection scraper for Portech — Yellow Pages Canada + OSM hybrid.

Pipeline:
1. Search Yellow Pages Canada (yellowpages.ca) by category + city. YP embeds
   business data as JSON-LD, which is reliable and contains name + address +
   permanent listing URL.
2. Visit each listing page to scrape phone + website + email when available.
3. If a website is listed, crawl 3-5 well-known contact paths for emails
   (decode obfuscated `info [at] domain.com` patterns).
4. Optional OSM (Overpass) fallback for businesses not on YP.

Everything is 100% free — no API keys.
"""
import asyncio
import json
import logging
import re
from html import unescape
from typing import List, Optional
from urllib.parse import quote_plus, urljoin, urlparse

import httpx

logger = logging.getLogger("portech.prospection")

YP_BASE = "https://www.yellowpages.ca"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------
REGIONS = {
    "montreal":  {"south": 45.41, "west": -73.97, "north": 45.71, "east": -73.47, "label": "Grand Montréal", "yp_city": "Montreal+QC"},
    "laval":     {"south": 45.51, "west": -73.91, "north": 45.71, "east": -73.59, "label": "Laval", "yp_city": "Laval+QC"},
    "rive-sud":  {"south": 45.39, "west": -73.66, "north": 45.59, "east": -73.31, "label": "Rive-Sud", "yp_city": "Longueuil+QC"},
    "rive-nord": {"south": 45.59, "west": -74.10, "north": 45.95, "east": -73.41, "label": "Rive-Nord", "yp_city": "Saint-Jerome+QC"},
}

# ---------------------------------------------------------------------------
# Categories — each maps to YP search keywords + Overpass tags
# ---------------------------------------------------------------------------
CATEGORIES = {
    "vitrerie": {
        "label": "Vitreries",
        "yp_keywords": ["vitrerie", "glaziers"],
        "osm_tags": [('shop', 'glaziery'), ('craft', 'glaziery'), ('name', 'vitrerie', True)],
    },
    "entrepreneur": {
        "label": "Entrepreneurs généraux",
        "yp_keywords": ["entrepreneur+general", "general+contractor"],
        "osm_tags": [('office', 'construction_company'), ('craft', 'general_contractor'), ('craft', 'carpenter')],
    },
    "architecte": {
        "label": "Architectes",
        "yp_keywords": ["architecte", "architects"],
        "osm_tags": [('office', 'architect')],
    },
    "designer": {
        "label": "Designers d'intérieur",
        "yp_keywords": ["designer+interieur", "interior+designers"],
        "osm_tags": [('office', 'interior_design'), ('shop', 'interior_decoration')],
    },
    "promoteur": {
        "label": "Constructeurs / promoteurs",
        "yp_keywords": ["promoteur+immobilier", "construction"],
        "osm_tags": [('office', 'estate_agent'), ('office', 'developer')],
    },
    "commercial": {
        "label": "Centres d'achats & bâtiments commerciaux",
        "yp_keywords": ["centre+commercial", "shopping+centres"],
        "osm_tags": [('shop', 'mall')],
    },
}

# ---------------------------------------------------------------------------
# Email + helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
OBFUSCATED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*(?:\[at\]|\(at\)|\s+at\s+|\{at\})\s*([a-zA-Z0-9.\-]+)\s*(?:\[dot\]|\(dot\)|\s+dot\s+|\{dot\}|\.)\s*([a-zA-Z]{2,})",
    re.IGNORECASE,
)
JUNK_SUFFIXES = (
    "wixpress", "wix.com", "godaddy", "example", "noreply",
    "no-reply", "donotreply", "domain.com", "test.com", "yourdomain",
    "yourcompany", "yourwebsite", "name.com", "yp.ca", "yellowpages",
    "exemple", "youremail", "sentry",
)

CONTACT_PATHS = [
    "", "/contact", "/contact-us", "/contactez-nous", "/nous-joindre",
    "/about", "/a-propos",
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
}


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _is_junk_email(addr: str) -> bool:
    a = addr.lower()
    return any(j in a for j in JUNK_SUFFIXES)


def _score_email(addr: str) -> int:
    local = addr.split("@", 1)[0].lower()
    for i, pref in enumerate(["info", "contact", "bonjour", "hello", "ventes",
                              "sales", "service", "admin", "office"]):
        if local.startswith(pref):
            return i
    return 100


def _extract_emails_from_html(html: str, prefer_domain: Optional[str] = None) -> List[str]:
    html = unescape(html)
    found = set()
    for m in re.finditer(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', html, re.IGNORECASE):
        found.add(m.group(1).lower())
    for m in EMAIL_RE.finditer(html):
        found.add(m.group(0).lower())
    for m in OBFUSCATED_RE.finditer(html):
        found.add(f"{m.group(1)}@{m.group(2)}.{m.group(3)}".lower())
    clean = [a for a in found if not _is_junk_email(a) and len(a) < 60]
    if prefer_domain:
        domain_root = prefer_domain.split(".")[0]
        clean.sort(key=lambda a: (0 if domain_root in a else 1, _score_email(a)))
    else:
        clean.sort(key=_score_email)
    return clean


# ---------------------------------------------------------------------------
# Yellow Pages Canada scraper
# ---------------------------------------------------------------------------
async def _yp_search_listings(
    client: httpx.AsyncClient,
    keyword: str,
    yp_city: str,
    page: int = 1,
) -> List[dict]:
    """Return raw business stubs from a YP search results page (JSON-LD)."""
    url = f"{YP_BASE}/search/si/{page}/{quote_plus(keyword)}/{yp_city}"
    try:
        r = await client.get(url, headers=BROWSER_HEADERS, timeout=15.0)
    except Exception as exc:
        logger.warning("YP search HTTP error: %s", exc)
        return []
    if r.status_code != 200:
        return []
    html = r.text
    listings: List[dict] = []
    # JSON-LD blocks — YP wraps everything in @graph
    for jsonld_match in re.finditer(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    ):
        try:
            data = json.loads(jsonld_match.group(1).strip())
        except Exception:
            continue
        nodes = []
        if isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                nodes = graph
            else:
                nodes = [data]
        elif isinstance(data, list):
            nodes = data
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = node.get("@type") or ""
            # Normalize @type which may be a list or contain a URI
            type_str = " ".join(node_type) if isinstance(node_type, list) else str(node_type)
            if "ItemList" not in type_str:
                continue
            for el in node.get("itemListElement", []):
                item = el.get("item") or {}
                item_type = item.get("@type") or ""
                item_type_str = " ".join(item_type) if isinstance(item_type, list) else str(item_type)
                if "LocalBusiness" not in item_type_str:
                    continue
                addr = item.get("address") or {}
                geo = item.get("geo") or {}
                listings.append({
                    "name": item.get("name"),
                    "yp_url": item.get("url"),
                    "address": addr.get("streetAddress"),
                    "city": addr.get("addressLocality"),
                    "postal_code": addr.get("postalCode"),
                    "lat": geo.get("latitude"),
                    "lon": geo.get("longitude"),
                })
    # Dedupe by yp_url
    seen = set()
    out = []
    for stub in listings:
        u = stub.get("yp_url")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        if stub.get("name"):
            out.append(stub)
    return out


async def _yp_fetch_details(client: httpx.AsyncClient, listing: dict) -> dict:
    """Visit a YP listing page to grab phone + website + email."""
    url = listing.get("yp_url")
    if not url:
        return listing
    try:
        r = await client.get(url, headers=BROWSER_HEADERS, timeout=15.0)
    except Exception as exc:
        logger.debug("YP details fetch failed: %s", exc)
        return listing
    if r.status_code != 200:
        return listing
    html = r.text
    # Phone — look for tel: link first, then xx-xxx-xxxx patterns
    m = re.search(r'href="tel:\+?([0-9\-\s().]+)"', html)
    if m:
        listing["phone"] = m.group(1).strip()
    else:
        m = re.search(r'<span[^>]+class="[^"]*phone[^"]*"[^>]*>\s*([0-9().\s\-]+?)\s*</span>', html)
        if m:
            listing["phone"] = m.group(1).strip()
    # Website — YP wraps external sites in /redirect?... or stores them in data-url
    m = re.search(r'href="(?:[^"]*[?&])?(?:redirect|url)=([^"&]+)"', html)
    if m:
        from urllib.parse import unquote
        listing["website"] = unquote(m.group(1))
    if not listing.get("website"):
        # Try inline JSON or schema.org URL property (but exclude YP's own URL)
        for em in re.finditer(r'"url"\s*:\s*"(https?://[^"]+)"', html):
            url_candidate = em.group(1)
            if "yellowpages" not in url_candidate and "yp.ca" not in url_candidate:
                listing["website"] = url_candidate
                break
    # Email — direct mailto on YP page (rare but happens)
    emails = _extract_emails_from_html(html)
    if emails:
        listing["email"] = emails[0]
    return listing


async def _crawl_website_for_contact(
    client: httpx.AsyncClient,
    base_url: str,
) -> tuple[Optional[str], Optional[str]]:
    """Crawl up to 4 contact-related pages on a business website."""
    base_url = _normalize_url(base_url)
    if not base_url:
        return None, None
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc.replace("www.", "")
    found_emails: list[str] = []
    found_phone: Optional[str] = None
    for path in CONTACT_PATHS:
        url = urljoin(origin + "/", path.lstrip("/"))
        try:
            r = await client.get(url, headers=BROWSER_HEADERS, timeout=8.0, follow_redirects=True)
        except Exception:
            continue
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
            continue
        emails = _extract_emails_from_html(r.text, prefer_domain=domain)
        if emails:
            found_emails.extend(emails)
        if not found_phone:
            pm = re.search(r'(?:tel:|t[ée]l[ée]phone[\s:]*)\s*\+?\d[\d\s().\-]{8,18}', r.text, re.IGNORECASE)
            if pm:
                found_phone = re.sub(r'^[^+\d]*(\+?\d[\d\s().\-]+)$', r'\1', pm.group(0))
        if found_emails:
            break
    # Score + dedupe
    seen = set()
    unique = []
    for e in found_emails:
        if e not in seen and not _is_junk_email(e):
            seen.add(e)
            unique.append(e)
    unique.sort(key=lambda a: (0 if domain.split(".")[0] in a else 1, _score_email(a)))
    return (unique[0] if unique else None), found_phone


async def enrich_prospect(prospect: dict, client: Optional[httpx.AsyncClient] = None) -> dict:
    """Re-enrich a prospect using its existing website. Returns the mutated dict."""
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=15.0)
    try:
        if prospect.get("website"):
            email, phone = await _crawl_website_for_contact(client, prospect["website"])
            if email and not prospect.get("email"):
                prospect["email"] = email
            if phone and not prospect.get("phone"):
                prospect["phone"] = phone
    finally:
        if owns_client:
            await client.aclose()
    return prospect


# ---------------------------------------------------------------------------
# Public scrape API
# ---------------------------------------------------------------------------
async def scrape_region(
    region_key: str,
    max_results: int = 30,
    category: str = "vitrerie",
    deep_enrich: bool = True,
) -> List[dict]:
    region = REGIONS.get(region_key)
    if not region:
        raise ValueError(f"Unknown region: {region_key}")
    cat = CATEGORIES.get(category)
    if not cat:
        raise ValueError(f"Unknown category: {category}")

    yp_city = region["yp_city"]
    all_stubs: List[dict] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Pull from each YP keyword, page 1 (and page 2 if we need more)
        for keyword in cat["yp_keywords"]:
            for page in (1, 2):
                stubs = await _yp_search_listings(client, keyword, yp_city, page)
                all_stubs.extend(stubs)
                if len(all_stubs) >= max_results * 2:
                    break
                if len(stubs) < 5:
                    break  # last page reached
            if len(all_stubs) >= max_results * 2:
                break

        # Dedupe by yp_url
        seen = set()
        unique = []
        for s in all_stubs:
            key = s.get("yp_url") or (s.get("name"), s.get("city"))
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        unique = unique[:max_results]

        # Step 2: fetch YP detail page for each to get phone + website
        sem = asyncio.Semaphore(4)

        async def fetch_one(stub):
            async with sem:
                return await _yp_fetch_details(client, stub)

        details = await asyncio.gather(*[fetch_one(s) for s in unique], return_exceptions=True)
        enriched_stubs = [d for d in details if isinstance(d, dict)]

        # Step 3: deep enrich — crawl each website for contact info
        if deep_enrich:
            sem2 = asyncio.Semaphore(5)

            async def crawl_one(p):
                async with sem2:
                    if p.get("website"):
                        email, phone = await _crawl_website_for_contact(client, p["website"])
                        if email and not p.get("email"):
                            p["email"] = email
                        if phone and not p.get("phone"):
                            p["phone"] = phone
                return p
            enriched_stubs = await asyncio.gather(*[crawl_one(p) for p in enriched_stubs])

    # Final normalization → prospect dicts
    out = []
    for s in enriched_stubs:
        if not s.get("name"):
            continue
        out.append({
            "name": s["name"],
            "email": s.get("email"),
            "phone": s.get("phone"),
            "website": s.get("website"),
            "address": s.get("address"),
            "city": s.get("city") or region["label"],
            "region": region_key,
            "category": category,
            "source": "yellowpages",
        })
    return out


async def scrape_all_regions(
    max_per_region: int = 40,
    category: str = "vitrerie",
    deep_enrich: bool = True,
) -> List[dict]:
    results = []
    for key in REGIONS:
        try:
            chunk = await scrape_region(key, max_per_region, category, deep_enrich)
            results.extend(chunk)
        except Exception as exc:
            logger.warning("Scrape failed for %s/%s: %s", key, category, exc)
    return results
