import httpx
from PIL import Image
import io

OCR_URL = "http://ocr_service:8001"
VISION_URL = "http://vision_service:8002"


async def ocr(img: Image.Image) -> dict:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{OCR_URL}/ocr", files={"file": ("img.png", buf, "image/png")})
        r.raise_for_status()
        return r.json()


async def remove_text(img: Image.Image, blocks: list) -> Image.Image:
    import json
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            f"{VISION_URL}/remove-text",
            files={"file": ("img.png", buf, "image/png")},
            params={"blocks": json.dumps(blocks)},
        )
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content))


async def caption(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(f"{VISION_URL}/caption", files={"file": ("img.jpg", buf, "image/jpeg")})
        r.raise_for_status()
        return r.json()["caption"]