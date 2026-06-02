from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import base64
import random
import traceback
import unicodedata

from .humor_analysis import analyse_humor
from .translation import translate_meme, literal_translate
from .text_adding import add_translated_text

app = FastAPI()
MAX_RETRIES = 3


def strip_json_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def has_non_latin_letters(text: str) -> bool:
    for ch in text:
        if unicodedata.category(ch).startswith("L") and not ("a" <= ch.lower() <= "z"):
            return True
    return False


def has_non_cyrillic_letters(text: str) -> bool:
    for ch in text:
        if unicodedata.category(ch).startswith("L") and not ("Ѐ" <= ch <= "ӿ"):
            return True
    return False


def validate_translation(data: dict) -> None:
    errors = []
    for key, value in data.items():
        if not isinstance(value, str):
            continue
        if key.endswith("_en") and has_non_latin_letters(value):
            errors.append(f"в поле {key} остался нелатинский текст")
        if key.endswith("_ru") and has_non_cyrillic_letters(value):
            errors.append(f"в поле {key} остался текст не на кириллице")
    for i, block in enumerate(data.get("blocks_en", [])):
        text = block.get("text", "")
        if has_non_latin_letters(text):
            errors.append(f"в блоке перевода №{i + 1} остался нелатинский текст")
    full_text = data.get("full_text_en", "").strip()
    for i, block in enumerate(data.get("blocks_en", [])):
        block_text = block.get("text", "").strip()
        if block_text and block_text not in full_text:
            errors.append(f"текст блока перевода №{i + 1} не входит в общий перевод: «{block_text}»")
    if errors:
        raise ValueError("; ".join(errors))


@app.post("/translate")
async def api_translate(
    original: UploadFile,
    clean: UploadFile,
    ocr: str = Form(...),
    caption: str = Form(...),
):
    original_img = Image.open(io.BytesIO(await original.read()))
    clean_img = Image.open(io.BytesIO(await clean.read()))
    ocr_data = json.loads(ocr)

    ocr_texts = [b["text"] for b in ocr_data.get("blocks", [])]
    literal = literal_translate(ocr_texts)

    analysis_text = None
    last_err = None
    humor_retries = 0
    for _ in range(MAX_RETRIES):
        try:
            result = await analyse_humor(
                str(ocr_data.get("blocks", [])), caption,
                seed=random.randint(0, 2**31 - 1),
            )
            if not result or len(result.strip()) < 10:
                raise ValueError("получен слишком короткий ответ")
            if has_non_latin_letters(result):
                raise ValueError("в ответе остался нелатинский текст")
            analysis_text = result
            break
        except Exception as e:
            traceback.print_exc()
            last_err = e
            humor_retries += 1
    if analysis_text is None:
        return JSONResponse(
            status_code=500,
            content={"error": f"не удалось проанализировать юмор ({last_err})"},
        )

    translation_data = None
    last_err = None
    translation_retries = 0
    for _ in range(MAX_RETRIES):
        try:
            raw = await translate_meme(
                ocr_data, analysis_text, literal,
                seed=random.randint(0, 2**31 - 1),
            )
            raw = strip_json_markdown(raw)
            if not raw:
                raise ValueError("получен пустой ответ")
            parsed = json.loads(raw)
            try:
                validate_translation(parsed)
                translation_data = parsed
                last_err = None
                break
            except Exception as ve:
                traceback.print_exc()
                translation_data = parsed
                last_err = ve
                translation_retries += 1
        except Exception as e:
            traceback.print_exc()
            last_err = e
            translation_retries += 1

    if translation_data is None:
        return JSONResponse(
            status_code=500,
            content={"error": f"не удалось перевести текст мема ({last_err})"},
        )

    partial = {
        "analysis": analysis_text,
        "literal_translation": literal,
        "explanation_ru": translation_data.get("explanation_ru"),
        "explanation_en": translation_data.get("explanation_en"),
        "full_text_en": translation_data.get("full_text_en"),
        "blocks_en": translation_data.get("blocks_en"),
        "result_image_base64": None,
        "humor_retries": humor_retries,
        "translation_retries": translation_retries,
    }

    if last_err is not None:
        partial["validation_error"] = str(last_err)
        return partial

    try:
        result_img = add_translated_text(
            original_img, clean_img, translation_data.get("blocks_en", [])
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"не удалось наложить перевод на изображение ({e})"})

    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    partial["result_image_base64"] = base64.b64encode(buf.getvalue()).decode()
    return partial
