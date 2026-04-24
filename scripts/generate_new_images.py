"""
Generate 3 new images for Portech site:
- heritage-torch  : transmission of knowledge from elder to younger man (chapter 05 About)
- panic-bar       : realistic chrome panic bar (replace flawed AI image)
- workshop-tools  : shelf with hardware boxes (replace flawed AI image)
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
    "Ultra photorealistic, editorial documentary photography, shot on a 50mm lens, "
    "natural light, deep navy blue (#0c182b / #1e3457) tones with brushed metal accents, "
    "cinematic depth of field, clean composition, no logos, no text overlays, "
    "16:9 landscape framing."
)

IMAGES = [
    (
        "heritage-torch",
        "Symbolic editorial photograph showing the transmission of trade knowledge "
        "between two generations. Foreground: an older skilled craftsman's experienced "
        "hands (visible weathered fingers, calloused palms, no face) handing a heavy-duty "
        "polished commercial door hardware tool — a chrome lever-handle lockset — to a "
        "younger man's hands (no face). The handover is happening above a dark wooden "
        "workshop bench softly lit by a warm overhead lamp. Background: blurred industrial "
        "workshop with door hardware on shelves, deep navy blue ambient light. "
        "Mood: respect, legacy, mentorship, passing of the torch. Warm rim light on the "
        "metal hardware to make it gleam like a torch being passed. Cinematic, emotional, "
        "no faces, no text.",
    ),
    (
        "panic-bar",
        "Hyper realistic stock photography of a brand new push-bar (panic bar / crash bar) "
        "professionally installed on a glossy painted commercial steel door, hospital corridor "
        "context. The push bar is a long horizontal stainless steel bar, satin chrome finish, "
        "with end caps and a vertical rod system. Crisp metallic detail, every screw visible, "
        "perfect alignment, sharp shadows. Door is matte light grey. Wall behind is clean "
        "neutral, soft natural lighting from a window on the left. Documentary photography style, "
        "no people, completely realistic, no defects or anomalies, no warped geometry.",
    ),
    (
        "workshop-tools",
        "Hyper realistic photograph of a tall industrial steel shelving unit in a clean "
        "professional locksmith workshop, fully stocked with neatly aligned cardboard "
        "boxes of commercial door hardware. Each box is plain unbranded brown cardboard with "
        "white labels visible but no readable text. Some boxes are partially open showing "
        "shiny chrome lever handles, lock cylinders, hinges, and strike plates inside. "
        "Warm overhead workshop lighting, deep navy blue shadows, perfectly orderly, "
        "no people, documentary style, no defects, photorealistic, every box detail crisp, "
        "no text or logos.",
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
            print(f"[{idx}] FAIL {filename}: no image returned")
            return
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        path = OUT_DIR / f"{filename}.png"
        path.write_bytes(image_bytes)
        print(f"[{idx}] OK {filename}.png ({len(image_bytes) // 1024} KB)")
    except Exception as e:
        print(f"[{idx}] FAIL {filename}: {e}")


async def main():
    for idx, (filename, prompt) in enumerate(IMAGES, start=1):
        await gen_one(idx, filename, prompt)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
