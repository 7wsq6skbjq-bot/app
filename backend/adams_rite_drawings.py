"""Adams Rite Parts Manual — table of contents index + PDF page merge.

The manual's page 2 is a table of contents: each product line ends with its
printed page number (the exploded drawing page). Printed page P maps to the
0-based reader index P (page[0] is the cover).
"""
import io
import os
import re
from functools import lru_cache
from typing import List


def _tokens_from_label(label: str) -> set:
    """Model codes in a TOC label, e.g. '3600', 'MS1850S', '8800' → match keys.
    We keep codes that contain a run of >=3 digits to avoid false positives."""
    up = label.upper()
    toks = set()
    for m in re.findall(r"[A-Z]{0,3}\d{3,4}[A-Z]{0,2}", up):
        if re.search(r"\d{3,}", m):
            toks.add(m)
            toks.add(re.sub(r"[^0-9]", "", m))  # bare digits e.g. 1850
    return {t for t in toks if len(t) >= 3}


import pypdf

MANUAL_PATH = os.path.join(os.path.dirname(__file__), "vendor_catalogs",
                           "adams_rite_parts_manual.pdf")

# A TOC entry: a label followed by a trailing page number.
_TOC_LINE = re.compile(r"^(.*?[A-Za-z].*?)\s+(\d{1,3})\s*$")
_SKIP = ("adamsrite.com", "assaabloy", "Copyright", "All rights", "Patent",
         "Reproduction", "©")


@lru_cache(maxsize=1)
def load_index() -> tuple:
    """Return a tuple of {"label","page"} dicts parsed from the TOC (pages 2-3)."""
    reader = pypdf.PdfReader(MANUAL_PATH)
    total = len(reader.pages)
    entries = []
    seen = set()
    for idx in (1, 2):  # TOC spans first couple of pages
        if idx >= total:
            break
        for line in (reader.pages[idx].extract_text() or "").split("\n"):
            line = line.strip()
            if not line or any(s in line for s in _SKIP):
                continue
            m = _TOC_LINE.match(line)
            if not m:
                continue
            label = re.sub(r"\s+", " ", m.group(1)).strip(" .-")
            page = int(m.group(2))
            if len(label) < 4 or page < 2 or page >= total:
                continue
            key = (label.lower(), page)
            if key in seen:
                continue
            seen.add(key)
            entries.append({"label": label, "page": page})
    return tuple(entries)


def detect_from_hardware(hardware_texts: List[str]) -> list:
    """Match plan hardware text (description + part number) to manual drawings.
    Returns [{"label","page","matched"}] for each detected drawing."""
    blob = " ".join((t or "").upper() for t in hardware_texts)
    alnum = re.sub(r"[^A-Z0-9]", " ", blob)
    padded = " " + alnum + " "
    out, seen = [], set()
    for e in load_index():
        for tok in _tokens_from_label(e["label"]):
            # match as a bounded token to avoid e.g. 3600 matching 43600
            if re.search(r"(?<![0-9])" + re.escape(tok) + r"(?![0-9A-Z])", padded) \
                    or (" " + tok + " ") in padded:
                if e["page"] not in seen:
                    seen.add(e["page"])
                    out.append({"label": e["label"], "page": e["page"], "matched": tok})
                break
    return out


def merge_drawing_pages(base_pdf: bytes, pages: List[int]) -> bytes:
    """Append the given printed pages (drawing + its parts page) of the manual
    to `base_pdf`. Returns merged PDF bytes. Invalid pages are skipped."""
    if not pages:
        return base_pdf
    reader = pypdf.PdfReader(MANUAL_PATH)
    total = len(reader.pages)
    writer = pypdf.PdfWriter()
    writer.append(pypdf.PdfReader(io.BytesIO(base_pdf)))
    added = set()
    for p in pages:
        # printed page P → 0-based index P (cover is index 0). Include the
        # drawing page and the facing parts/price page when present.
        for idx in (p, p + 1):
            if 0 <= idx < total and idx not in added:
                writer.add_page(reader.pages[idx])
                added.add(idx)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
