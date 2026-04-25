"""
Iter 8 — Regenerate problematic images with strict new constraints:
- Every visible technician wears a BLACK hoodie / polo / t-shirt with "PORTECH"
  in WHITE letters (large across the back, OR small on the chest left side).
- ALL power tools are DEWALT yellow-and-black.
- ALL visible text/signage is in FRENCH (SORTIE not EXIT, etc.).
- Strictly COMMERCIAL aluminum doors. NEVER residential.
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

BRAND_RULE = (
    "If a technician is visible, he must wear a SOLID BLACK hoodie, polo or t-shirt "
    "with the word 'PORTECH' clearly printed in WHITE block-letter typography "
    "(either LARGE across the upper back, OR SMALL on the left chest). The 'PORTECH' "
    "text must be sharp, legible, white-on-black. No other branding visible."
)
TOOL_RULE = (
    "Every power tool visible (drill, impact driver, screwdriver, etc.) must be a "
    "DeWALT-branded YELLOW and BLACK power tool with the recognizable yellow body "
    "and black grip. No other tool brands."
)
TEXT_RULE = (
    "Any visible signage, sticker or text in the image MUST be in FRENCH "
    "(use 'SORTIE' for exit signs, French shop signage, etc.). Absolutely no English text."
)
COMMERCIAL_RULE = (
    "Strictly COMMERCIAL aluminum or steel doors (storefront, office tower, school, "
    "hospital, mall, restaurant). ABSOLUTELY NO residential / home / wooden front doors."
)

STYLE = (
    "Ultra photorealistic editorial photography, 50mm or 85mm lens, natural industrial "
    "lighting, navy-blue (#1E3A5F) ambient tones with brushed-metal accents, cinematic "
    "depth of field, clean composition, documentary feel, 16:9 landscape framing. "
    f"{COMMERCIAL_RULE} {BRAND_RULE} {TOOL_RULE} {TEXT_RULE}"
)

# Filename, prompt
IMAGES = [
    # ===== GALERIE — Interventions =====
    ("gal-interv-1",
     "Wide medium shot of a male technician (face hidden / 3/4 from behind) installing a "
     "brushed-stainless commercial lever HANDLE on the RIGHT-hand stile of an aluminum "
     "commercial storefront door (handle pointing to the LEFT — mirrored from the typical "
     "shot). Technician wears a black PORTECH hoodie (PORTECH visible across the back in "
     "white block letters). DeWalt yellow impact driver visible on a small toolcart. "
     "Background: bright modern office reception lobby with navy-blue accent wall."),
    ("gal-interv-2",
     "Close-up shot of a hydraulic surface-mounted door closer being installed on the TOP "
     "of an aluminum commercial door — the closer BODY is mounted on the DOOR LEAF, and the "
     "ARM's foot bracket is anchored on the DOOR FRAME (the head jamb), exactly as a real "
     "commercial install. Show the technician's gloved hands torquing a screw on the FOOT "
     "BRACKET attached to the FRAME. Technician wears black PORTECH polo (small white "
     "'PORTECH' on left chest visible). DeWalt yellow impact driver in foreground."),
    ("gal-interv-3",
     "Close-up shot of a male technician's gloved hand using a DeWalt yellow drill driver "
     "to install a continuous geared hinge on the EDGE (hinge stile) of a heavy aluminum "
     "commercial door — the operator drives the screw THROUGH the hinge leaf INTO the "
     "door edge, in the correct hinge-screw position. Technician's black PORTECH t-shirt "
     "sleeve visible (small white PORTECH logo). Brushed-aluminum door grain visible."),
    ("gal-interv-4",
     "Studio macro shot of a REAL commercial mortise lock (Schlage L-series style) being "
     "inserted into the mortise pocket of a brushed aluminum commercial door, with a "
     "high-security keyed cylinder partially threaded into the lock body. Show the "
     "stainless faceplate with two screw holes, the latch and deadbolt clearly visible — "
     "this must look like an actual industry-standard mortise lock, not a fictional one. "
     "Technician's gloved hand (with black PORTECH hoodie sleeve, small white PORTECH "
     "logo) holding the cylinder."),

    # ===== GALERIE — Chantiers (replace gal-chantier-2) =====
    ("gal-chantier-2",
     "Wide editorial shot of a male technician working on a commercial aluminum door inside "
     "a luxurious high-end CONDO TOWER LOBBY in downtown Montreal — marble floor, navy-blue "
     "feature wall, brushed stainless elevator doors in soft focus background. Technician "
     "viewed from 3/4 back (face not visible), wearing a SOLID BLACK PORTECH HOODIE with "
     "large WHITE 'PORTECH' lettering across the upper back, perfectly legible. He is "
     "kneeling/crouching to adjust hardware on the lower part of a tall aluminum-framed "
     "glass commercial door. DeWalt yellow tools laid out neatly on a black mat next to him. "
     "Cinematic, luxurious, prestigious atmosphere."),

    # ===== GALERIE — Dispositifs de sortie =====
    ("gal-exit-1",
     "Wide medium shot of a chrome RIM panic device (touchpad horizontal exit bar) "
     "installed on a single aluminum commercial exit door, the bar HORIZONTALLY MIRRORED so "
     "the LATCH side is on the RIGHT and the HINGE side on the LEFT (opposite of typical). "
     "Above the door, a backlit FRENCH 'SORTIE' exit sign is glowing softly. Concrete-floor "
     "corridor in the background, navy-blue lighting."),
    ("gal-exit-4",
     "Macro close-up of a chrome touchpad-style commercial panic exit device being lightly "
     "pressed — clearly show the LATCH MECHANISM emerging from the END of the PANIC BAR "
     "ITSELF (not from the door frame), retracting into the bar's housing. The latch is a "
     "stainless tongue attached to the bar end. Aluminum commercial door stile visible "
     "below the bar, cool navy-blue side lighting."),

    # ===== GALERIE — Barres antipaniques (4 full reshoots) =====
    ("gal-panic-1",
     "Editorial wide shot of a heavy-duty horizontal panic bar (Von Duprin-style) "
     "professionally installed on a single aluminum commercial back-of-house exit door of "
     "a downtown Montreal retail store. The bar is correctly mounted at waist height, "
     "ALL hardware clearly legitimate: end caps, touchpad center, latch on the latch-side "
     "end. Above the door, a backlit FRENCH 'SORTIE' exit sign glows. Polished concrete "
     "loading area visible through a small wired-glass vision panel."),
    ("gal-panic-2",
     "Editorial medium shot of a brushed-stainless commercial panic exit device with "
     "cylinder-dogging feature, installed on an aluminum commercial double-leaf exit door "
     "in a movie theater lobby corridor. The bar is at the correct waist height, the "
     "cylinder is on the LATCH side, navy-blue carpet. Backlit FRENCH 'SORTIE' sign above. "
     "All proportions and mounting points realistic."),
    ("gal-panic-3",
     "Editorial wide shot of a black-anodized aluminum-finish commercial panic bar correctly "
     "mounted on a pair of aluminum commercial double doors at the back of a pharmacy. "
     "The two bar segments meet at the center mullion, end caps visible, latch hardware "
     "real and proportional. Fluorescent ceiling reflection on polished tile. Backlit "
     "FRENCH 'SORTIE' sign above the door."),
    ("gal-panic-4",
     "Editorial close-up of an electrified commercial panic exit device with a request-to-"
     "exit (REX) module, installed on a single aluminum commercial secure-zone door. "
     "A discreet electrified hinge wire (armored cable) runs into the door edge. The bar "
     "is the touchpad type, real Von-Duprin / Sargent-style proportions. Backlit FRENCH "
     "'SORTIE' sign overhead. Navy-blue secure corridor in background."),

    # ===== GALERIE — Serrures (2 reshoots) =====
    ("gal-lock-1",
     "Editorial macro shot of a REAL commercial mortise lock body (Schlage L-series / "
     "Sargent 8200 style) partially exposed inside the mortise pocket of an aluminum "
     "commercial door stile. Show the stainless faceplate with two visible screws, the "
     "latch bolt, the deadbolt, and the lock case interior — anatomically correct. "
     "Aluminum brushed door grain visible. Workshop background in soft navy-blue focus, "
     "DeWalt yellow tools partially visible on a workbench."),
    ("gal-lock-3",
     "Editorial product / install shot of a REAL commercial electronic mortise lock with "
     "an integrated key-card / RFID reader (Schlage AD-300 / dormakaba E-Plex style) "
     "installed on a brushed aluminum commercial door of a corporate secure room. The "
     "card-reader window glows a soft green LED. The lever handle and escutcheon are "
     "real industry-standard proportions. French-language electronic SORTIE sign above. "
     "Navy-blue corridor in background."),

    # ===== SERVICES =====
    ("services-installation",
     "Wide editorial shot of a male technician (face hidden / 3/4 back) installing a "
     "brushed-stainless commercial cylindrical leverset on an aluminum commercial office "
     "door. Technician wears a SOLID BLACK PORTECH HOODIE with LARGE WHITE 'PORTECH' "
     "lettering across the upper back, fully legible. He uses a DeWalt yellow impact "
     "driver on the leverset. Modern office interior background, navy-blue accent wall, "
     "polished concrete floor. Cinematic, high-end install context."),
    ("services-machining",
     "Wide editorial shot of an aluminum commercial door section clamped on a workshop "
     "bench, while a male technician uses a DeWalt yellow router (yellow body, black "
     "grip) to cut a fresh mortise pocket into the door stile. Aluminum chips visible, "
     "the technician wears a black PORTECH polo (small white 'PORTECH' logo on the left "
     "chest). Industrial workshop lit with navy-blue accents, organized tool wall in "
     "background. Sharp focus on the router bit and the door."),
    ("services-repair",
     "Wide editorial shot of a male technician (3/4 back, face hidden) adjusting a "
     "hydraulic surface-mounted door closer at the top of an aluminum commercial interior "
     "door using a DeWalt yellow Allen-bit driver. The closer body is on the door leaf and "
     "the foot bracket on the head jamb (frame), correctly mounted. Technician wears black "
     "PORTECH hoodie with LARGE WHITE 'PORTECH' lettering across the upper back. Office "
     "corridor with navy-blue lighting in background."),
]


async def gen_one(idx: int, total: int, filename: str, prompt: str) -> bool:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    full_prompt = f"{prompt}\n\n{STYLE}"
    chat = LlmChat(
        api_key=api_key,
        session_id=f"portech-iter8-{filename}",
        system_message=(
            "You are a professional commercial architectural photography AI. "
            "Generate ONE photorealistic image. Strictly commercial. "
            "The technician must be wearing PORTECH-branded black workwear. "
            "All power tools must be DeWalt yellow-and-black. "
            "All visible text must be in French."
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
            print(f"[{idx}/{total}] ❌ {filename}: no image returned")
            return False
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        path.write_bytes(image_bytes)
        print(f"[{idx}/{total}] ✅ {filename}.png ({len(image_bytes) // 1024} KB)")
        return True
    except Exception as e:
        print(f"[{idx}/{total}] ❌ {filename}: {e}")
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
