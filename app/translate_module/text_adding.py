import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Approximate text-pixel coverage that DejaVu produces at typical sizes.
# Used to estimate how much heavier the original font was.
_BASELINE_RATIO_REGULAR = 0.12
_BASELINE_RATIO_BOLD    = 0.17


def _luminance(color: tuple) -> float:
    r, g, b = color
    return 0.299 * r + 0.587 * g + 0.114 * b


def _analyze_block(original_np: np.ndarray, coords: tuple) -> dict:
    x1, y1, x2, y2 = coords
    region = original_np[y1:y2, x1:x2]
    if region.size == 0:
        return {"text_color": (0, 0, 0), "bg_color": (255, 255, 255),
                "text_ratio": 0.25, "has_stroke": False, "stroke_color": None,
                "stroke_ratio": 0.0}

    pixels = region.reshape(-1, 3).astype(np.float32)

    def bgr_to_rgb(c):
        b, g, r = c.astype(int)
        return (int(r), int(g), int(b))

    _, labels2, centers2 = cv2.kmeans(
        pixels, 2, None,
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
        10, cv2.KMEANS_RANDOM_CENTERS,
    )
    counts2    = np.bincount(labels2.flatten())
    text_idx   = int(np.argmin(counts2))
    text_color = bgr_to_rgb(centers2[text_idx])
    bg_color   = bgr_to_rgb(centers2[int(np.argmax(counts2))])
    text_ratio = float(counts2[text_idx] / len(labels2))

    has_stroke   = False
    stroke_color = None
    stroke_ratio = 0.0

    if len(pixels) >= 9:
        _, labels3, centers3 = cv2.kmeans(
            pixels, 3, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
            10, cv2.KMEANS_RANDOM_CENTERS,
        )
        counts3 = np.bincount(labels3.flatten())
        order   = np.argsort(counts3)           # ascending: text, stroke, bg
        t_color = bgr_to_rgb(centers3[order[0]])
        m_color = bgr_to_rgb(centers3[order[1]])
        m_ratio = float(counts3[order[1]] / len(labels3))
        m_lum   = _luminance(m_color)
        t_lum   = _luminance(t_color)
        if abs(t_lum - m_lum) > 100 and (m_lum < 50 or m_lum > 200) and 0.04 < m_ratio < 0.45:
            has_stroke   = True
            stroke_color = m_color
            stroke_ratio = m_ratio

    return {
        "text_color":  text_color,
        "bg_color":    bg_color,
        "text_ratio":  text_ratio,
        "has_stroke":  has_stroke,
        "stroke_color": stroke_color,
        "stroke_ratio": stroke_ratio,
    }


def _thicken_for(text_ratio: float, bold: bool, font_size: int) -> int:
    """Estimate fake-bold stroke width to compensate for DejaVu's thin strokes.

    If the original text_ratio exceeds DejaVu's natural coverage, we add a
    same-color stroke to expand the glyphs proportionally.
    """
    baseline = _BASELINE_RATIO_BOLD if bold else _BASELINE_RATIO_REGULAR
    excess   = max(0.0, text_ratio - baseline)
    # empirical: each unit of excess ratio corresponds to ~font_size/4 pixels of stroke
    thicken  = round(font_size * excess / 4.0)
    return max(1, min(thicken, font_size // 8))


def _get_font(text: str, coords: tuple, bold: bool, padding: int = 4) -> ImageFont.FreeTypeFont:
    x1, y1, x2, y2 = coords
    box_w = x2 - x1 - padding * 2
    box_h = y2 - y1 - padding * 2
    font_path = FONT_BOLD if bold and os.path.exists(FONT_BOLD) else FONT_REGULAR
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
    draw   = ImageDraw.Draw(result)

    for block in blocks_en:
        text   = block.get("text", "").strip()
        coords = tuple(block["coords"])
        if not text:
            continue

        x1, y1, x2, y2 = coords
        info    = _analyze_block(original_np, coords)
        color   = info["text_color"]
        bold    = info["text_ratio"] > 0.28
        font    = _get_font(text, coords, bold=bold)
        thicken = _thicken_for(info["text_ratio"], bold, font.size)

        bbox   = draw.textbbox((0, 0), text, font=font)
        text_x = x1 + (x2 - x1 - (bbox[2] - bbox[0])) // 2
        text_y = y1 + (y2 - y1 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        xy     = (text_x, text_y)

        if info["has_stroke"]:
            outline_w = max(1, round(
                font.size * info["stroke_ratio"] / max(info["text_ratio"], 0.01) * 0.12
            ))
            draw.text(xy, text, font=font, fill=color,
                      stroke_width=outline_w + thicken, stroke_fill=info["stroke_color"])
            draw.text(xy, text, font=font, fill=color,
                      stroke_width=thicken, stroke_fill=color)
        else:
            draw.text(xy, text, font=font, fill=color,
                      stroke_width=thicken, stroke_fill=color)

    return result
