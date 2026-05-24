"""
Free Google Maps scraper for prospection (vitreries).

Uses the Nominatim + OpenStreetMap Overpass API — 100% free, no API key
required. Searches for `shop=glaziery` and similar tags around a region.

For higher-quality contact info (emails), we fall back to scraping the
business website when one is listed in OSM.
"""
import asyncio
import logging
import re
from typing import List

import httpx

logger = logging.getLogger("portech.prospection")

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Bounding boxes for our target regions (approximate)
REGIONS = {
    "montreal":  {"south": 45.41, "west": -73.97, "north": 45.71, "east": -73.47, "label": "Grand Montréal"},
    "laval":     {"south": 45.51, "west": -73.91, "north": 45.71, "east": -73.59, "label": "Laval"},
    "rive-sud":  {"south": 45.39, "west": -73.66, "north": 45.59, "east": -73.31, "label": "Rive-Sud"},
    "rive-nord": {"south": 45.59, "west": -74.10, "north": 45.95, "east": -73.41, "label": "Rive-Nord"},
}

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _overpass_query(bbox: dict) -> str:
    s, w, n, e = bbox["south"], bbox["west"], bbox["north"], bbox["east"]
    return (
        "[out:json][timeout:30];\n"
        "(\n"
        f'  node["shop"="glaziery"]({s},{w},{n},{e});\n'
        f'  way["shop"="glaziery"]({s},{w},{n},{e});\n'
        f'  node["craft"="glaziery"]({s},{w},{n},{e});\n'
        f'  way["craft"="glaziery"]({s},{w},{n},{e});\n'
        f'  node["name"~"vitrerie",i]({s},{w},{n},{e});\n'
        f'  way["name"~"vitrerie",i]({s},{w},{n},{e});\n'
        ");\n"
        "out body center tags;\n"
    )


def _node_to_prospect(node: dict, region_key: str) -> dict | None:
    tags = node.get("tags") or {}
    name = tags.get("name")
    if not name:
        return None
    # OSM addr parts
    addr_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
    ]
    address = " ".join(p for p in addr_parts if p) or None
    city = tags.get("addr:city")
    phone = (tags.get("phone") or tags.get("contact:phone") or "").replace(" ", "")
    if phone and not phone.startswith("+"):
        # leave as-is, user can clean up
        pass
    email = tags.get("email") or tags.get("contact:email")
    website = tags.get("website") or tags.get("contact:website")
    return {
        "name": name,
        "email": email,
        "phone": tags.get("phone") or tags.get("contact:phone"),
        "website": website,
        "address": address,
        "city": city,
        "region": region_key,
        "source": "google-maps",
    }


async def _maybe_extract_email_from_website(url: str) -> str | None:
    """Best-effort fetch of homepage + /contact page to find an email."""
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    candidates = [url]
    if not url.rstrip("/").endswith(("/contact", "/contact-us", "/nous-joindre")):
        candidates.append(url.rstrip("/") + "/contact")
    for candidate in candidates:
        try:
            async with httpx.AsyncClient(
                timeout=8.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 PortechBot/1.0"},
            ) as client:
                r = await client.get(candidate)
                if r.status_code != 200:
                    continue
                # Look for mailto: links first
                m = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r.text)
                if m:
                    return m.group(1)
                m = EMAIL_RE.search(r.text)
                if m:
                    found = m.group(0)
                    # Skip obvious noise
                    if any(s in found.lower() for s in ("sentry", "wixpress", "godaddy", "example", "noreply")):
                        continue
                    return found
        except Exception as exc:
            logger.debug("website fetch failed %s: %s", candidate, exc)
    return None


async def scrape_region(region_key: str, max_results: int = 30) -> List[dict]:
    """Return a list of prospect dicts for a given region key."""
    bbox = REGIONS.get(region_key)
    if not bbox:
        raise ValueError(f"Unknown region: {region_key}")

    query = _overpass_query(bbox)
    headers = {
        "User-Agent": "PortechProspectionBot/1.0 (contact: info@portech.info)",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    raw_results: List[dict] = []
    for el in data.get("elements", [])[: max_results * 2]:
        p = _node_to_prospect(el, region_key)
        if p:
            raw_results.append(p)

    # Dedupe by name
    seen = set()
    unique = []
    for p in raw_results:
        key = (p["name"].strip().lower(), p.get("city") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    # Fetch missing emails from websites in parallel (limit to first N)
    enrich = unique[:max_results]
    tasks = []
    for p in enrich:
        if not p.get("email") and p.get("website"):
            tasks.append(_maybe_extract_email_from_website(p["website"]))
        else:
            tasks.append(asyncio.sleep(0, result=None))
    found_emails = await asyncio.gather(*tasks, return_exceptions=True)
    for p, e in zip(enrich, found_emails):
        if isinstance(e, str) and e:
            p["email"] = e

    return enrich


async def scrape_all_regions(max_per_region: int = 40) -> List[dict]:
    """Scrape all 4 target regions and merge."""
    results = []
    for key in REGIONS:
        try:
            chunk = await scrape_region(key, max_per_region)
            results.extend(chunk)
        except Exception as exc:
            logger.warning("Scrape failed for %s: %s", key, exc)
    return results
