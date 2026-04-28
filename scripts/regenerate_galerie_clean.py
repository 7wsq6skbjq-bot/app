"""
Iter 14 — Regenerate 12 galerie images with CLEAN HARDWARE close-up aesthetic.

User feedback: previous Portech-branded technician + DeWalt tool images are wrong.
Reference style: SALTO smart locks, mortise cylinder close-ups, commercial panic
bars on aluminum doors. NO people, NO tools, NO fictional branding.

Output: PNG files written to /app/frontend/public/generated/portfolio/
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/generated/portfolio")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- Universal style/composition rules embedded into every prompt -----
STYLE = (
    "Photorealistic high-end commercial architectural product photography. "
    "Sharp tack focus on the door hardware, shallow depth of field with a soft "
    "blurred contextual background. Clean professional product-on-door shot in "
    "the style of manufacturer catalog photography (SALTO, Sargent, Von Duprin, "
    "Schlage). Natural daylight or soft studio lighting, neutral color grading. "
    "Square 1:1 framing, 4K detail. STRICTLY: NO PEOPLE visible, NO HANDS, NO "
    "TOOLS, NO drills, NO screwdrivers, NO branding text, NO logos, NO French "
    "or English signage in the frame. Just the hardware mounted on a real "
    "commercial door, photographed at a slight angle showing depth and finish."
)

IMAGES = [
    # ---- Interventions (4) ----
    (
        "gal-interv-1",
        "Close-up of a brushed stainless-steel commercial lever handle freshly "
        "installed on a dark anodized aluminum storefront door. The lever is "
        "mounted on a slim rectangular escutcheon. Visible mortise edge plate "
        "on the door jamb. Background: blurred modern office lobby with soft "
        "warm indirect lighting. Door panel takes ~60% of frame, hardware "
        "centered."
    ),
    (
        "gal-interv-2",
        "Mid-shot of an LCN-style heavy-duty surface-mounted hydraulic door "
        "closer mounted on the upper push-side of a light-grey commercial "
        "aluminum door. The closer body is dark bronze finish with a parallel "
        "arm extending to the door frame. Background: blurred bright glass "
        "office corridor. Architectural product detail, no humans."
    ),
    (
        "gal-interv-3",
        "Detailed product shot of a continuous geared aluminum hinge running "
        "the full height between a brushed-aluminum commercial door and its "
        "matching frame. Visible knuckle teeth pattern, satin anodized finish. "
        "Slight perspective from inside an office, soft outdoor light spilling "
        "through the door gap. No people, no tools."
    ),
    (
        "gal-interv-4",
        "Macro close-up of a high-security 6-pin restricted-keyway brass "
        "cylinder seated inside a satin-chrome mortise lock face on a wooden "
        "commercial office door. The cylinder is freshly installed, the keyway "
        "facing the camera at a slight angle. Soft blurred warm office "
        "background. Manufacturer-catalog quality."
    ),
    # ---- Dispositifs de sortie (3 — keeping #3) ----
    (
        "gal-exit-1",
        "Chrome rim exit device (panic touchpad bar style) mounted "
        "horizontally on the inside of a single anodized-aluminum storefront "
        "door. Polished stainless finish, visible end caps, mounting bolts "
        "neatly aligned. Background: blurred entrance vestibule with daylight "
        "from the glass panel. Clean commercial product shot, no humans."
    ),
    (
        "gal-exit-2",
        "Concealed vertical-rod exit device in a high school auditorium pair "
        "of double doors. Stainless steel touchpad bar across the active "
        "leaf, top and bottom rod points just barely visible at the head and "
        "threshold. Doors are dark grey hollow metal with a small wired-glass "
        "vision lite. Soft directional house lighting. No people."
    ),
    (
        "gal-exit-4",
        "Macro close-up of a chrome-finish touchpad-style exit device on a "
        "commercial aluminum door — focus on the dogging cylinder hole, end "
        "cap and the brushed-stainless push pad. Slight angle reveals the "
        "depth of the chassis. Blurred neutral grey corridor background. "
        "Studio-grade product photography, no humans."
    ),
    # ---- Barres antipaniques (1 — only #2) ----
    (
        "gal-panic-2",
        "Brushed-stainless cross-bar style panic exit device with a hex "
        "dogging key feature, mounted on the inside of a dark-grey hollow-"
        "metal commercial door in a movie theatre back-of-house corridor. "
        "Visible mounting plate, cylindrical rim case on the latch side. Cool "
        "neutral fluorescent lighting blurred in background. No people."
    ),
    # ---- Serrures (4) ----
    (
        "gal-lock-1",
        "Stainless steel mortise lock case partially exposed inside the edge "
        "of an open brushed-aluminum commercial door. The deadbolt and "
        "latchbolt are visible, the strike plate is on the matching frame. "
        "Slightly angled shot, soft warm indirect light from a modern office "
        "interior blurred behind. No tools, no hands, no people."
    ),
    (
        "gal-lock-2",
        "Cylindrical lever lockset with a matte-black flat lever handle and "
        "matte-black round rose, installed on a light-oak veneered commercial "
        "office door. Centered close-up at slight angle, soft daylight from "
        "the side. Background: minimalist neutral office wall blurred. "
        "Premium product look, no humans."
    ),
    (
        "gal-lock-3",
        "Electronic RFID/card mortise lock with a discreet black reader panel "
        "above a brushed-stainless lever handle, mounted on a light wood "
        "commercial door of a secure server room. Small green LED indicator "
        "visible. Clean product shot in the style of SALTO XS4 hotel-lock "
        "marketing photography. Slight angle, soft studio lighting. No "
        "people, no branding text in the frame."
    ),
    (
        "gal-lock-4",
        "Storeroom-function classroom-grade mortise lock with a heavy-duty "
        "stainless steel lever and visible exterior cylinder, mounted on a "
        "painted hollow-metal warehouse door. Industrial grey wall blurred "
        "behind the door. Cool top lighting, slightly angled product shot. "
        "Robust commercial-grade hardware. No people, no tools, no branding."
    ),
]


async def gen_one(idx: int, total: int, filename: str, prompt: str) -> bool:
    full_prompt = f"{prompt}\n\n{STYLE}"
    api_key = os.getenv("EMERGENT_LLM_KEY")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"galerie-clean-{filename}",
        system_message=(
            "You are an architectural product photography AI. Generate ONE "
            "photorealistic close-up image of commercial door hardware. STRICTLY "
            "no people, no hands, no tools, no logos, no signage text. The image "
            "must look like a high-end manufacturer catalog or marketing photo "
            "(SALTO, Sargent, Von Duprin style)."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    path = OUT_DIR / f"{filename}.png"
    try:
        _text, images = await chat.send_message_multimodal_response(
            UserMessage(text=full_prompt)
        )
        if not images:
            print(f"[{idx}/{total}] FAIL {filename}: no image returned")
            return False
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        path.write_bytes(image_bytes)
        print(f"[{idx}/{total}] OK   {filename}.png ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"[{idx}/{total}] FAIL {filename}: {e}")
        return False


async def main():
    total = len(IMAGES)
    ok = 0
    for idx, (filename, prompt) in enumerate(IMAGES, start=1):
        if await gen_one(idx, total, filename, prompt):
            ok += 1
    print(f"\nDone — {ok}/{total} succeeded.")


if __name__ == "__main__":
    asyncio.run(main())
