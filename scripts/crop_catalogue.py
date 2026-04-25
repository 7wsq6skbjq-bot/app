"""
Crop selected catalogue pages from Sargent PDFs into clean catalogue tiles
for /app/frontend/public/catalogue/.
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
# crop_box is in original coords (x1, y1, x2, y2)
SELECTIONS = [
    # ===== POIGNÉES & LEVIERS — Studio Collection (Sargent 1004765) =====
    # Right-half crop to keep clean white product area (left half has city imagery)
    ("AADSS1004765", "page-08.jpg", "handle-1.png", (560, HEADER, W, H - FOOTER)),
    ("AADSS1004765", "page-11.jpg", "handle-2.png", (560, HEADER, W, H - FOOTER)),
    ("AADSS1004765", "page-14.jpg", "handle-3.png", (560, HEADER, W, H - FOOTER)),

    # ===== SERRURES & CYLINDRES — Degree Key System (1004587) =====
    ("AADSS1004587", "page-01.jpg", "lock-1.png", None),       # cover
    ("AADSS1004587", "page-06.jpg", "lock-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1004587", "page-08.jpg", "lock-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== BARRES ANTIPANIQUES — 5300 Alarmed Exit (1086801) =====
    ("AADSS1086801", "page-1.jpg", "panic-1.png", None),       # cover with full panic bar
    ("AADSS1086801", "page-3.jpg", "panic-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1086801", "page-4.jpg", "panic-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== FERME-PORTES — 2300/2409 Fire Guard (1257255) =====
    ("AADSS1257255", "page-01.jpg", "closer-1.png", None),     # cover
    ("AADSS1257255", "page-04.jpg", "closer-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1257255", "page-06.jpg", "closer-3.png", (0, HEADER, W, H - FOOTER)),

    # ===== CONTRÔLE D'ACCÈS — Multi-Point Auto Deadlocking (1052882) =====
    ("AADSS1052882", "page-01.jpg", "access-1.png", None),     # cover
    ("AADSS1052882", "page-04.jpg", "access-2.png", (0, HEADER, W, H - FOOTER)),
    ("AADSS1052882", "page-06.jpg", "access-3.png", (0, HEADER, W, H - FOOTER)),
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
        # resize to max 1400px wide
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
