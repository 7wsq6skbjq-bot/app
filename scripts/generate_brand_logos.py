"""
Generate clean text-only brand-logo tiles for brands where the official
logo could not be downloaded. Output: WHITE background, BLACK brand name
in the brand's signature typographical style.
"""
import asyncio
import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv("/app/backend/.env")

OUT_DIR = Path("/app/frontend/public/brands")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (filename, prompt) — generate stylised text logo tiles, all on a CLEAN WHITE background.
LOGOS = [
    ("sargent",
     "Minimalist clean text-only brand wordmark logo. The single word 'SARGENT' in BLACK "
     "uppercase serif typography, centered on a PURE WHITE background. The 'S' has a "
     "slight seriffed stroke, evoking the historical Sargent Manufacturing identity. "
     "Sharp vector style, no tagline, no extra text, no gradient. Square 800x800 "
     "minimal logo composition."),
    ("hager",
     "Minimalist clean text-only brand wordmark logo. The single word 'HAGER' in BOLD "
     "BLACK condensed sans-serif uppercase, centered on a PURE WHITE background, with "
     "a small thin red horizontal accent bar to the LEFT of the word. Square 800x800 "
     "clean vector style, no tagline."),
    ("von-duprin",
     "Minimalist clean brand wordmark logo. The two-line text 'VON' on top and 'DUPRIN' "
     "below in BOLD BLACK serif uppercase, centered on a PURE WHITE background. Sharp "
     "industrial typography, no tagline, square 800x800 composition."),
    ("lcn",
     "Minimalist clean brand wordmark logo. The three letters 'LCN' in HEAVY BLACK "
     "condensed sans-serif uppercase, centered on a PURE WHITE background. Strong, "
     "industrial, recognizable. Square 800x800 clean vector style, no tagline."),
    ("adams-rite",
     "Minimalist clean brand wordmark logo. The two-word text 'ADAMS RITE' in BLACK "
     "italic uppercase serif typography, centered on a PURE WHITE background. Vintage "
     "industrial feel. Square 800x800 clean vector style, no tagline."),
    ("corbin-russwin",
     "Minimalist clean brand wordmark logo. The two-word text 'CORBIN RUSSWIN' in BLACK "
     "uppercase serif typography on TWO LINES (CORBIN top / RUSSWIN bottom), centered on "
     "a PURE WHITE background. Classic, refined typography. Square 800x800 clean."),
    ("norton",
     "Minimalist clean brand wordmark logo. The single word 'NORTON' in BLACK uppercase "
     "sans-serif typography, centered on a PURE WHITE background, with a subtle red "
     "horizontal underline beneath the word. Industrial door-hardware feel. Square "
     "800x800 clean vector style."),
]


async def gen_one(filename, prompt):
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"brand-logo-{filename}",
        system_message="Generate ONE clean square brand wordmark logo tile, black text on white background.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
        modalities=["image", "text"]
    )
    path = OUT_DIR / f"{filename}.png"
    if path.exists() and path.stat().st_size > 50_000:
        print(f"⏭  {filename} exists")
        return True
    try:
        _t, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
        if images:
            data = base64.b64decode(images[0]["data"])
            path.write_bytes(data)
            print(f"✅ {filename} ({len(data)//1024} KB)")
            return True
    except Exception as e:
        print(f"❌ {filename}: {str(e)[:80]}")
    return False


async def main():
    for filename, prompt in LOGOS:
        await gen_one(filename, prompt)


if __name__ == "__main__":
    asyncio.run(main())
