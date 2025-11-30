# app/core/image_tool.py
"""
Image generation helper. Generates an image via OpenAI Images API if OPENAI_API_KEY set and org verified.
If key missing or blocked, can return a small PIL placeholder image (so UI can still show something).
"""

import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HAS_OPENAI = bool(OPENAI_API_KEY)

def generate_image_bytes(prompt: str, size: str = "1024x1024"):
    """
    Returns raw PNG bytes.
    If OpenAI key present, calls images API.
    Otherwise returns a generated placeholder PNG.
    """
    if HAS_OPENAI:
        try:
            import openai
            openai.api_key = OPENAI_API_KEY
            # Use DALL·E or gpt-image-1 as available in your account
            # This may raise a 403 if your org isn't verified.
            resp = openai.Image.create(prompt=prompt, n=1, size=size)
            b64 = resp["data"][0]["b64_json"]
            img_bytes = base64.b64decode(b64)
            return img_bytes
        except Exception as e:
            print("OpenAI image error:", e)
            # fall through to placeholder
    # Placeholder: draw a simple PNG with prompt text (safe demo)
    img = Image.new("RGB", (1024, 1024), color=(18, 18, 20))
    d = ImageDraw.Draw(img)
    try:
        # try a truetype font from system
        f = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        f = ImageFont.load_default()
    text = "Analogy image (placeholder)\n" + (prompt[:200] + "..." if len(prompt) > 200 else prompt)
    d.multiline_text((32, 32), text, font=f, fill=(200,200,230))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
