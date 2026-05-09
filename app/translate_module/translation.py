from ollama import Client
import ctranslate2
import sentencepiece as spm
import os

client = Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))

_MODEL_DIR = os.environ.get("OPUS_MT_MODEL_DIR", "/models/opus-mt-ru-en")
_translator = None
_sp_source = None
_sp_target = None


def _load_model():
    global _translator, _sp_source, _sp_target
    if _translator is None:
        _translator = ctranslate2.Translator(_MODEL_DIR, device="cpu", inter_threads=2)
        _sp_source = spm.SentencePieceProcessor()
        _sp_source.Load(os.path.join(_MODEL_DIR, "source.spm"))
        _sp_target = spm.SentencePieceProcessor()
        _sp_target.Load(os.path.join(_MODEL_DIR, "target.spm"))
    return _translator, _sp_source, _sp_target


def literal_translate(texts: list[str]) -> list[str]:
    if not texts:
        return []
    try:
        translator, sp_src, sp_tgt = _load_model()
        tokenized = [sp_src.Encode(t, out_type=str) for t in texts]
        results = translator.translate_batch(
            tokenized,
            no_repeat_ngram_size=4,
            repetition_penalty=1.5,
            beam_size=2,
        )
        return [sp_tgt.Decode(r.hypotheses[0]) for r in results]
    except Exception:
        return [""] * len(texts)


def make_translation_prompt(analysis_text: str, ocr: dict, literal_translations: list[str] | None = None) -> str:
    blocks = ocr.get("blocks", [])
    blocks_formatted = "\n".join(
        f"  bbox={b['bbox']}, text=\"{b['text']}\"" for b in blocks
    )
    coords_list = [b["bbox"] for b in blocks]

    if literal_translations and len(literal_translations) == len(blocks):
        literal_formatted = "\n".join(
            f"  bbox={b['bbox']}, ru=\"{b['text']}\", literal_en=\"{lit}\""
            for b, lit in zip(blocks, literal_translations)
        )
        literal_section = f"""LITERAL TRANSLATION (word-for-word machine translation, for reference only):
{literal_formatted}

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


def translate_meme(ocr: dict, analysis_text: str, literal_translations: list[str] | None = None) -> str:
    response = client.chat(
        model="qwen2.5:7b-instruct",
        messages=[{"role": "user", "content": make_translation_prompt(analysis_text, ocr, literal_translations)}],
        options={"temperature": 0.3},
    )
    return response.message.content
