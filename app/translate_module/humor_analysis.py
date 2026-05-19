from ollama import AsyncClient
import os


def make_reasoning_promt(ocr_blocks, visual_context):
    return f"""
You analyze a Russian meme step by step.

IMPORTANT RULES:
- Think carefully before answering
- Do NOT repeat instructions in output
- Output ONLY final filled fields
- Do NOT include words like "Write", "Explain", "Step"
- Do NOT copy any part of these instructions into the answer
- If truly impossible to understand meme → INSUFFICIENT
- Use ONLY English in output (no Russian, no Chinese, no other languages)

INPUT:
blocks: {ocr_blocks}
image_description: {visual_context}

----------------------------------------

STEP 1 — MEANING

MEANING: short literal explanation of text

----------------------------------------

STEP 2 — IMAGE ANALYSIS

IMAGE_CONTENT: brief description of visible elements

IMAGE_INTERACTION:
- contradiction / reinforcement / punchline / context / decoration

IMAGE_ROLE:
- essential / optional / not_needed

IMAGE_REASON:
brief explanation of how image contributes to humor

----------------------------------------

STEP 3 — HUMOR TYPE

HUMOR_TYPE:
irony / absurdity / contrast / exaggeration /
understatement / wordplay / situational humor /
meta-humor / cultural reference

----------------------------------------

STEP 4 — WHY IT'S FUNNY

EXPLANATION_EN: 1–3 sentences, explain humor (not restating text)

----------------------------------------

STEP 5 — CONFIDENCE

Rate overall confidence based on text readability and image clarity.

CONFIDENCE: high / medium / low
CONFIDENCE_REASON: one sentence — why this confidence level

----------------------------------------

FINAL RULES:
- Output ONLY fields above
- Do NOT repeat prompts or instructions
- Do NOT include formatting words ("Write", "Explain", etc.)
"""


client = AsyncClient(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))


async def analyse_humor(ocr_blocks: str, visual_context: str) -> str:
    response = await client.chat(
        model="qwen2.5:7b-instruct",
        messages=[{"role": "user", "content": make_reasoning_promt(ocr_blocks, visual_context)}]
    )
    return response.message.content
