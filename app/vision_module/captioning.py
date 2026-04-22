from ollama import Client
import os

PROMPT = """
You are a visual description system.

Your task is to describe all visible content in an image in a structured way.

OUTPUT FORMAT:
Start with "Panel 1:" and continue with Panel 2, Panel 3 if needed.
Do not write anything outside panel sections.

PANEL DETECTION:
- Split image into panels only if there are clear visual separations (borders, gaps, layout blocks)
- If not, use only Panel 1
- Use reading order: top-to-bottom, left-to-right

WHAT TO DESCRIBE:
Describe ALL visible elements, including:
- people, animals, objects
- background elements
- text regions (even if unreadable or empty areas where text likely exists)
- drawn or symbolic elements in the image

SPATIAL DESCRIPTION:
- Use simple spatial relations: left, right, above, below, inside, next to
- Do not use coordinates or numbers

CONSTRAINTS:
- Do NOT explain meaning, intent, humor, or story
- Do NOT add summaries or conclusions
- Do NOT add text outside panels
- Do NOT use phrases like "this image shows" or "we see"

COMPLETENESS RULE:
- If an element is clearly visible, it must be included
- Prefer completeness over brevity
"""

client = Client(host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))

def describe_image(img_path: str) -> str:
    response = client.chat(
        model="qwen2.5vl:3b",
        messages=[{"role": "user", "content": PROMPT, "images": [img_path]}],
    )
    return response.message.content