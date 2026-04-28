"""
Iter 15 — Fix 5 bad galerie images + replace Home/Services technician shots.

Hard rules baked into EVERY prompt:
- NO people, NO hands, NO tools, NO drills, NO screwdrivers
- NO "partially exposed" / "disassembled" / "exploded view" hardware
- NO fictional branding, NO French/English signage in-frame
- Hardware must be COMPLETELY INSTALLED and CLOSED
- Clean manufacturer-catalog product photography aesthetic (SALTO, Sargent, Von Duprin style)
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
ALT_DIR = Path("/app/frontend/public/generated")
ALT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = (
    "Photorealistic high-end commercial architectural product photography, sharp "
    "tack focus, shallow depth of field, soft blurred contextual background. "
    "Manufacturer-catalog quality (SALTO, Sargent, Von Duprin, LCN). Natural "
    "daylight or soft studio lighting, neutral color grading, 1:1 square 4K detail. "
    "STRICTLY: NO PEOPLE, NO HANDS, NO TOOLS, no drills, no screwdrivers, no "
    "branding text, no logos, no French or English signage in-frame. Hardware "
    "must be COMPLETELY INSTALLED AND CLOSED — absolutely NO partial exposure, "
    "NO disassembly, NO exploded view, NO internals visible."
)

IMAGES = [
    # ============ 5 CORRECTIONS — galerie ============
    (
        OUT_DIR, "gal-interv-2",
        "Close-up product shot of a surface-mounted hydraulic door closer in a "
        "CORRECT REGULAR-ARM INSTALLATION: the rectangular cast-iron closer BODY "
        "is mounted horizontally on the push-side face of a light-grey commercial "
        "aluminum door, near the top of the door (about 6 inches below the head). "
        "The closer's MAIN ARM extends UP AND OUTWARD from the body, and its "
        "forearm END is bolted to the DOOR FRAME HEADER (soffit) via a bracket "
        "— NOT to the door. Arm forms an obtuse angle. Finish: matte black / "
        "dark bronze. Background: blurred bright office corridor with glass walls."
    ),
    (
        OUT_DIR, "gal-interv-3",
        "Full-height portrait composition showing a CONTINUOUS GEARED ALUMINUM "
        "HINGE running the ENTIRE VERTICAL LENGTH of a single commercial "
        "aluminum door, visible from the very TOP to the very BOTTOM of the "
        "door with NO break in the hinge. The hinge is a single continuous "
        "brushed-aluminum satin-anodized piece on the left edge of the door "
        "leaf, connecting it to the matching vertical frame. The camera shows "
        "the full 7-foot height of the door inside a modern office interior. "
        "Soft daylight. Door fully closed, hinge fully installed top to bottom."
    ),
    (
        OUT_DIR, "gal-interv-4",
        "Macro close-up of a HIGH-SECURITY restricted-keyway BRASS CYLINDER "
        "FULLY INSTALLED and seated flush inside the face of a commercial "
        "MORTISE LOCK face plate on the exterior side of a wooden commercial "
        "office door. The cylinder is a complete solid cylinder with the "
        "keyway facing the camera at a slight 20-degree angle. The mortise "
        "lock face is satin stainless steel. Everything is completely closed "
        "and installed — nothing disassembled, nothing partially exposed, no "
        "internals visible. Soft warm wooden office background blurred."
    ),
    (
        OUT_DIR, "gal-lock-1",
        "Close-up architectural product shot of a COMPLETELY INSTALLED and "
        "FULLY CLOSED commercial mortise lockset on the EXTERIOR FACE of a "
        "brushed aluminum commercial door: visible satin-stainless lever "
        "handle mounted on a slim rectangular escutcheon plate, with a "
        "restricted-keyway brass cylinder above the lever. Strike plate on "
        "the matching frame. Slight 3/4 angle from the hinge side. Clean, "
        "closed, finished install — nothing exposed, nothing disassembled. "
        "Soft blurred modern office interior background."
    ),
    (
        OUT_DIR, "gal-exit-4",
        "Close-up of an authentic commercial TOUCHPAD-STYLE EXIT DEVICE in "
        "the Von Duprin 98/99 or Sargent 80-Series family: long horizontal "
        "stainless-steel push pad (touchpad) running across roughly two "
        "thirds of the door width, with molded end caps at each end and a "
        "rim-mount lock case on the latch side showing a small dogging "
        "cylinder key-hole. COMPLETELY INSTALLED on the inside face of a "
        "dark-grey hollow-metal commercial door. Brushed stainless finish. "
        "Slight 3/4 angle. Blurred fluorescent-lit corridor background. "
        "Nothing exposed, nothing disassembled."
    ),

    # ============ HOME — 9 replacements ============
    (
        OUT_DIR, "home-showcase-tech",
        "Modern brushed stainless-steel wide lever handle with a matching "
        "rectangular escutcheon plate, fully installed on a dark anodized "
        "aluminum commercial storefront door. Close-up at slight angle. "
        "Background: blurred modern office entry lobby with natural daylight."
    ),
    (
        OUT_DIR, "home-service-installation",
        "Close-up of a matte-black commercial lever handle with a round "
        "escutcheon rose, fully installed on a sleek dark grey commercial "
        "aluminum door. Crisp reveals, flush escutcheon against the door "
        "face. Blurred bright office background. Manufacturer-catalog look."
    ),
    (
        OUT_DIR, "home-service-machining",
        "Close-up of the edge of a prepared commercial aluminum door showing "
        "a CLEANLY MACHINED MORTISE POCKET with the mortise lock body "
        "ALREADY INSTALLED inside it — satin-stainless face plate flush with "
        "the door edge, latch and deadbolt visible from the edge. Completely "
        "finished install — no tools, no hands, no exposed internals. Door "
        "fully closed view from the edge. Blurred workshop interior."
    ),
    (
        OUT_DIR, "home-service-repair",
        "Close-up of a surface-mounted commercial hydraulic door closer, "
        "correctly installed with the body on the push side of a commercial "
        "aluminum door and the arm attached to the frame header. Satin "
        "bronze finish, clean and well-adjusted. Blurred modern office "
        "corridor background, soft indirect daylight."
    ),
    (
        OUT_DIR, "home-service-upgrade",
        "Close-up of a brand new premium brushed-nickel commercial mortise "
        "lockset (lever + escutcheon + cylinder) fully installed and closed "
        "on a modern commercial aluminum door. Pristine new hardware, flush "
        "mount, crisp details. Blurred upscale office interior background."
    ),
    (
        OUT_DIR, "home-showcase-exit",
        "Chrome rim exit device (panic touchpad bar) mounted horizontally "
        "on the inside of a single anodized-aluminum storefront commercial "
        "door. Polished stainless finish, molded end caps, dogging cylinder "
        "visible. Slight 3/4 angle. Blurred entrance vestibule background "
        "with daylight through the glass."
    ),
    (
        OUT_DIR, "home-showcase-panic",
        "Brushed-stainless crash-bar style panic exit device on the inside "
        "of a dark grey hollow-metal commercial door in a retail back-of-"
        "house corridor. Visible mounting plate and rim case on the latch "
        "side. Cool neutral lighting, slight angle. Completely installed."
    ),
    (
        OUT_DIR, "home-showcase-lock",
        "Macro close-up of a satin-nickel commercial cylindrical lever "
        "lockset on a light-oak veneered commercial office door. Flush "
        "round rose, straight lever. Blurred minimalist neutral office "
        "background. Completely installed, perfect finish."
    ),

    # precision-install lives in /generated (not /portfolio)
    (
        ALT_DIR, "precision-install",
        "Close-up architectural shot of a commercial aluminum entrance door "
        "with perfect reveal gaps: visible continuous hinge, flush mortise "
        "lock face on the edge, matching strike plate on the frame. "
        "Hardware completely installed and aligned to the millimetre. Slight "
        "3/4 angle. Blurred modern lobby background."
    ),

    # ============ SERVICES — 4 replacements ============
    (
        OUT_DIR, "services-installation",
        "Wide-angle close-up of a brushed-stainless commercial lever handle "
        "and matching rectangular escutcheon completely installed on a dark "
        "anodized aluminum entrance door. Soft daylight from blurred lobby "
        "in the background. Catalog product quality."
    ),
    (
        OUT_DIR, "services-machining",
        "Close-up of the door-edge profile of a commercial aluminum door "
        "showing a perfectly machined mortise pocket with the mortise lock "
        "FULLY INSTALLED — satin-stainless face plate flush with edge, "
        "latch bolt visible. Clean finished edge, no tools, no hands. "
        "Blurred workshop shelving background."
    ),
    (
        OUT_DIR, "services-repair",
        "Close-up of a surface-mounted hydraulic door closer in correct "
        "regular-arm installation (body on door push side, arm bolted to "
        "frame header). Matte black finish, well adjusted, perfect angle. "
        "Blurred school or institutional corridor background."
    ),
    (
        OUT_DIR, "services-upgrade",
        "Macro close-up of a brand new premium brushed-nickel mortise lever "
        "lockset freshly installed on a modern commercial aluminum door. "
        "Pristine finish, flush escutcheon. Blurred upscale office interior."
    ),
]


async def gen_one(idx, total, out_dir, filename, prompt):
    full_prompt = f"{prompt}\n\n{STYLE}"
    api_key = os.getenv("EMERGENT_LLM_KEY")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"clean-v2-{filename}",
        system_message=(
            "You are an architectural product photography AI. Generate ONE "
            "photorealistic close-up image of commercial door hardware. STRICT: "
            "no people, no hands, no tools, no logos, no signage text, no "
            "partial exposure, no disassembly. The hardware must be COMPLETELY "
            "INSTALLED AND CLOSED. Catalog-quality (SALTO, Sargent, Von Duprin)."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    path = out_dir / f"{filename}.png"
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
        print(f"[{idx}/{total}] OK   {path.name} ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"[{idx}/{total}] FAIL {filename}: {e}")
        return False


async def main():
    total = len(IMAGES)
    ok = 0
    for idx, (out_dir, fname, prompt) in enumerate(IMAGES, start=1):
        if await gen_one(idx, total, out_dir, fname, prompt):
            ok += 1
    print(f"\nDone — {ok}/{total} succeeded.")


if __name__ == "__main__":
    asyncio.run(main())
