"""
Generate Portech website images using Gemini Nano Banana.
Run once during setup. Saves PNGs to /app/frontend/public/generated/.
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = (
    "Ultra photorealistic, editorial photography, shot on a 50mm lens, "
    "natural industrial lighting, rich navy blue (#1E3A5F) tones with brushed metal accents, "
    "commercial interior / workshop context, cinematic depth of field, "
    "clean composition, documentary feel — no people's faces visible, "
    "no logos, no text overlays, 16:9 or 4:3 landscape framing."
)

IMAGES = [
    # filename, prompt
    (
        "hero-doors",
        "Modern glass commercial entrance door hardware in a stylish lobby. "
        "Close focus on polished stainless-steel push bar and hinge mechanism. "
        "Deep navy blue ambient lighting, dramatic shadows, high-end architectural photography.",
    ),
    (
        "panic-bar",
        "Extreme close-up of a brand-new chrome commercial panic bar (crash bar) "
        "installed on an aluminum commercial door. Sharp mechanical detail, "
        "tiny Allen screws visible, soft navy blue light reflecting off the metal.",
    ),
    (
        "door-closer",
        "Macro shot of a heavy-duty hydraulic door closer mounted on the top of "
        "a commercial aluminum door frame. Matte black arm with brass pivot. "
        "Precise and mechanical, industrial aesthetic.",
    ),
    (
        "commercial-lock",
        "Close-up of a heavy-duty commercial mortise lock and strike plate on "
        "an aluminum door. Stainless steel finish, keyway detail, "
        "navy blue shadows, precision tool photography.",
    ),
    (
        "technician-hands",
        "Close-up shot of a technician's gloved hands using a precision screwdriver "
        "to install a door lock on a commercial aluminum door. No face visible. "
        "Focus on skilled craftsmanship and clean workwear.",
    ),
    (
        "workshop-tools",
        "Overhead flat-lay of door hardware tools laid out on a dark wooden workshop bench: "
        "torque drivers, drill bits, precision calipers, Allen keys, door hardware packages. "
        "Navy blue tones, industrial order and precision.",
    ),
    (
        "commercial-entrance",
        "Exterior wide shot of a modern commercial storefront with a matte black aluminum "
        "entrance door at dusk. Warm interior glow contrasting with deep navy blue sky. "
        "Sharp architectural lines, no people.",
    ),
    (
        "school-corridor",
        "Wide shot of a clean, modern school corridor at a commercial double-door with "
        "visible panic bars. Polished floor, navy blue accent signage. "
        "Empty corridor, architectural photography.",
    ),
    (
        "before-problem",
        "A damaged old commercial door lock: visibly worn, misaligned strike plate, "
        "scratched metal, rust spots, old paint. Harsh lighting to emphasize the problem. "
        "Desaturated, slightly cold tones.",
    ),
    (
        "after-fixed",
        "A brand-new perfectly aligned chrome commercial lock on a polished aluminum door. "
        "Crisp clean install, bright natural light, visible precision in alignment and finish. "
        "High-end 'after' photo.",
    ),
    (
        "condo-lobby",
        "Interior shot of a luxurious condo tower lobby with double commercial doors, "
        "navy blue accent walls, brushed metal hardware, marble floor. "
        "Modern Quebec residential architecture feel.",
    ),
    (
        "hardware-grid",
        "Flat-lay studio shot of various commercial door hardware components arranged "
        "geometrically on a deep navy blue matte background: panic bars, lever handles, "
        "strike plates, hinges, door closers. Editorial product photography.",
    ),
    (
        "restaurant-door",
        "Close-up of a modern restaurant entrance — matte black aluminum door with "
        "brushed metal handle, navy blue signage reflection on glass. "
        "Warm interior light bleeding out. Professional hospitality architecture.",
    ),
    (
        "precision-install",
        "Close-up of a technician's hand holding a precision digital caliper measuring "
        "a door frame opening. Extremely crisp focus on the caliper's digital display. "
        "Navy blue workshop background.",
    ),
]


async def gen_one(idx: int, filename: str, prompt: str) -> None:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    full_prompt = f"{prompt}\n\n{STYLE}"
    chat = LlmChat(
        api_key=api_key,
        session_id=f"portech-img-{filename}",
        system_message="You are a professional commercial photography AI. Generate one photorealistic image as described.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    try:
        _text, images = await chat.send_message_multimodal_response(
            UserMessage(text=full_prompt)
        )
        if not images:
            print(f"[{idx}] ❌ {filename}: no image returned")
            return
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        path = OUT_DIR / f"{filename}.png"
        path.write_bytes(image_bytes)
        print(f"[{idx}] ✅ {filename}.png ({len(image_bytes) // 1024} KB)")
    except Exception as e:
        print(f"[{idx}] ❌ {filename}: {e}")


async def main():
    # Generate sequentially to avoid rate limits
    for idx, (filename, prompt) in enumerate(IMAGES, start=1):
        await gen_one(idx, filename, prompt)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
