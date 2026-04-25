"""
Generate Portech portfolio images (Home / Services / Galerie / Catalogue).
ALL images are STRICTLY COMMERCIAL ALUMINUM DOORS / commercial hardware.
ZERO residential. ZERO duplicates.

Run: python3 /app/scripts/generate_portfolio_images.py
Saves PNGs to /app/frontend/public/generated/portfolio/.
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

# Hard rules baked into every prompt — repeated to make the model converge.
STYLE = (
    "Strictly COMMERCIAL setting (storefront, office tower, school, hospital, "
    "restaurant, retail, mall, factory). Aluminum or steel commercial doors ONLY. "
    "ABSOLUTELY NO residential / home / front-porch / wooden house doors. "
    "Ultra photorealistic editorial photography, shot on a 50mm or 85mm lens, "
    "natural industrial lighting, navy-blue (#1E3A5F) ambient tones with brushed "
    "stainless / black / chrome metal accents, cinematic depth of field, clean "
    "composition, documentary feel — no faces visible, no logos, no text overlays, "
    "16:9 landscape framing."
)

IMAGES = [
    # ============== HOME PAGE — 16 unique ==============
    ("home-hero",
     "Wide cinematic shot of a sleek modern commercial storefront at dusk. "
     "Black anodized aluminum entrance doors with full-height tempered glass, "
     "brushed-stainless push bars, polished concrete sidewalk. Empty street, "
     "warm interior glow visible through glazing. Architectural photography, "
     "ultra-sharp."),
    ("home-showcase-tech",
     "Close-up of a male technician's gloved hands using a torque screwdriver "
     "to install a stainless mortise lock on an aluminum commercial storefront door. "
     "Brushed-aluminum frame visible, navy-blue workwear sleeve, no face. "
     "Crisp focus on the screw-head and lock face."),
    ("home-showcase-exit",
     "Macro shot of a chrome Von-Duprin-style touchpad exit device installed on "
     "an aluminum stile-and-rail commercial door, warehouse corridor in background, "
     "soft navy-blue cool light, no logos."),
    ("home-showcase-panic",
     "Wide medium shot of a heavy-duty horizontal panic bar mounted on a pair "
     "of aluminum commercial double doors at the rear emergency exit of a "
     "shopping mall. Polished concrete floor, exit signage out of focus."),
    ("home-showcase-lock",
     "Extreme close-up of a satin-stainless commercial mortise lock cylinder and "
     "lever handle installed on a black aluminum door, brushed metal grain visible, "
     "shallow depth of field, navy-blue reflections."),
    ("home-grid-components",
     "Editorial flat-lay on a deep navy-blue matte background — geometric arrangement "
     "of various COMMERCIAL door hardware: panic bar, hydraulic closer, mortise lock, "
     "lever handle, strike plate, continuous hinge, push plate. Studio product "
     "photography, top-down."),
    ("home-service-installation",
     "Technician's hands aligning a stainless lever handle on an aluminum office-tower "
     "door, drill and bits resting on a wheeled cart in soft focus, navy-blue corporate "
     "lobby in background."),
    ("home-service-machining",
     "Close-up of a router cutting a fresh mortise pocket into an aluminum commercial "
     "door stile clamped on a workshop bench, fine aluminum chips, sharp focus on the "
     "router bit, navy-blue workshop ambient light."),
    ("home-service-repair",
     "Side view of a hydraulic surface-mounted door closer being adjusted with an "
     "Allen key on the head of an aluminum interior commercial door, navy-blue "
     "office hallway in background."),
    ("home-service-upgrade",
     "Close-up of a brand-new electronic commercial deadbolt with card reader being "
     "installed on a black aluminum office door, brushed stainless trim, navy-blue "
     "secure-area corridor."),
    ("home-client-restaurant",
     "Exterior medium shot of a high-end restaurant entrance — matte black aluminum "
     "double doors with brushed-brass push handles, dark stone facade, dim warm "
     "interior glow through glass, evening blue hour."),
    ("home-client-school",
     "Wide shot of a clean modern school main entrance — pair of aluminum commercial "
     "doors with vision panels and crash bars, polished tile floor, empty lit corridor "
     "behind, navy-blue lockers in soft focus."),
    ("home-client-condo",
     "Interior shot of a luxury condo tower lobby vestibule — full-height aluminum "
     "commercial double doors with brushed stainless pulls, marble floor, navy-blue "
     "feature wall, modern Quebec architecture."),
    ("home-client-office",
     "Modern corporate office reception — matte black aluminum framed glass doors "
     "with concealed hydraulic closer at the top, brushed-metal lever handle, "
     "navy-blue accent wall, polished concrete floor."),
    ("home-showcase-storefront",
     "Wide exterior of an upscale boutique storefront — full-height anodized aluminum "
     "framed glass entry, brushed-stainless vertical pull handle, matte black mullions, "
     "navy-blue overhead signage neutralized."),
    ("home-luxury-glass",
     "Close-up of a frameless tempered-glass pivot commercial door with brushed-stainless "
     "patch fittings and floor-mounted pivot, in a high-end hotel lobby with navy-blue "
     "marble walls."),

    # ============== SERVICES PAGE — 7 unique ==============
    ("services-hero",
     "Architectural exterior of a modern commercial building entrance with a row of "
     "anodized aluminum framed glass doors, dusk lighting, navy-blue sky, brushed metal "
     "push handles catching the warm interior light."),
    ("services-installation",
     "Close-up of a commercial cylindrical leverset being installed on an aluminum "
     "stile-and-rail door, screws partially driven in, brushed stainless finish, "
     "shallow depth-of-field, navy-blue jobsite background."),
    ("services-machining",
     "Aluminum commercial door clamped on a workshop bench while a precise template "
     "is positioned for drilling, drill bits and torque tool laid out, navy-blue "
     "industrial workshop lighting."),
    ("services-repair",
     "Macro shot of a damaged misaligned commercial strike plate on a black aluminum "
     "frame, scratch marks visible, with a technician's gloved hand holding a digital "
     "caliper to measure the gap."),
    ("services-upgrade",
     "Side-by-side composition: an old worn brass commercial mortise lock on the left "
     "and a brand-new stainless one on the right, both on aluminum door samples, "
     "studio navy-blue background."),
    ("services-consultation",
     "Architectural drawings, brushed metal door hardware swatches, lever handle "
     "sample, mortise lock sample and a navy-blue colour chart laid out on a dark "
     "studio table — top-down editorial product photography."),
    ("services-inspection",
     "Technician's hand holding a clipboard with an inspection report and pen, "
     "checking a commercial aluminum double-door installation in a corporate corridor, "
     "navy-blue lighting, focused on the report and the panic bar."),

    # ============== GALERIE — 20 unique (4 per category × 5) ==============
    # Interventions
    ("gal-interv-1",
     "Technician installing a brushed-stainless lever set on an aluminum commercial "
     "door — over-the-shoulder angle, focused on the lever and screws, navy-blue site."),
    ("gal-interv-2",
     "Hands torquing the bolts of a surface-mount hydraulic closer at the top of an "
     "aluminum commercial door frame, ladder partially visible, navy-blue ambient."),
    ("gal-interv-3",
     "Installing a continuous geared hinge on the edge of a heavy aluminum commercial "
     "door — close-up of the hinge channel and screws being driven."),
    ("gal-interv-4",
     "Inserting a high-security cylinder into an aluminum commercial mortise lock, "
     "extreme close-up on the cylinder face and brushed-stainless escutcheon."),
    # Chantiers haut de gamme
    ("gal-chantier-1",
     "Wide shot of an upscale boutique entrance under construction — frameless glass "
     "pivot door with brushed-stainless patch fittings, protective film still on the "
     "metal, navy-blue tarps in background."),
    ("gal-chantier-2",
     "Pre-assembly bench in a workshop: an aluminum commercial door section laid flat "
     "with a complete hardware kit (lock, lever, closer, hinges) ready to be installed, "
     "navy-blue overhead light."),
    ("gal-chantier-3",
     "Pair of black anodized aluminum commercial doors freshly installed at the "
     "entrance of a luxury restaurant, brushed-brass vertical pulls, soft evening "
     "navy-blue light outside."),
    ("gal-chantier-4",
     "Glass storefront elevation in a downtown office tower lobby — anodized aluminum "
     "framing, brushed-stainless push bars, navy-blue accent wall behind."),
    # Dispositifs de sortie
    ("gal-exit-1",
     "Close-up of a chrome rim panic device installed on a single aluminum commercial "
     "exit door, exit-sign glow above, navy-blue corridor."),
    ("gal-exit-2",
     "Concealed vertical-rod exit device on a pair of aluminum commercial double doors "
     "at a school auditorium emergency exit, polished tile floor."),
    ("gal-exit-3",
     "Surface vertical-rod exit device with top and bottom latches visible on aluminum "
     "double doors at a hospital service corridor, navy-blue lighting."),
    ("gal-exit-4",
     "Touchpad-style exit device close-up — chrome bar pressed slightly, aluminum door "
     "stile and weather-stripping visible, side-light navy-blue tone."),
    # Barres antipaniques
    ("gal-panic-1",
     "Horizontal black-finish panic bar on a back-of-house aluminum commercial door "
     "of a retail store, polished concrete loading dock visible through the small "
     "window."),
    ("gal-panic-2",
     "Brushed-stainless panic bar with cylinder dogging on an aluminum commercial "
     "door at a cinema lobby emergency exit, navy-blue carpet."),
    ("gal-panic-3",
     "Aluminum-anodized panic bar on a pair of pharmacy back doors, exit signage above, "
     "fluorescent ceiling reflection."),
    ("gal-panic-4",
     "Electrified panic bar with request-to-exit module on aluminum commercial door, "
     "wiring barely visible, navy-blue secure-zone door."),
    # Serrures commerciales
    ("gal-lock-1",
     "Heavy-duty stainless commercial mortise lock body partially exposed inside an "
     "aluminum door pocket, shavings cleaned, screws ready, macro photography."),
    ("gal-lock-2",
     "Cylindrical lever lockset in matte-black finish installed on an aluminum office "
     "door, brushed escutcheon trim, navy-blue corridor."),
    ("gal-lock-3",
     "Electronic mortise lock with key-card reader on a brushed aluminum commercial "
     "door of a corporate secure room, indicator LED softly glowing."),
    ("gal-lock-4",
     "Storeroom mortise lock with knurled escutcheon on a heavy aluminum stockroom "
     "door, brushed-stainless finish, navy-blue concrete wall behind."),

    # ============== CATALOGUE — 18 unique (3 per category × 6) ==============
    # Poignées & leviers
    ("cat-handle-1",
     "Studio product shot of a brushed-stainless commercial lever handle on a navy-blue "
     "matte background, isolated, editorial product photography."),
    ("cat-handle-2",
     "Studio shot of a tall vertical brushed-stainless storefront pull handle on navy-blue "
     "background, beautifully lit."),
    ("cat-handle-3",
     "Studio shot of a matte-black commercial lever handle and rose, navy-blue gradient "
     "background, sharp product photography."),
    # Serrures & cylindres
    ("cat-lock-1",
     "Studio shot of a stainless commercial mortise lock body with strike plate isolated "
     "on a navy-blue background, top-down editorial composition."),
    ("cat-lock-2",
     "Studio shot of a high-security keyed cylinder with restricted-keyway profile, "
     "isolated on navy-blue, sharp macro detail."),
    ("cat-lock-3",
     "Studio shot of a brushed-stainless commercial deadbolt with thumb-turn isolated "
     "on a navy-blue background."),
    # Barres antipaniques (catalogue)
    ("cat-panic-1",
     "Studio product shot of a horizontal touchpad exit device, isolated against navy-blue "
     "background, premium chrome finish."),
    ("cat-panic-2",
     "Studio product shot of a concealed vertical-rod exit device complete kit, top and "
     "bottom rods visible, navy-blue background."),
    ("cat-panic-3",
     "Studio shot of an electrified exit device with request-to-exit module visible, "
     "wiring tail showing, navy-blue background."),
    # Ferme-portes
    ("cat-closer-1",
     "Studio shot of a heavy-duty surface-mounted hydraulic door closer with arm and "
     "shoe, isolated on navy-blue, high-detail product photography."),
    ("cat-closer-2",
     "Studio shot of a concealed-in-frame overhead closer with adjustable arm, "
     "isolated on navy-blue."),
    ("cat-closer-3",
     "Studio shot of a floor-mounted center-pivot heavy-duty closer with cement-box "
     "cover plate, isolated on navy-blue."),
    # Contrôle d'accès
    ("cat-access-1",
     "Studio shot of a stainless commercial card reader keypad combo unit isolated on "
     "navy-blue, premium product photography."),
    ("cat-access-2",
     "Studio shot of an electric strike with faceplate isolated on navy-blue, brushed "
     "stainless finish."),
    ("cat-access-3",
     "Studio shot of a wireless smart commercial deadbolt with Bluetooth indicator, "
     "isolated on navy-blue."),
    # Charnières & pivots
    ("cat-hinge-1",
     "Studio shot of a continuous geared aluminum hinge full length, isolated on "
     "navy-blue background."),
    ("cat-hinge-2",
     "Studio shot of a heavy-duty stainless butt hinge with ball-bearing knuckles, "
     "isolated on navy-blue."),
    ("cat-hinge-3",
     "Studio shot of a center-mounted floor pivot assembly for commercial pivot doors, "
     "isolated on navy-blue background."),
]


async def gen_one(idx: int, total: int, filename: str, prompt: str) -> bool:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    full_prompt = f"{prompt}\n\n{STYLE}"
    chat = LlmChat(
        api_key=api_key,
        session_id=f"portech-portfolio-{filename}",
        system_message=(
            "You are a professional commercial architectural photography AI. "
            "Generate ONE photorealistic image. Strictly commercial — never residential."
        ),
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    path = OUT_DIR / f"{filename}.png"
    if path.exists() and path.stat().st_size > 50_000:
        print(f"[{idx}/{total}] ⏭  {filename}.png exists, skipping")
        return True
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
