import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/robotoflex/RobotoFlex.ttf"


_MIN_WDTH = 70


_SLANT_MAX = 14
_SLANT_STEP = 2
_SLANT_THRESHOLD = 4

_LINE_GAP_RATIO = 0.15
_EDGE_PADDING = 4


def _luminance(color: tuple) -> float:
    r, g, b = color
    return 0.299 * r + 0.587 * g + 0.114 * b


def _detect_slant(mask: np.ndarray) -> float:

    h, w = mask.shape
    if h < 12 or w < 8:
        return 0.0

    best_score = -1.0
    best_angle = 0
    for angle_deg in range(0, _SLANT_MAX + 1, _SLANT_STEP):
        if angle_deg == 0:
            sheared = mask
        else:
            shear = float(np.tan(np.radians(angle_deg)))
            new_w = w + int(np.ceil(shear * h)) + 2
            M = np.array([[1, shear, 0], [0, 1, 0]], dtype=np.float32)
            sheared = cv2.warpAffine(mask, M, (new_w, h), flags=cv2.INTER_NEAREST)
        col_sums = sheared.sum(axis=0).astype(np.float32)
        nonzero = np.where(col_sums > 0)[0]
        if len(nonzero) < 2:
            continue
        trimmed = col_sums[nonzero[0]:nonzero[-1] + 1]
        score = float(trimmed.var())
        if score > best_score:
            best_score = score
            best_angle = angle_deg

    return float(best_angle) if best_angle >= _SLANT_THRESHOLD else 0.0


def _detect_lines(mask: np.ndarray) -> list:

    h, w = mask.shape
    if h < 4 or w < 4:
        return [(0, h)] if h > 0 else []

    row_ink = (mask > 0).sum(axis=1)
    threshold = max(2, int(w * 0.02))
    has_ink = row_ink >= threshold

    bands = []
    in_band = False
    start = 0
    for y, hi in enumerate(has_ink):
        if hi and not in_band:
            in_band = True
            start = y
        elif not hi and in_band:
            in_band = False
            bands.append((start, y))
    if in_band:
        bands.append((start, h))
    if not bands:
        return []

    merged = [bands[0]]
    for s, e in bands[1:]:
        prev_s, prev_e = merged[-1]
        prev_h = prev_e - prev_s
        if s - prev_e < max(2, prev_h * 0.3):
            merged[-1] = (prev_s, e)
        else:
            merged.append((s, e))

    max_h = max(e - s for s, e in merged)
    return [(s, e) for s, e in merged if (e - s) >= max_h * 0.35]


def _detect_all_caps(mask: np.ndarray, bands: list) -> bool:
    if not bands:
        return False
    caps_votes = 0
    total_votes = 0
    for y1, y2 in bands:
        band = mask[y1:y2]
        if band.shape[0] < 6:
            continue
        num, _, stats, _ = cv2.connectedComponentsWithStats(band, connectivity=8)
        if num < 3:
            continue
        heights = stats[1:, cv2.CC_STAT_HEIGHT].astype(np.float32)
        band_h = y2 - y1
        heights = heights[heights >= band_h * 0.3]
        if len(heights) < 2:
            continue
        median_h = float(np.median(heights))
        max_h = float(heights.max())
        if median_h > 0 and max_h / median_h < 1.2:
            caps_votes += 1
        total_votes += 1
    return total_votes > 0 and caps_votes / total_votes >= 0.6


def _detect_alignment(mask: np.ndarray, bands: list) -> str:
    if not bands:
        return 'center'
    w = mask.shape[1]
    lefts, rights = [], []
    for y1, y2 in bands:
        col_sums = mask[y1:y2].sum(axis=0)
        nz = np.where(col_sums > 0)[0]
        if len(nz) < 2:
            continue
        lefts.append(int(nz[0]))
        rights.append(int(w - 1 - nz[-1]))
    if not lefts:
        return 'center'
    avg_left = float(np.mean(lefts))
    avg_right = float(np.mean(rights))
    threshold = w * 0.08
    if avg_left - avg_right < -threshold:
        return 'left'
    if avg_left - avg_right > threshold:
        return 'right'
    return 'center'


def _analyze_block(original_np: np.ndarray, coords: tuple) -> dict:
    x1, y1, x2, y2 = coords
    region = original_np[y1:y2, x1:x2]
    if region.size == 0:
        return {"text_color": (0, 0, 0), "bg_color": (255, 255, 255),
                "text_ratio": 0.25, "has_stroke": False, "stroke_color": None,
                "stroke_ratio": 0.0, "slant_deg": 0.0,
                "num_lines": 1, "is_all_caps": False, "alignment": "center"}

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

    text_mask = (labels2.flatten() == text_idx).astype(np.uint8).reshape(region.shape[:2]) * 255
    slant_deg = _detect_slant(text_mask)
    bands     = _detect_lines(text_mask)
    num_lines = max(1, len(bands))
    is_all_caps = _detect_all_caps(text_mask, bands)
    alignment   = _detect_alignment(text_mask, bands)

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
        order   = np.argsort(counts3)          
        stroke_cand = bgr_to_rgb(centers3[order[0]])
        body_cand   = bgr_to_rgb(centers3[order[1]])
        s_ratio     = float(counts3[order[0]] / len(labels3))

        s_lum    = _luminance(stroke_cand)
        body_lum = _luminance(body_cand)
        text_lum = _luminance(text_color)

        text_is_extreme = text_lum < 60 or text_lum > 195
        if (
            (s_lum < 40 or s_lum > 215)
            and abs(body_lum - s_lum) > 150
            and abs(text_lum - s_lum) > 150
            and text_is_extreme
            and 0.04 < s_ratio < 0.40
        ):
            has_stroke   = True
            stroke_color = stroke_cand
            stroke_ratio = s_ratio

    return {
        "text_color":   text_color,
        "bg_color":     bg_color,
        "text_ratio":   text_ratio,
        "has_stroke":   has_stroke,
        "stroke_color": stroke_color,
        "stroke_ratio": stroke_ratio,
        "slant_deg":    slant_deg,
        "num_lines":    num_lines,
        "is_all_caps":  is_all_caps,
        "alignment":    alignment,
    }


