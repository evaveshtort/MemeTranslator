from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import base64
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
            errors.append(f"{key} contains non-Latin letters")
        if key.endswith("_ru") and has_non_cyrillic_letters(value):
            errors.append(f"{key} contains non-Cyrillic letters")
    for i, block in enumerate(data.get("blocks_en", [])):
        text = block.get("text", "")
        if has_non_latin_letters(text):
            errors.append(f"blocks_en[{i}].text contains non-Latin letters")
    full_text = data.get("full_text_en", "").strip()
    joined = " ".join(b.get("text", "").strip() for b in data.get("blocks_en", [])).strip()
    if full_text != joined:
        errors.append(f"full_text_en != joined blocks_en: '{full_text}' vs '{joined}'")
    if errors:
        raise ValueError(f"Validation errors: {errors}")


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
    literal_translations = literal_translate(ocr_texts)

    analysis_text = None
    last_err = None
    humor_retries = 0
    for _ in range(MAX_RETRIES):
        try:
            result = analyse_humor(str(ocr_data.get("blocks", [])), caption)
            if not result or len(result.strip()) < 10:
                raise ValueError("Result too short")
            if has_non_latin_letters(result):
                raise ValueError("Analysis contains non-Latin letters (must be English only)")
            analysis_text = result
            break
        except Exception as e:
            last_err = e
            humor_retries += 1
    if analysis_text is None:
        return JSONResponse(
            status_code=500,
            content={"error": f"humor_analysis failed after {MAX_RETRIES} retries: {last_err}"},
        )


    translation_data = None
    last_err = None
    translation_retries = 0
    for _ in range(MAX_RETRIES):
        try:
            raw = translate_meme(ocr_data, analysis_text, literal_translations)
            raw = strip_json_markdown(raw)
            if not raw:
                raise ValueError("Empty result")
            parsed = json.loads(raw)
            validate_translation(parsed)
            translation_data = parsed
            break
        except Exception as e:
            last_err = e
            translation_retries += 1
    if translation_data is None:
        return JSONResponse(
            status_code=500,
            content={"error": f"translation failed after {MAX_RETRIES} retries: {last_err}"},
        )

    try:
        result_img = add_translated_text(
            original_img, clean_img, translation_data.get("blocks_en", [])
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"text_adding failed: {e}"})

    buf = io.BytesIO()
    result_img.save(buf, format="PNG")
    result_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "analysis": analysis_text,
        "literal_translation": " / ".join(t for t in literal_translations if t),
        "explanation_ru": translation_data.get("explanation_ru"),
        "explanation_en": translation_data.get("explanation_en"),
        "full_text_en": translation_data.get("full_text_en"),
        "blocks_en": translation_data.get("blocks_en"),
        "result_image_base64": result_base64,
        "humor_retries": humor_retries,
        "translation_retries": translation_retries,
    }
