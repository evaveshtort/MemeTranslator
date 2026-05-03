from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
import base64
import sys

from .client import ocr, remove_text, caption, translate
from .s3 import upload_image
from .database import create_tables, AsyncSessionLocal
from .models import MemeRequest

MAX_RETRIES = 3


@asynccontextmanager
async def lifespan(app):
    await create_tables()
    yield

app = FastAPI(lifespan=lifespan)


def _validate_ocr(result: dict) -> None:
    if not result.get("full_text", "").strip():
        raise ValueError("OCR full_text is empty")


def _validate_caption(text: str) -> None:
    if len(text.strip()) <= 10:
        raise ValueError(f"Caption too short ({len(text.strip())} chars)")


async def call_with_retry(fn, *args, validate=None, **kwargs):
    last_err = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await fn(*args, **kwargs)
            if validate is not None:
                validate(result)
            return result, attempt 
        except Exception as e:
            last_err = e
    raise last_err


async def _save(record: MemeRequest) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(record)
            await session.commit()
    except Exception as e:
        print(f"DB save failed: {e}", file=sys.stderr)


@app.post("/process")
async def process(file: UploadFile):
    started_at = datetime.now(timezone.utc)
    record = MemeRequest(started_at=started_at, status="processing")

    raw = await file.read()
    img = Image.open(io.BytesIO(raw))

    try:
        ocr_result, ocr_retries = await call_with_retry(ocr, img, validate=_validate_ocr)
    except Exception as e:
        record.status = "error"
        record.error = f"ocr: {e}"
        await _save(record)
        return JSONResponse(status_code=500, content={"error": f"ocr failed: {e}"})
    record.ocr_done_at = datetime.now(timezone.utc)
    record.ocr_retries = ocr_retries
    record.ocr_blocks = ocr_result["blocks"]
    record.ocr_full_text = ocr_result.get("full_text")

    try:
        clean_img, _ = await call_with_retry(remove_text, img, ocr_result["blocks"])
    except Exception as e:
        record.status = "error"
        record.error = f"remove_text: {e}"
        await _save(record)
        return JSONResponse(status_code=500, content={"error": f"remove_text failed: {e}"})
    record.remove_text_done_at = datetime.now(timezone.utc)

    try:
        description, caption_retries = await call_with_retry(caption, clean_img, validate=_validate_caption)
    except Exception as e:
        record.status = "error"
        record.error = f"caption: {e}"
        await _save(record)
        return JSONResponse(status_code=500, content={"error": f"caption failed: {e}"})
    record.caption_done_at = datetime.now(timezone.utc)
    record.caption_retries = caption_retries
    record.visual_context = description

    try:
        translate_result, _ = await call_with_retry(translate, img, clean_img, ocr_result, description)
    except Exception as e:
        record.status = "error"
        record.error = f"translate: {e}"
        await _save(record)
        return JSONResponse(status_code=500, content={"error": f"translate failed: {e}"})
    record.translate_done_at = datetime.now(timezone.utc)
    record.humor_analysis = translate_result.get("analysis")
    record.humor_analysis_retries = translate_result.get("humor_retries", 0)
    record.translation_retries = translate_result.get("translation_retries", 0)
    record.explanation_ru = translate_result.get("explanation_ru")
    record.explanation_en = translate_result.get("explanation_en")
    record.full_text_en = translate_result.get("full_text_en")
    record.blocks_en = translate_result.get("blocks_en")

    try:
        original_url = upload_image(Image.open(io.BytesIO(raw)), folder="memes/original")
        clean_url = upload_image(clean_img, folder="memes/clean")
        result_img = Image.open(io.BytesIO(base64.b64decode(translate_result["result_image_base64"])))
        result_url = upload_image(result_img, folder="memes/result")
    except Exception as e:
        record.status = "error"
        record.error = f"s3 upload: {e}"
        await _save(record)
        return JSONResponse(status_code=500, content={"error": f"s3 upload failed: {e}"})
    record.original_image_url = original_url
    record.clean_image_url = clean_url
    record.result_image_url = result_url

    record.completed_at = datetime.now(timezone.utc)
    record.status = "success"
    await _save(record)

    return {
        "ocr": ocr_result,
        "caption": description,
        "original_image_url": original_url,
        "clean_image_url": clean_url,
        "analysis": translate_result.get("analysis"),
        "explanation_ru": translate_result.get("explanation_ru"),
        "explanation_en": translate_result.get("explanation_en"),
        "full_text_en": translate_result.get("full_text_en"),
        "blocks_en": translate_result.get("blocks_en"),
        "result_image_url": result_url,
    }