def _weight_for(text_ratio: float) -> int:

    return int(max(200, min(1000, text_ratio * 3000)))


_AXIS_NAME_TO_TAG = {
    "Weight":       "wght",
    "Width":        "wdth",
    "Optical Size": "opsz",
    "Slant":        "slnt",
}


def _axis_tag(axis: dict) -> str:
    name = axis.get("name")
    if isinstance(name, bytes):
        name = name.decode("ascii", errors="ignore")
    return _AXIS_NAME_TO_TAG.get(name or "", "")


def _make_var_font(size: int, wght: int, wdth: int, slnt: float) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(FONT_PATH, size)
    opsz = max(8, min(144, size))
    target = {"wght": wght, "wdth": wdth, "opsz": opsz, "slnt": slnt}
    values = []
    for axis in font.get_variation_axes():
        tag = _axis_tag(axis)
        values.append(target.get(tag, axis["default"]))
    font.set_variation_by_axes(values)
    return font


def _split_into_lines(text: str, num_lines: int) -> list:

    if num_lines <= 1:
        return [text]
    words = text.split()
    if len(words) <= 1:
        return [text]
    if len(words) <= num_lines:
        return words

    target = len(text) / num_lines
    lines = []
    cur, cur_len = [], 0
    for w in words:
        next_len = cur_len + (1 if cur else 0) + len(w)
        remaining_lines = num_lines - len(lines)
        if cur and remaining_lines > 1 and next_len > target * 1.15:
            lines.append(' '.join(cur))
            cur, cur_len = [w], len(w)
        else:
            cur.append(w)
            cur_len = next_len
    if cur:
        lines.append(' '.join(cur))
    return lines


def _measure(lines: list, font, draw) -> tuple:
    widths, tops = [], []
    max_h = 0
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        widths.append(bbox[2] - bbox[0])
        tops.append(bbox[1])
        max_h = max(max_h, bbox[3] - bbox[1])
    return widths, tops, max_h


def _fits(lines: list, font, draw, box_w: int, box_h: int) -> bool:
    widths, _, line_h = _measure(lines, font, draw)
    n = len(lines)
    total_h = line_h * n + int(line_h * _LINE_GAP_RATIO) * (n - 1)
    return max(widths) <= box_w and total_h <= box_h


def _get_font(lines: list, coords: tuple, text_ratio: float, slant_deg: float) -> ImageFont.FreeTypeFont:
    x1, y1, x2, y2 = coords
    box_w = x2 - x1 - _EDGE_PADDING * 2
    box_h = y2 - y1 - _EDGE_PADDING * 2
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    wght = _weight_for(text_ratio)
    slnt = -min(slant_deg, 10.0)

    for size in range(200, 8, -1):
        font = _make_var_font(size, wght=wght, wdth=100, slnt=slnt)
        widths, _, line_h = _measure(lines, font, dummy)
        n = len(lines)
        total_h = line_h * n + int(line_h * _LINE_GAP_RATIO) * (n - 1)
        if total_h > box_h:
            continue
        max_w = max(widths)
        if max_w <= box_w:
            return font
        needed_wdth = int(100 * box_w / max_w)
        if needed_wdth >= _MIN_WDTH:
            font = _make_var_font(size, wght=wght, wdth=max(_MIN_WDTH, needed_wdth), slnt=slnt)
            if _fits(lines, font, dummy, box_w, box_h):
                return font
    return _make_var_font(8, wght=wght, wdth=_MIN_WDTH, slnt=slnt)


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
        info  = _analyze_block(original_np, coords)
        color = info["text_color"]

        if info["is_all_caps"]:
            text = text.upper()
        lines = _split_into_lines(text, info["num_lines"])
        font  = _get_font(lines, coords, info["text_ratio"], info["slant_deg"])

        widths, tops, line_h = _measure(lines, font, draw)
        gap = int(line_h * _LINE_GAP_RATIO)
        total_h = line_h * len(lines) + gap * (len(lines) - 1)
        y_start = y1 + (y2 - y1 - total_h) // 2

        alignment = info["alignment"]
        for i, ln in enumerate(lines):
            if alignment == 'left':
                x = x1 + _EDGE_PADDING
            elif alignment == 'right':
                x = x2 - _EDGE_PADDING - widths[i]
            else:
                x = x1 + (x2 - x1 - widths[i]) // 2
            y = y_start + i * (line_h + gap) - tops[i]

            if info["has_stroke"]:
                outline_w = max(1, round(
                    font.size * info["stroke_ratio"] / max(info["text_ratio"], 0.01) * 0.12
                ))
                draw.text((x, y), ln, font=font, fill=color,
                          stroke_width=outline_w, stroke_fill=info["stroke_color"])
            else:
                draw.text((x, y), ln, font=font, fill=color)

    return result
