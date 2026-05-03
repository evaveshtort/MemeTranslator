import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def get_text_color(original_np: np.ndarray, coords: tuple) -> tuple:
    x1, y1, x2, y2 = coords
    region = original_np[y1:y2, x1:x2]
    if region.size == 0:
        return (0, 0, 0)

    pixels = region.reshape(-1, 3).astype(np.float32)
    _, labels, centers = cv2.kmeans(
        pixels, 2, None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
        10, cv2.KMEANS_RANDOM_CENTERS
    )

    counts = np.bincount(labels.flatten())
    text_cluster = np.argmin(counts)
    b, g, r = centers[text_cluster].astype(int)
    return (int(r), int(g), int(b))


def get_font(text: str, coords: tuple, font_path: str = FONT_PATH, padding: int = 4) -> ImageFont.FreeTypeFont:
    x1, y1, x2, y2 = coords
    box_w = x2 - x1 - padding * 2
    box_h = y2 - y1 - padding * 2
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(200, 8, -1):
        font = ImageFont.truetype(font_path, size)
        bbox = dummy.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= box_w and bbox[3] - bbox[1] <= box_h:
            return font
    return ImageFont.truetype(font_path, 8)


def add_translated_text(
    original_img: Image.Image,
    clean_img: Image.Image,
    blocks_en: list,
) -> Image.Image:
    original_np = cv2.cvtColor(np.array(original_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    result = clean_img.copy().convert("RGB")
    draw = ImageDraw.Draw(result)

    for block in blocks_en:
        text = block.get("text", "").strip()
        coords = tuple(block["coords"])
        if not text:
            continue

        x1, y1, x2, y2 = coords
        color = get_text_color(original_np, coords)
        font = get_font(text, coords)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_x = x1 + (x2 - x1 - (bbox[2] - bbox[0])) // 2
        text_y = y1 + (y2 - y1 - (bbox[3] - bbox[1])) // 2 - bbox[1]

        draw.text((text_x, text_y), text, font=font, fill=color)

    return result
