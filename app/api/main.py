from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
import base64

from .client import ocr, remove_text, caption, translate

app = FastAPI()
MAX_RETRIES = 3


def _validate_ocr(result: dict) -> None:
    if not result.get("full_text", "").strip():
        raise ValueError("OCR full_text is empty")


def _validate_caption(text: str) -> None:
    if len(text.strip()) <= 10:
        raise ValueError(f"Caption too short ({len(text.strip())} chars)")


async def call_with_retry(fn, *args, validate=None, **kwargs):
    last_err = None
    for _ in range(MAX_RETRIES):
        try:
            result = await fn(*args, **kwargs)
            if validate is not None:
                validate(result)
            return result
        except Exception as e:
            last_err = e
    raise last_err


@app.post("/process")
async def process(file: UploadFile):
    img = Image.open(io.BytesIO(await file.read()))

    try:
        ocr_result = await call_with_retry(ocr, img, validate=_validate_ocr)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"ocr failed: {e}"})

    try:
        clean_img = await call_with_retry(remove_text, img, ocr_result["blocks"])
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"remove_text failed: {e}"})

    try:
        description = await call_with_retry(caption, clean_img, validate=_validate_caption)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"caption failed: {e}"})

    try:
        translate_result = await call_with_retry(translate, img, clean_img, ocr_result, description)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"translate failed: {e}"})

    buf = io.BytesIO()
    clean_img.save(buf, format="PNG")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "ocr": ocr_result,
        "caption": description,
        "image_base64": img_base64,
        **translate_result,
    }
