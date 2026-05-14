from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile
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

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from .client import ocr, remove_text, caption, translate
from .s3 import upload_image
from .database import create_tables, AsyncSessionLocal
from .models import MemeRequest, User
from .auth import hash_password, verify_password, create_token, decode_token


class AuthBody(BaseModel):
    email: str
    password: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def optional_user(token: str | None = Depends(oauth2_scheme)):
    if not token:
        return None
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        return None
    return {"id": sub, "email": payload.get("email", "")}


async def required_user(user=Depends(optional_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

MAX_RETRIES = 3


class RetryError(Exception):
    def __init__(self, cause, last_result=None):
        super().__init__(str(cause))
        self.__cause__ = cause
        self.last_result = last_result

_pending_images: dict[uuid.UUID, bytes] = {}
_last_processed_user: str | None = None
_worker_event: asyncio.Event = None 

_embed_model = None


def _embed_sync(query: str) -> list[float]:
    global _embed_model
    if _embed_model is None:
        from fastembed import TextEmbedding
        _embed_model = TextEmbedding("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return next(_embed_model.embed([query])).tolist()


async def _pick_next() -> tuple["MemeRequest | None", "bytes | None"]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.status == "queued", MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.asc())
        )
        queued = result.scalars().all()

    if not queued:
        return None, None

    other = [r for r in queued if str(r.user_id) != _last_processed_user]
    record = other[0] if other else queued[0]

    raw = _pending_images.pop(record.id, None)
    if raw is None:
        await _update(record.id, status="error", current_step="error",
                      error="ocr: данные изображения утеряны после перезапуска")
        return await _pick_next()

    return record, raw


async def _compute_queue_position(record: "MemeRequest") -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.status == "queued", MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.asc())
        )
        queued = result.scalars().all()

    remaining = list(queued)
    position = 0
    last_user = _last_processed_user

    while remaining:
        other = [r for r in remaining if str(r.user_id) != last_user]
        next_req = other[0] if other else remaining[0]
        if next_req.id == record.id:
            return position
        position += 1
        last_user = str(next_req.user_id)
        remaining.remove(next_req)

    return position


async def _worker_loop():
    global _last_processed_user
    while True:
        record, raw = await _pick_next()
        if record is None:
            await _worker_event.wait()
            _worker_event.clear()
            continue

        _last_processed_user = str(record.user_id)
        await _update(record.id, status="processing", current_step="ocr")
        try:
            await run_pipeline(record.id, raw, preset_original_url=record.original_image_url)
        except Exception as e:
            await _update(record.id, status="error", current_step="error",
                          error=f"pipeline: {e}")


@asynccontextmanager
async def lifespan(app):
    global _worker_event
    await create_tables()
    async with AsyncSessionLocal() as session:
        await session.execute(text(
            "UPDATE meme_requests SET status='error', current_step='error', "
            "error='ocr: сервер был перезапущен во время обработки' "
            "WHERE status IN ('queued', 'processing')"
        ))
        await session.commit()
    _worker_event = asyncio.Event()
    worker = asyncio.create_task(_worker_loop())
    yield
    worker.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



def _validate_ocr(result: dict) -> None:
    import unicodedata
    text = result.get("full_text", "").strip()
    if not text:
        raise ValueError("на картинке не обнаружен текст")
    letters = [ch for ch in text if unicodedata.category(ch).startswith("L")]
    if letters:
        cyrillic_ratio = sum(1 for ch in letters if "Ѐ" <= ch <= "ӿ") / len(letters)
        if cyrillic_ratio < 0.9:
            raise ValueError("текст на картинке не на русском языке")


def _validate_caption(text_val: str) -> None:
    if len(text_val.strip()) <= 10:
        raise ValueError("не удалось получить описание изображения")


async def call_with_retry(fn, *args, validate=None, **kwargs):
    last_err = None
    last_result = None
    for attempt in range(MAX_RETRIES):
        try:
            result = await fn(*args, **kwargs)
            last_result = result
            if validate is not None:
                validate(result)
            return result, attempt
        except Exception as e:
            last_err = e
    raise RetryError(last_err, last_result)


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


