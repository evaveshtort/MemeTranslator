from ollama import Client
import os

def make_translation_promt(analysis_text, ocr_blocks):
    return f"""
Translate a Russian meme into natural English.

OUTPUT:
- Return ONLY valid JSON
- No extra text

----------------------------------------

OCR BLOCKS (ONLY text to translate):
{ocr_blocks}

ANALYSIS (context only, do NOT translate):
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

- Number of blocks: {len(ocr_blocks.blocks)}
- Keep same order
- Copy coords exactly: {[b.coords for b in ocr_blocks.blocks]}
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
- English only in *_en
- English words are existing, english grammar is correct
- Russian only in *_ru
- Russian words are existing, russian grammar is correct
- No invented words
- full_text_en == joined blocks
- coords unchanged
"""

client = Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))

def analyse_humor(ocr_blocks: str, analysis_text: str) -> str:
    response = client.chat(
        model="qwen2.5:7b-instruct",
        messages=[{"role": "user", "content": make_translation_promt(analysis_text, ocr_blocks)}], options={'temperature': 0.3}
    )
    return response.message.content