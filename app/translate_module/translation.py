from ollama import AsyncClient
import httpx
import os

client = AsyncClient(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))

_YANDEX_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"


def literal_translate(texts: list[str]) -> str:
    if not texts:
        return ""
    api_key = os.environ.get("YANDEX_TRANSLATE_KEY", "")
    if not api_key:
        return ""
    try:
        full_text = " / ".join(t for t in texts if t)
        response = httpx.post(
            _YANDEX_URL,
            headers={"Authorization": f"Api-Key {api_key}"},
            json={"texts": [full_text], "sourceLanguageCode": "ru", "targetLanguageCode": "en"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["translations"][0]["text"]
    except Exception:
        return ""


def make_translation_prompt(analysis_text: str, ocr: dict, literal: str = "") -> str:
    blocks = ocr.get("blocks", [])
    blocks_formatted = "\n".join(
        f"  bbox={b['bbox']}, text=\"{b['text']}\"" for b in blocks
    )
    coords_list = [b["bbox"] for b in blocks]

    if literal:
        literal_section = f"""LITERAL TRANSLATION (word-for-word machine translation, for reference only):
"{literal}"

This is a rough literal translation — grammar and phrasing may be awkward.
Use it as a semantic anchor to verify meaning:
- DO use it to confirm you haven't dropped words, negations, or changed the meaning
- DO use it as a starting point for choosing the right English vocabulary
- Do NOT copy it verbatim — your job is to make the final translation fluent and natural

"""
    else:
        literal_section = ""

    return f"""
Translate a Russian meme into natural English.

OUTPUT:
- Return ONLY valid JSON
- No extra text

----------------------------------------

OCR BLOCKS (ONLY text to translate):
{blocks_formatted}

{literal_section}ANALYSIS (context only, do NOT translate):
{analysis_text}

----------------------------------------

1. TRANSLATION

- Translate ONLY text from OCR BLOCKS
- Use ANALYSIS only to understand meaning and tone
- Do NOT add new information
- Do NOT describe the image

MEANING:
- Preserve meaning, adapt only if needed for keep joke funny (wordplay or similar)
- Never drop negations (no, not, never) or key words

STYLE:
- Make it sound natural in English
- Use simple and common words
- Use natural English word order (NOT Russian structure)

ADAPTATION:
- If literal translation sounds bad → rephrase naturally
- If unsure → choose a simpler and more common phrasing
- Do NOT invent words

----------------------------------------

2. CAPITALIZATION (STRICT)

- If source is ALL CAPS → keep ALL CAPS
- If source is NOT ALL CAPS → use normal sentence case
- Do NOT convert to ALL CAPS unless original is ALL CAPS
- If unsure → use normal sentence case

----------------------------------------

3. BLOCKS

- Number of blocks: {len(blocks)}
- Keep same order
- Copy coords exactly: {coords_list}
- Each block = its part of the sentence
- Do NOT duplicate text across blocks

----------------------------------------

4. EXPLANATION

Write 2–3 sentences explaining the joke.

explanation_en:
- Explain why it is funny (contrast, mismatch, irony)
- Do NOT repeat the text

explanation_ru:
- Объясни по-русски с нуля
- Представь, что объясняешь другу
- Пиши просто и естественно
- Используй только обычные слова
- Не придумывай слова
- Избегай шаблонных фраз

CONSISTENCY RULE:

- All fields in INPUT ANALYSIS describe the SAME image
- Treat them as different descriptions of the same visual scene
- Do NOT treat different fields as separate images or separate scenes
- Combine information from all fields into one unified understanding of the image

Importance order:
1. WHY IT'S FUNNY — if present, use as the primary source
2. EXPLANATION_EN — use as primary source if WHY IT'S FUNNY is absent
3. Supplement with IMAGE_REASON and IMAGE_INTERACTION for fuller picture

- Do NOT add new facts, actions, or objects not present in OCR or analysis
- The number of people/objects must be inferred from IMAGE_CONTENT, not multiplied by multiple descriptions
- If different fields disagree, prefer IMAGE_CONTENT as the most reliable source

----------------------------------------

OUTPUT JSON:

{{
  "explanation_ru": "...",
  "explanation_en": "...",
  "full_text_en": "...",
  "blocks_en": [
    {{
      "coords": [x0, y0, x1, y1],
      "text": "..."
    }}
  ]
}}

----------------------------------------

FINAL CHECK:

- Valid JSON
- English only in *_en fields (no Russian, no Chinese, no other non-Latin scripts)
- English words are existing, english grammar is correct
- Russian only in *_ru fields (no English, no Chinese, no other non-Cyrillic scripts)
- Russian words are existing, russian grammar is correct
- No invented words
- full_text_en == joined blocks
- coords unchanged
"""


async def translate_meme(ocr: dict, analysis_text: str, literal: str = "", seed: int | None = None) -> str:
    options = {"temperature": 0.3}
    if seed is not None:
        options["seed"] = seed
    response = await client.chat(
        model="qwen2.5:7b-instruct",
        messages=[{"role": "user", "content": make_translation_prompt(analysis_text, ocr, literal)}],
        options=options,
    )
    return response.message.content
