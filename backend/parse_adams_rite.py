import json
import re
import sys

import pypdf

PRICE = re.compile(r"\$\s?(\d{1,4}(?:\.\d{1,2})?)")
LEAD_ITEM = re.compile(r"^\d{1,3}$")
UNITS_TAIL = re.compile(r"(Pack of \d+|Pkg of \d+|Package of \d+|Each|Pair|Set).*$", re.I)


def parse(path):
    r = pypdf.PdfReader(path)
    rows = []
    for i, p in enumerate(r.pages):
        t = p.extract_text() or ""
        for line in t.split("\n"):
            line = line.strip()
            if "$" not in line:
                continue
            pm = list(PRICE.finditer(line))
            if not pm:
                continue
            price = float(pm[-1].group(1))
            head = line[: pm[-1].start()].strip()
            toks = head.split()
            if not toks:
                continue
            if LEAD_ITEM.fullmatch(toks[0]):
                toks = toks[1:]
            if not toks:
                continue
            pn = toks[0]
            # part number must contain a digit and be reasonably long
            if not re.search(r"\d", pn) or len(pn) < 4:
                continue
            desc = " ".join(toks[1:])
            desc = UNITS_TAIL.sub("", desc).strip()
            rows.append({
                "part_number": pn,
                "description": desc[:120],
                "list_price_usd": price,
                "page": i + 1,
            })
    # dedupe keeping first occurrence
    seen = {}
    for x in rows:
        seen.setdefault(x["part_number"], x)
    return rows, list(seen.values())


if __name__ == "__main__":
    all_rows, uniq = parse(sys.argv[1] if len(sys.argv) > 1 else "vendor_catalogs/adams_rite_parts_manual.pdf")
    print("total rows:", len(all_rows), "| unique part numbers:", len(uniq))
    for x in uniq[:20]:
        print(x)
    json.dump(uniq, open("/tmp/ar_rows.json", "w"))
    print("saved /tmp/ar_rows.json")
