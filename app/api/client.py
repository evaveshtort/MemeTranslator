import httpx
import json
from PIL import Image
import io

OCR_URL = "http://ocr_service:8001"
VISION_URL = "http://vision_service:8002"
TRANSLATE_URL = "http://translate_service:8003"


async def ocr(img: Image.Image) -> dict:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{OCR_URL}/ocr", files={"file": ("img.png", buf, "image/png")})
        r.raise_for_status()
        return r.json()


async def remove_text(img: Image.Image, blocks: list) -> Image.Image:
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


async def translate(
    original_img: Image.Image,
    clean_img: Image.Image,
    ocr_data: dict,
    caption_text: str,
) -> dict:
    original_buf = io.BytesIO()
    original_img.save(original_buf, format="PNG")
    original_buf.seek(0)

    clean_buf = io.BytesIO()
    clean_img.save(clean_buf, format="PNG")
    clean_buf.seek(0)

    async with httpx.AsyncClient(timeout=600) as client:
        r = await client.post(
            f"{TRANSLATE_URL}/translate",
            files={
                "original": ("original.png", original_buf, "image/png"),
                "clean": ("clean.png", clean_buf, "image/png"),
            },
            data={
                "ocr": json.dumps(ocr_data, ensure_ascii=False),
                "caption": caption_text,
            },
        )
        r.raise_for_status()
        return r.json()
