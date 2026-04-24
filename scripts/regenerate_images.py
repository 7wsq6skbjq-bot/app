"""
Regenerate specific Portech images that didn't turn out well.
- technician-hands : Intervention / installation showcase
- panic-bar       : Installation de quincaillerie service card
- before-problem + after-fixed : must be the SAME door, same angle, just different state.
  We generate before FIRST, then pass it as reference image to generate after.
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/generated")
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def gen_simple(filename: str, prompt: str) -> Path:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"portech-regen-{filename}",
        system_message="You are a professional commercial-architecture photography AI.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    _t, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        raise RuntimeError(f"No image returned for {filename}")
    path = OUT_DIR / f"{filename}.png"
    path.write_bytes(base64.b64decode(images[0]["data"]))
    print(f"✅ {filename}.png ({path.stat().st_size // 1024} KB)")
    return path


async def gen_with_reference(filename: str, prompt: str, reference_path: Path) -> Path:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    img_b64 = base64.b64encode(reference_path.read_bytes()).decode("utf-8")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"portech-regen-ref-{filename}",
        system_message="You are a professional commercial-architecture photography AI.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    _t, images = await chat.send_message_multimodal_response(
        UserMessage(text=prompt, file_contents=[ImageContent(img_b64)])
    )
    if not images:
        raise RuntimeError(f"No image returned for {filename}")
    path = OUT_DIR / f"{filename}.png"
    path.write_bytes(base64.b64decode(images[0]["data"]))
    print(f"✅ {filename}.png (via ref) ({path.stat().st_size // 1024} KB)")
    return path


STYLE = (
    "Ultra photorealistic commercial photography. Shot with a 50mm lens, "
    "natural daylight mixed with warm interior lighting. "
    "Editorial documentary style, no text, no logos, no faces visible, "
    "realistic human anatomy (hands must have exactly five fingers, no distortion), "
    "sharp focus, shallow depth of field, 16:9 landscape framing."
)


async def main():
    # -----------------------------------------------------------
    # 1) technician-hands (Intervention / installation showcase)
    # -----------------------------------------------------------
    tech_prompt = (
        "A close-up professional documentary photograph of a male worker's hands "
        "(wearing navy-blue work gloves) using a cordless electric drill to mount "
        "a commercial mortise lock on the edge of a matte-black aluminum commercial door. "
        "The door is vertical in frame, the lock is half-installed with the faceplate "
        "screws visible. The worker's torso is partially visible wearing a dark work jacket. "
        "NO FACE in frame. The hands must look natural and realistic (five fingers each, "
        "proper proportions). Background is slightly out of focus — a commercial workshop "
        "with metallic shelving. The overall color palette is navy-blue, brushed metal, "
        "and warm wood accents. " + STYLE
    )
    await gen_simple("technician-hands", tech_prompt)

    # -----------------------------------------------------------
    # 2) panic-bar (Installation de quincaillerie)
    # -----------------------------------------------------------
    panic_prompt = (
        "An extreme close-up product photograph of a brand-new stainless steel "
        "commercial panic bar (crash bar / exit device) freshly installed horizontally "
        "across a matte-black aluminum commercial double door. "
        "The panic bar is pristine, highly reflective, with visible Von Duprin / "
        "Sargent-style mechanism. Small hex screws visible. "
        "The door handle side is slightly visible to the right. "
        "Lighting is cool daylight from the left, casting subtle navy-blue shadows on "
        "the brushed metal. No people. No text. No logos. Shot like a high-end "
        "architectural product catalog. Crisp, sharp, industrial. " + STYLE
    )
    await gen_simple("panic-bar", panic_prompt)

    # -----------------------------------------------------------
    # 3) before-problem — will be the SOURCE of the after image
    # -----------------------------------------------------------
    before_prompt = (
        "A wide documentary photograph of the INTERIOR side of a worn commercial "
        "aluminum door (beige/off-white frame, scuffed and scratched). "
        "Mounted on the door: an OLD, visibly worn stainless steel commercial panic bar "
        "with scratches, stains, peeling paint around the mounting screws, a misaligned "
        "strike plate at the top, and a dented door closer arm with oil leaking. "
        "The door handle has a bent lever. Lighting is flat, slightly yellow, like an "
        "old fluorescent tube — making everything look tired and neglected. "
        "The door is centered, seen from a slight 3/4 angle. Empty commercial corridor "
        "in the background (slightly blurred). Shows all the small problems clearly. "
        + STYLE
    )
    before_path = await gen_simple("before-problem", before_prompt)

    # -----------------------------------------------------------
    # 4) after-fixed — USES before image as reference
    # -----------------------------------------------------------
    after_prompt = (
        "Using the commercial door shown in the reference image as the starting point, "
        "generate a NEW image of the EXACT SAME DOOR (same aluminum frame, same "
        "interior corridor, same camera angle and distance, same 3/4 perspective) — "
        "but now completely restored and renovated by a professional technician: \n"
        "- Frame cleaned and repainted (uniform matte finish, no scratches)\n"
        "- Brand-new polished stainless-steel commercial panic bar (no scratches, "
        "perfectly aligned horizontally)\n"
        "- New chrome door closer with clean arm (no leaks)\n"
        "- New straight lever handle (no bend)\n"
        "- New aligned strike plate at the top\n"
        "- Lighting is now cool, bright, natural daylight (not yellow fluorescent)\n"
        "- Overall atmosphere: clean, crisp, professional, freshly installed, pride-of-"
        "workmanship. Keep the same door shape, same corridor, same perspective so the "
        "two photos can be placed side-by-side as a believable before/after pair. "
        + STYLE
    )
    await gen_with_reference("after-fixed", after_prompt, before_path)


if __name__ == "__main__":
    asyncio.run(main())
