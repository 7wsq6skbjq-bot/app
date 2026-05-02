"""
Generate 5 landscape cover-style photos specifically for the Google Business
Profile carousel. Each image is wide cinematic 16:9 framing, showcasing a
different service/product family from Portech's offering.

Rules (strictly enforced):
- NO people, NO hands, NO tools, no drills, no screwdrivers
- NO branding text, NO logos, NO signage in-frame
- Hardware fully installed and closed — no partial exposure, no disassembly
- Catalog-quality product photography aesthetic (SALTO / Sargent / Von Duprin)

Output: /app/frontend/public/gbp/ (so user can download them from the site).
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/gbp")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = (
    "WIDE LANDSCAPE 16:9 cinematic composition, wide horizontal framing for "
    "social media cover / business profile header use. Photorealistic high-"
    "end commercial architectural product photography. Sharp tack focus on "
    "the hardware, shallow depth of field, soft blurred contextual background. "
    "Manufacturer-catalog quality (SALTO, Sargent, Von Duprin, LCN). Natural "
    "daylight or soft studio lighting, neutral color grading, 4K detail. "
    "STRICTLY: NO PEOPLE, NO HANDS, NO TOOLS, no drills, no screwdrivers, no "
    "branding text, no logos, no French or English signage in-frame. Hardware "
    "must be COMPLETELY INSTALLED AND CLOSED — absolutely NO partial exposure, "
    "NO disassembly, NO exploded view, NO internals visible."
)

IMAGES = [
    (
        "gbp-cover-hero",
        "Wide cinematic landscape shot of a polished brushed-stainless-steel "
        "commercial lever handle set and slim rectangular escutcheon plate, "
        "perfectly centered on a dark anodized aluminum commercial storefront "
        "door in a modern Montreal office tower lobby. Clean morning daylight "
        "spilling in from a glass vestibule beyond. The door takes up the full "
        "height of the frame on the right side; soft architectural lobby space "
        "blurs out to the left. Ultra-premium magazine cover aesthetic. "
        "Everything completely installed and flush-mounted."
    ),
    (
        "gbp-exit-devices",
        "Wide cinematic landscape view of a pair of dark-grey hollow-metal "
        "commercial double doors — an institutional corridor view — each door "
        "fitted with a long stainless-steel touchpad exit device (Von Duprin "
        "98/99 style) running horizontally across the inside face. Molded end "
        "caps, visible dogging cylinders, perfectly aligned. Clean empty "
        "corridor stretches into soft-focus background. Neutral institutional "
        "lighting. Completely installed, nothing exposed."
    ),
    (
        "gbp-panic-bars",
        "Landscape cinematic close-up of a brushed-stainless crash-bar style "
        "panic exit device mounted on the inside of a dark grey commercial "
        "hollow-metal door of a school or retail back-of-house. Wide "
        "horizontal composition that emphasizes the full length of the push "
        "bar. Cool neutral overhead light, blurred hallway background with "
        "soft bokeh. Clean, completely installed, no branding."
    ),
    (
        "gbp-mortise-lock",
        "Wide landscape macro composition of a premium commercial mortise "
        "lockset FULLY INSTALLED on the exterior face of a brushed-aluminum "
        "commercial door: satin-stainless lever handle on a slim rectangular "
        "escutcheon, with a restricted-keyway brass cylinder above the lever. "
        "Slight 3/4 angle from the hinge side showing the matching strike "
        "plate on the frame. Soft blurred modern office interior in background."
    ),
    (
        "gbp-closer-hinge",
        "Wide landscape view showing the upper portion of a commercial aluminum "
        "door with a surface-mounted hydraulic door closer correctly installed "
        "in regular-arm configuration: rectangular closer BODY horizontal on "
        "the push-side face of the door near the head, closer ARM extending "
        "UP and OUTWARD with its forearm bolted to the FRAME HEADER above. "
        "Matte black / dark bronze finish. Architectural office background "
        "blurred. Completely installed, perfectly adjusted."
    ),
]


async def gen_one(idx, total, filename, prompt):
    full_prompt = f"{prompt}\n\n{STYLE}"
    api_key = os.getenv("EMERGENT_LLM_KEY")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"gbp-{filename}",
        system_message=(
            "You are an architectural product photography AI. Generate ONE "
            "WIDE LANDSCAPE photorealistic image of commercial door hardware "
            "suitable for a Google Business Profile cover photo. STRICT: no "
            "people, no hands, no tools, no logos, no signage text, no partial "
            "exposure. Catalog-quality (SALTO, Sargent, Von Duprin)."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    path = OUT_DIR / f"{filename}.png"
    try:
        _t, imgs = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
        if not imgs:
            print(f"[{idx}/{total}] FAIL {filename}: no image")
            return False
        b = base64.b64decode(imgs[0]["data"])
        path.write_bytes(b)
        print(f"[{idx}/{total}] OK {filename}.png ({len(b)//1024} KB)")
        return True
    except Exception as exc:
        print(f"[{idx}/{total}] FAIL {filename}: {exc}")
        return False


async def main():
    total = len(IMAGES)
    ok = 0
    for idx, (fn, pr) in enumerate(IMAGES, start=1):
        if await gen_one(idx, total, fn, pr):
            ok += 1
    print(f"\nDone — {ok}/{total} succeeded.")


if __name__ == "__main__":
    asyncio.run(main())
