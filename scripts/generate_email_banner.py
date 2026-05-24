"""
Generate professional email banner assets for Portech prospection campaigns.

Two assets:
- email-header.png  → 1200x240 (retina 600x120) navy banner: logo + tagline
- email-footer.png  → 1200x300 (retina 600x150) signature visual with a
                      detail product shot + dark overlay

Outputs to /app/frontend/public/email/ so they're hostable via portech.info.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("/app/frontend/public/email")
OUT.mkdir(parents=True, exist_ok=True)

NAVY = (12, 24, 43)              # #0c182b — main brand
NAVY_LIGHT = (29, 53, 87)         # #1d3557 — accent line
WHITE = (255, 255, 255)
MUTED = (151, 176, 208)           # #97b0d0 — secondary text


def find_font(*candidates, size=24):
    """Pick the first available TTF on disk; fall back to PIL default."""
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ============================================================
#  HEADER  — 1200x240 (retina, displayed at 600x120 in email)
# ============================================================
W, H = 1200, 240
header = Image.new("RGB", (W, H), NAVY)
draw = ImageDraw.Draw(header)

# Subtle grid lines (architectural feel)
for x in range(0, W, 48):
    draw.line([(x, 0), (x, H)], fill=(20, 35, 58), width=1)
for y in range(0, H, 48):
    draw.line([(0, y), (W, y)], fill=(20, 35, 58), width=1)

# Accent thin line at the very bottom
draw.rectangle([(0, H - 4), (W, H)], fill=MUTED)

# Paste the Portech monogram on the left (vertically centered)
mono_src = Path("/app/frontend/public/brand/portech-mark.png")
if mono_src.exists():
    mono = Image.open(mono_src).convert("RGBA")
    # Resize to fit ~70 % of header height
    target_h = int(H * 0.62)
    ratio = target_h / mono.height
    mono = mono.resize(
        (int(mono.width * ratio), target_h), Image.LANCZOS,
    )
    # Mask to keep transparency
    header.paste(mono, (60, (H - mono.height) // 2), mono)

# Right side: company name + tagline
font_bold = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=58,
)
font_light = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=22,
)

# Headline
draw.text((310, 65), "PORTECH", font=font_bold, fill=WHITE)
# Sub-line
sub = "QUINCAILLERIE DE PORTE COMMERCIALE"
draw.text((315, 140), sub, font=font_light, fill=MUTED)
# Thin separator on the right
draw.line([(280, 60), (280, 200)], fill=MUTED, width=2)

header.save(OUT / "email-header.png", "PNG", optimize=True)
print(f"Wrote email-header.png ({header.size})")


# ============================================================
#  FOOTER SIGNATURE  —  1200x300 (displayed 600x150)
# ============================================================
FW, FH = 1200, 300
footer = Image.new("RGB", (FW, FH), NAVY)
fd = ImageDraw.Draw(footer)

# Subtle grid again
for x in range(0, FW, 48):
    fd.line([(x, 0), (x, FH)], fill=(20, 35, 58), width=1)
for y in range(0, FH, 48):
    fd.line([(0, y), (FW, y)], fill=(20, 35, 58), width=1)

# Top accent line
fd.rectangle([(0, 0), (FW, 4)], fill=MUTED)

# Try to overlay a real product detail shot on the right side as a "showcase"
detail_path = Path("/app/frontend/public/gbp/gbp-cover-hero.png")
band_width = 0
if detail_path.exists():
    detail = Image.open(detail_path).convert("RGB")
    crop_w = 460
    dW, dH = detail.size
    band = detail.crop(
        (dW // 2, 0, dW // 2 + crop_w, dH) if dW > crop_w else (0, 0, dW, dH)
    )
    ratio = FH / band.height
    band = band.resize((int(band.width * ratio), FH), Image.LANCZOS)
    px = FW - band.width
    band_width = band.width
    footer.paste(band, (px, 0))
    overlay = Image.new("RGBA", (band.width, FH), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(band.width):
        alpha = max(80, int(240 - (i / band.width) * 180))
        od.line([(i, 0), (i, FH)], fill=(12, 24, 43, alpha))
    footer.paste(overlay, (px, 0), overlay)

# Paste the small Portech monogram in the top-left of the footer for branding
mono_src = Path("/app/frontend/public/brand/portech-mark.png")
if mono_src.exists():
    mono = Image.open(mono_src).convert("RGBA")
    target_h = 60
    ratio = target_h / mono.height
    mono = mono.resize((int(mono.width * ratio), target_h), Image.LANCZOS)
    footer.paste(mono, (60, 36), mono)

font_bold_md = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=34,
)
font_md = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=22,
)
font_sm = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=18,
)
font_xs = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=15,
)
font_label = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=13,
)

# Brand text next to the small monogram
fd.text((150, 46), "PORTECH", font=font_bold_md, fill=WHITE)
fd.text(
    (150, 86),
    "Quincaillerie de porte commerciale",
    font=font_xs, fill=MUTED,
)

# Vertical separator
fd.line([(60, 118), (FW - band_width - 60, 118)], fill=(40, 60, 100), width=1)

# Two-column info layout
# --- LEFT COLUMN: services ---
fd.text((60, 138), "SERVICES", font=font_label, fill=MUTED)
services = [
    "Installation & remplacement",
    "Entretien & ajustement",
    "Portes aluminium sur mesure",
    "Sous-traitance vitreries",
]
y = 162
for s in services:
    # Small dot bullet
    fd.ellipse([(60, y + 9), (66, y + 15)], fill=MUTED)
    fd.text((78, y), s, font=font_xs, fill=WHITE)
    y += 28

# --- RIGHT COLUMN (still on the left half): contact + zone ---
right_x = 480
fd.text((right_x, 138), "CONTACT", font=font_label, fill=MUTED)
fd.text((right_x, 162), "438 376-4177", font=font_md, fill=WHITE)
fd.text((right_x, 196), "portech.info", font=font_md, fill=WHITE)
fd.text((right_x, 234), "ZONE DESSERVIE", font=font_label, fill=MUTED)
fd.text((right_x, 258), "Grand Montréal · Laval", font=font_xs, fill=WHITE)
fd.text((right_x, 280), "Rive-Sud · Rive-Nord", font=font_xs, fill=WHITE)

footer.save(OUT / "email-footer.png", "PNG", optimize=True)
print(f"Wrote email-footer.png ({footer.size})")
print("\nDone.")