async def _update_search_fields(record_id: uuid.UUID) -> None:
    rid = str(record_id)
    try:
        async with AsyncSessionLocal() as session:
            row = await session.execute(
                text(
                    "SELECT ocr_full_text, full_text_en, visual_context, "
                    "explanation_ru, explanation_en FROM meme_requests WHERE id = :id"
                ),
                {"id": rid},
            )
            r = row.mappings().one_or_none()
        if not r:
            return
    except Exception as e:
        print(f"Search fields fetch failed: {e}", file=sys.stderr)
        return

    # Update search_vector (always)
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("""
                UPDATE meme_requests SET search_vector =
                    setweight(to_tsvector('russian', :ocr_text), 'A') ||
                    setweight(to_tsvector('russian', :exp_ru),   'B') ||
                    setweight(to_tsvector('english', :full_en),  'A') ||
                    setweight(to_tsvector('english', :exp_en),   'B') ||
                    setweight(to_tsvector('english', :visual),   'C')
                WHERE id = :id
            """), {
                "ocr_text": r["ocr_full_text"] or "",
                "exp_ru":   r["explanation_ru"] or "",
                "full_en":  r["full_text_en"] or "",
                "exp_en":   r["explanation_en"] or "",
                "visual":   r["visual_context"] or "",
                "id": rid,
            })
            await session.commit()
    except Exception as e:
        print(f"search_vector update failed: {e}", file=sys.stderr)

    # Update search_embedding (separately, so vector failure doesn't break FTS)
    try:
        combined = " ".join(filter(None, [
            r["ocr_full_text"], r["full_text_en"], r["visual_context"],
            r["explanation_ru"], r["explanation_en"],
        ]))
        if not combined.strip():
            return
        vec = await asyncio.get_event_loop().run_in_executor(None, _embed_sync, combined)
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
        async with AsyncSessionLocal() as session:
            await session.execute(text(
                "UPDATE meme_requests SET search_embedding = CAST(:embed AS vector) WHERE id = :id"
            ), {"embed": embedding_str, "id": rid})
            await session.commit()
    except Exception as e:
        print(f"search_embedding update failed: {e}", file=sys.stderr)


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
        "user_id": str(r.user_id) if r.user_id else None,
        "ocr_retries": r.ocr_retries,
        "caption_retries": r.caption_retries,
        "humor_analysis_retries": r.humor_analysis_retries,
        "translation_retries": r.translation_retries,
    }


async def run_pipeline(record_id: uuid.UUID, raw: bytes, preset_original_url: str | None = None) -> None:
    img = Image.open(io.BytesIO(raw))

    await _update(record_id, current_step="ocr")
    try:
        ocr_result, ocr_retries = await call_with_retry(ocr, img, validate=_validate_ocr)
    except RetryError as e:
        await _update(record_id,
                      ocr_full_text=(e.last_result or {}).get("full_text"),
                      status="error", current_step="error", error=f"ocr: {e.__cause__ or e}")
        return
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
        original_url = preset_original_url or upload_image(Image.open(io.BytesIO(raw)), folder="memes/original")
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
    await _update_search_fields(record_id)


@app.post("/process")
async def process(file: UploadFile, user=Depends(required_user)):
    raw = await file.read()
    original_url = await asyncio.get_event_loop().run_in_executor(
        None, lambda: upload_image(Image.open(io.BytesIO(raw)), folder="memes/original")
    )
    card_id = uuid.uuid4()
    record = MemeRequest(
        card_id=card_id,
        user_id=uuid.UUID(user["id"]),
        started_at=datetime.now(timezone.utc),
        status="queued",
        current_step="queued",
        original_image_url=original_url,
    )
    await _save(record)
    _pending_images[record.id] = raw
    _worker_event.set()
    return {"card_id": str(card_id)}


@app.get("/memes")
async def list_memes():
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("""
                SELECT DISTINCT ON (card_id) *
                FROM meme_requests
                WHERE deleted = false AND status != 'error'
                ORDER BY card_id, started_at DESC
            """)
        )
        records = rows.mappings().all()
    return [dict(r) for r in records]


