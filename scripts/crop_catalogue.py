"""
Crop selected catalogue pages from Sargent / Hager / Von Duprin / Dormakaba PDFs
into clean catalogue tiles for /app/frontend/public/catalogue/.
"""
from pathlib import Path
from PIL import Image

SRC = Path("/tmp/pdfhi")
OUT = Path("/app/frontend/public/catalogue")
OUT.mkdir(parents=True, exist_ok=True)

# Each PDF page renders at 1700×2200 (200 dpi)
W, H = 1700, 2200
HEADER = 90      # remove top header
FOOTER = 110     # remove bottom footer

# (catalog_id, page_filename, output_filename, crop_box or None for default trim)
SELECTIONS = [
    # ===== POIGNÉES & LEVIERS — Sargent Studio Collection =====
    ("AADSS1004765", "page-08.jpg", "handle-1.png", (560, HEADER, W, H - FOOTER)),
    ("AADSS1004765", "page-11.jpg", "handle-2.png", (560, HEADER, W, H - FOOTER)),
    ("AADSS1004765", "page-14.jpg", "handle-3.png", (560, HEADER, W, H - FOOTER)),

    # ===== SERRURES & CYLINDRES — Sargent Degree Key System =====
    ("AADSS1004587", "page-01.jpg", "lock-1.png", None),
    ("AADSS1004587", "page-06.jpg", "lock-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1004587", "page-08.jpg", "lock-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== BARRES ANTIPANIQUES — Sargent 5300 Alarmed Exit =====
    ("AADSS1086801", "page-1.jpg", "panic-1.png", None),
    ("AADSS1086801", "page-3.jpg", "panic-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1086801", "page-4.jpg", "panic-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== FERME-PORTES — Sargent 2300/2409 Fire Guard =====
    ("AADSS1257255", "page-01.jpg", "closer-1.png", None),
    ("AADSS1257255", "page-04.jpg", "closer-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1257255", "page-06.jpg", "closer-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== CONTRÔLE D'ACCÈS — Von Duprin Electrical Security =====
    ("Von_Duprin_Electrical_Security_Products_and_Accessories_Catalog_109981", "page-01.jpg", "access-1.png", None),
    ("Von_Duprin_Electrical_Security_Products_and_Accessories_Catalog_109981", "page-06.jpg", "access-2.png", (0, HEADER, W, H - FOOTER)),
    ("Von_Duprin_Electrical_Security_Products_and_Accessories_Catalog_109981", "page-20.jpg", "access-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== CHARNIÈRES & PIVOTS — Hager Commercial Hinges =====
    ("2016_hager_catalog_commhinges_rev5_v148", "page-01.jpg", "hinge-1.png", None),
    ("2016_hager_catalog_commhinges_rev5_v148", "page-08.jpg", "hinge-2.png", (0, HEADER, W, H - FOOTER)),
    ("2016_hager_catalog_commhinges_rev5_v148", "page-20.jpg", "hinge-3.png", (0, HEADER, W, H - FOOTER)),
]


def process():
    ok = 0
    for cat_id, src, dst, box in SELECTIONS:
        src_path = SRC / cat_id / src
        if not src_path.exists():
            print(f"❌ missing: {src_path}")
            continue
        im = Image.open(src_path).convert("RGB")
        if box:
            im = im.crop(box)
        max_w = 1400
        if im.size[0] > max_w:
            ratio = max_w / im.size[0]
            im = im.resize((max_w, int(im.size[1] * ratio)), Image.LANCZOS)
        out_path = OUT / dst
        im.save(out_path, "PNG", optimize=True)
        print(f"✅ {dst}: {im.size[0]}x{im.size[1]} ({out_path.stat().st_size//1024}KB)")
        ok += 1
    print(f"\n{ok}/{len(SELECTIONS)} ok")


if __name__ == "__main__":
    process()
