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
if detail_path.exists():
    detail = Image.open(detail_path).convert("RGB")
    # Crop the right half (vertical band ~500px wide) to act as an accent
    crop_w = 500
    dW, dH = detail.size
    band = detail.crop(
        (dW // 2, 0, dW // 2 + crop_w, dH) if dW > crop_w else (0, 0, dW, dH)
    )
    # Resize the band to footer height while maintaining aspect
    ratio = FH / band.height
    band = band.resize((int(band.width * ratio), FH), Image.LANCZOS)
    # Paste on the right
    px = FW - band.width
    footer.paste(band, (px, 0))
    # Gradient overlay from dark to transparent over the band so text stays readable
    overlay = Image.new("RGBA", (band.width, FH), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(band.width):
        # alpha goes from 240 (very dark left edge) to 60 (mostly transparent right)
        alpha = max(60, int(240 - (i / band.width) * 180))
        od.line([(i, 0), (i, FH)], fill=(12, 24, 43, alpha))
    footer.paste(overlay, (px, 0), overlay)

# Footer text on the left
font_bold_md = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=36,
)
font_md = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=22,
)
font_sm = find_font(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=18,
)

fd.text((60, 60), "Cédrick Pimparé", font=font_bold_md, fill=WHITE)
fd.text((60, 110), "Fondateur · Portech", font=font_md, fill=MUTED)

# Contact stack
fd.text((60, 165), "438 376-4177", font=font_md, fill=WHITE)
fd.text((60, 200), "portech.info", font=font_md, fill=WHITE)
fd.text(
    (60, 240),
    "Grand Montréal · Laval · Rive-Sud · Rive-Nord",
    font=font_sm, fill=MUTED,
)

footer.save(OUT / "email-footer.png", "PNG", optimize=True)
print(f"Wrote email-footer.png ({footer.size})")
print("\nDone.")