@app.get("/memes/search")
async def search_memes(q: str, limit: int = 20):
    if not q.strip():
        return []

    embedding_str = None
    try:
        vec = await asyncio.get_event_loop().run_in_executor(None, _embed_sync, q)
        embedding_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
    except Exception as e:
        print(f"Embed failed: {e}", file=sys.stderr)

    fts_condition = """
        (search_vector @@ websearch_to_tsquery('russian', :q)
         OR search_vector @@ websearch_to_tsquery('english', :q))
    """
    vec_condition = (
        "search_embedding IS NOT NULL AND search_embedding <=> CAST(:embed AS vector) < 0.6"
        if embedding_str else "false"
    )
    trgm_condition = """
        similarity(
            COALESCE(ocr_full_text,'') || ' ' || COALESCE(full_text_en,''),
            :q
        ) > 0.2
    """
    fts_score = """
        COALESCE(ts_rank(search_vector,
            websearch_to_tsquery('russian', :q) ||
            websearch_to_tsquery('english', :q)
        ), 0) * 3
    """
    vec_score = (
        "COALESCE(1.0 - (search_embedding <=> CAST(:embed AS vector)), 0)"
        if embedding_str else "0"
    )
    trgm_score = """
        COALESCE(similarity(
            COALESCE(ocr_full_text,'') || ' ' || COALESCE(full_text_en,''),
            :q
        ), 0)
    """

    sql = f"""
        WITH latest AS (
            SELECT DISTINCT ON (card_id) *
            FROM meme_requests
            WHERE deleted = false AND status = 'success'
            ORDER BY card_id, started_at DESC
        )
        SELECT
            id, card_id, status, current_step, started_at, completed_at,
            ocr_full_text, visual_context, humor_analysis, literal_translation,
            explanation_ru, explanation_en, full_text_en, blocks_en,
            original_image_url, clean_image_url, result_image_url, error,
            ({fts_score} + {vec_score} + {trgm_score}) AS score
        FROM latest
        WHERE {fts_condition} OR ({vec_condition}) OR ({trgm_condition})
        ORDER BY score DESC
        LIMIT :limit
    """

    params: dict = {"q": q, "limit": limit}
    if embedding_str:
        params["embed"] = embedding_str

    async with AsyncSessionLocal() as session:
        rows = await session.execute(text(sql), params)
        records = rows.mappings().all()

    return [dict(r) for r in records]


@app.get("/memes/my")
async def my_memes(user=Depends(required_user)):
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("""
                SELECT DISTINCT ON (card_id) *
                FROM meme_requests
                WHERE deleted = false AND user_id = :uid
                ORDER BY card_id, started_at DESC
            """),
            {"uid": user["id"]},
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
async def delete_meme(card_id: uuid.UUID, user=Depends(required_user)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(MemeRequest)
            .where(MemeRequest.card_id == card_id, MemeRequest.deleted == False)
            .order_by(MemeRequest.started_at.desc())
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if not record:
            return
        if record.user_id is None or str(record.user_id) != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        _pending_images.pop(record.id, None)
        record.deleted = True
        await session.commit()


@app.post("/memes/{card_id}/regenerate")
async def regenerate_meme(card_id: uuid.UUID, user=Depends(required_user)):
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
        if old.user_id is None or str(old.user_id) != user["id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
        original_url = old.original_image_url
        old.deleted = True
        await session.commit()

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(original_url)
        resp.raise_for_status()
        raw = resp.content

    new_record = MemeRequest(
        card_id=card_id,
        user_id=uuid.UUID(user["id"]),
        started_at=datetime.now(timezone.utc),
        status="queued",
        current_step="queued",
        original_image_url=original_url,
    )
    await _save(new_record)
    _pending_images[new_record.id] = raw
    _worker_event.set()
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

            data: dict = {"status": record.status, "current_step": record.current_step}
            if record.status == "queued":
                data["queue_position"] = await _compute_queue_position(record)
            yield f"data: {json.dumps(data)}\n\n"

            if record.status in ("success", "error"):
                break

            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/auth/register")
async def register(body: AuthBody):
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(User.email == body.email.lower())
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already registered")
        user = User(
            email=body.email.lower(),
            password_hash=hash_password(body.password),
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    token = create_token(str(user.id), user.email)
    return {"token": token, "user": {"id": str(user.id), "email": user.email}}


@app.post("/auth/login")
async def login(body: AuthBody):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == body.email.lower())
        )
        user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(str(user.id), user.email)
    return {"token": token, "user": {"id": str(user.id), "email": user.email}}
