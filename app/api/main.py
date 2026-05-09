from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from sqlalchemy import select, text
import asyncio
import httpx
import io
import base64
import json
import sys
import uuid

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



def _validate_ocr(result: dict) -> None:
    if not result.get("full_text", "").strip():
        raise ValueError("OCR full_text is empty")


def _validate_caption(text_val: str) -> None:
    if len(text_val.strip()) <= 10:
        raise ValueError(f"Caption too short ({len(text_val.strip())} chars)")


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


async def _update(record_id, **fields) -> None:
    try:
        async with AsyncSessionLocal() as session:
            record = await session.get(MemeRequest, record_id)
            if record:
                for k, v in fields.items():
                    setattr(record, k, v)
                await session.commit()
    except Exception as e:
        print(f"DB update failed: {e}", file=sys.stderr)


async def _save(record: MemeRequest) -> None:
    try:
        async with AsyncSessionLocal() as session:
            session.add(record)
            await session.commit()
    except Exception as e:
        print(f"DB save failed: {e}", file=sys.stderr)


def _meme_to_dict(r: MemeRequest) -> dict:
    return {
        "id": str(r.id),
        "card_id": str(r.card_id),
        "status": r.status,
        "current_step": r.current_step,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "ocr_full_text": r.ocr_full_text,
        "visual_context": r.visual_context,
        "humor_analysis": r.humor_analysis,
        "literal_translation": r.literal_translation,
        "explanation_ru": r.explanation_ru,
        "explanation_en": r.explanation_en,
        "full_text_en": r.full_text_en,
        "blocks_en": r.blocks_en,
        "original_image_url": r.original_image_url,
        "clean_image_url": r.clean_image_url,
        "result_image_url": r.result_image_url,
        "error": r.error,
    }


async def run_pipeline(record_id: uuid.UUID, raw: bytes) -> None:
    img = Image.open(io.BytesIO(raw))

    # OCR
    await _update(record_id, current_step="ocr")
    try:
        ocr_result, ocr_retries = await call_with_retry(ocr, img, validate=_validate_ocr)
    except Exception as e:
        await _update(record_id, status="error", current_step="error", error=f"ocr: {e}")
        return
    await _update(
        record_id,
        ocr_done_at=datetime.now(timezone.utc),
        ocr_retries=ocr_retries,
        ocr_blocks=ocr_result["blocks"],
        ocr_full_text=ocr_result.get("full_text"),
        current_step="remove_text",
    )

    # Удаление текста
    try:
        clean_img, _ = await call_with_retry(remove_text, img, ocr_result["blocks"])
    except Exception as e:
        await _update(record_id, status="error", current_step="error", error=f"remove_text: {e}")
        return
    await _update(
        record_id,
        remove_text_done_at=datetime.now(timezone.utc),
        current_step="caption",
    )

    # Описание
    try:
        description, caption_retries = await call_with_retry(caption, clean_img, validate=_validate_caption)
    except Exception as e:
        await _update(record_id, status="error", current_step="error", error=f"caption: {e}")
        return
    await _update(
        record_id,
        caption_done_at=datetime.now(timezone.utc),
        caption_retries=caption_retries,
        visual_context=description,
        current_step="translate",
    )

    # Перевод
    try:
        translate_result, _ = await call_with_retry(translate, img, clean_img, ocr_result, description)
    except Exception as e:
        await _update(record_id, status="error", current_step="error", error=f"translate: {e}")
        return
    await _update(
        record_id,
        translate_done_at=datetime.now(timezone.utc),
        humor_analysis=translate_result.get("analysis"),
        literal_translation=translate_result.get("literal_translation"),
        humor_analysis_retries=translate_result.get("humor_retries", 0),
        translation_retries=translate_result.get("translation_retries", 0),
        explanation_ru=translate_result.get("explanation_ru"),
        explanation_en=translate_result.get("explanation_en"),
        full_text_en=translate_result.get("full_text_en"),
        blocks_en=translate_result.get("blocks_en"),
        current_step="upload",
    )

    # S3
    try:
        original_url = upload_image(Image.open(io.BytesIO(raw)), folder="memes/original")
        clean_url = upload_image(clean_img, folder="memes/clean")
        result_img = Image.open(io.BytesIO(base64.b64decode(translate_result["result_image_base64"])))
        result_url = upload_image(result_img, folder="memes/result")
    except Exception as e:
        await _update(record_id, status="error", current_step="error", error=f"s3: {e}")
        return

    await _update(
        record_id,
        original_image_url=original_url,
        clean_image_url=clean_url,
        result_image_url=result_url,
        completed_at=datetime.now(timezone.utc),
        status="success",
        current_step="done",
    )


@app.post("/process")
async def process(file: UploadFile, background_tasks: BackgroundTasks):
    raw = await file.read()
    card_id = uuid.uuid4()
    record = MemeRequest(
        card_id=card_id,
        started_at=datetime.now(timezone.utc),
        status="processing",
        current_step="ocr",
    )
    await _save(record)
    background_tasks.add_task(run_pipeline, record.id, raw)
    return {"card_id": str(card_id)}


@app.get("/memes")
async def list_memes():
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("""
                SELECT DISTINCT ON (card_id) *
                FROM meme_requests
                WHERE deleted = false
                ORDER BY card_id, started_at DESC
            """)
        )
        records = rows.mappings().all()
    return [dict(r) for r in records]


@app.get("/memes/{card_id}")
async def get_meme(card_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.card_id == card_id, MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
    if not record:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return _meme_to_dict(record)


@app.delete("/memes/{card_id}", status_code=204)
async def delete_meme(card_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.card_id == card_id, MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            record.deleted = True
            await session.commit()


@app.post("/memes/{card_id}/regenerate")
async def regenerate_meme(card_id: uuid.UUID, background_tasks: BackgroundTasks):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.card_id == card_id, MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.desc())
            .limit(1)
        )
        old = result.scalar_one_or_none()
        if not old:
            return JSONResponse(status_code=404, content={"error": "not found"})
        original_url = old.original_image_url
        old.deleted = True
        await session.commit()

    # Скачиваем оригинал из S3
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(original_url)
        resp.raise_for_status()
        raw = resp.content

    new_record = MemeRequest(
        card_id=card_id,
        started_at=datetime.now(timezone.utc),
        status="processing",
        current_step="ocr",
    )
    await _save(new_record)
    background_tasks.add_task(run_pipeline, new_record.id, raw)
    return {"card_id": str(card_id)}


@app.get("/memes/{card_id}/events")
async def meme_events(card_id: uuid.UUID):
    async def stream():
        while True:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(MemeRequest)
                    .where(MemeRequest.card_id == card_id, MemeRequest.deleted == False)
                    .order_by(MemeRequest.started_at.desc())
                    .limit(1)
                )
                record = result.scalar_one_or_none()

            if not record:
                yield f"data: {json.dumps({'status': 'error', 'current_step': 'error'})}\n\n"
                break

            payload = json.dumps({
                "status": record.status,
                "current_step": record.current_step,
            })
            yield f"data: {payload}\n\n"

            if record.status in ("success", "error"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")
