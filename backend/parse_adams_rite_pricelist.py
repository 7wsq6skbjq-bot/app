import json
import re
import sys

import pypdf

PRICE = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)")
# leading product code: optional letters, optional +, 3-4 digits, then code chars
PART = re.compile(r"^[A-Z]{0,4}\+?\d{3,4}[A-Z0-9\+\-/]*$")
SKIP_STARTS = ("how to order", "product no", "models", "model ", "model&",
               "special models", "table of contents", "us ", "canada ",
               "patent", "all rights", "updated", "finishes", "note",
               "accessories", "packaging")


def parse(path):
    r = pypdf.PdfReader(path)
    rows = []
    for i, p in enumerate(r.pages):
        for raw in (p.extract_text() or "").split("\n"):
            line = raw.replace("\u2002", " ").replace("\u2003", " ").strip()
            if "$" not in line:
                continue
            low = line.lower()
            if any(low.startswith(s) for s in SKIP_STARTS):
                continue
            pm = list(PRICE.finditer(line))
            if not pm:
                continue
            price = float(pm[-1].group(1).replace(",", ""))
            if price <= 0 or price > 100000:
                continue
            head = line[: pm[-1].start()].strip()
            toks = head.split()
            if not toks:
                continue
            pn = toks[0]
            if not PART.match(pn) or not re.search(r"\d{3,}", pn):
                continue
            desc = " ".join(toks[1:]).strip(" ,.-")
            rows.append({"part_number": pn, "description": desc[:140],
                         "list_price_usd": price, "page": i + 1})
    seen = {}
    for x in rows:
        # keep the first (or the one with a description)
        if x["part_number"] not in seen or (not seen[x["part_number"]]["description"] and x["description"]):
            seen[x["part_number"]] = x
    return rows, list(seen.values())


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "vendor_catalogs/adams_rite_pricelist_full.pdf"
    allr, uniq = parse(path)
    print("total price rows:", len(allr), "| unique part numbers:", len(uniq))
    for x in uniq[:25]:
        print(f"  {x['part_number']:22s} {('$'+str(x['list_price_usd'])):>9s}  {x['description'][:60]}")
    json.dump(uniq, open("/tmp/ar_full.json", "w"))
    print("saved /tmp/ar_full.json")
