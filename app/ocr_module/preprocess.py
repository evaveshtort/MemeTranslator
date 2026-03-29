import cv2
import numpy as np
from PIL import Image

from .config import PreprocessConfig


def preprocess(img: Image.Image, cfg: PreprocessConfig) -> Image.Image:
    img_np = np.array(img)

    if cfg.grayscale and len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

    if cfg.resize is not None:
        img_np = cv2.resize(
            img_np,
            None,
            fx=cfg.resize,
            fy=cfg.resize,
            interpolation=cv2.INTER_CUBIC,
        )

    if cfg.clahe:
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        clahe_obj = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_np = clahe_obj.apply(img_np)

    if cfg.blur == "gaussian":
        img_np = cv2.GaussianBlur(img_np, (5, 5), 0)
    elif cfg.blur == "median":
        img_np = cv2.medianBlur(img_np, 3)
    elif cfg.blur == "bilateral":
        img_np = cv2.bilateralFilter(img_np, 9, 75, 75)

    if cfg.threshold == "otsu":
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, img_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif cfg.threshold == "binary":
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, img_np = cv2.threshold(img_np, 127, 255, cv2.THRESH_BINARY)
    elif cfg.threshold == "adaptive":
        if len(img_np.shape) == 3:
            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        img_np = cv2.adaptiveThreshold(
            img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    if cfg.morph is not None:
        kernel = np.ones((3, 3), np.uint8)
        if cfg.morph == "open":
            img_np = cv2.morphologyEx(img_np, cv2.MORPH_OPEN, kernel)
        elif cfg.morph == "close":
            img_np = cv2.morphologyEx(img_np, cv2.MORPH_CLOSE, kernel)
        elif cfg.morph == "dilate":
            img_np = cv2.dilate(img_np, kernel, iterations=1)
        elif cfg.morph == "erode":
            img_np = cv2.erode(img_np, kernel, iterations=1)

    if cfg.edge_enhance:
        img_np = cv2.Canny(img_np, 50, 150)

    if cfg.invert:
        img_np = cv2.bitwise_not(img_np)

    if cfg.sharpen:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        img_np = cv2.filter2D(img_np, -1, kernel)

    if cfg.denoise:
        if len(img_np.shape) == 3:
            img_np = cv2.fastNlMeansDenoisingColored(img_np, h=10, hColor=10)
        else:
            img_np = cv2.fastNlMeansDenoising(img_np, h=10)

    # grayscale → RGB, чтобы Surya всегда получал трёхканальное изображение
    if len(img_np.shape) == 2:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_GRAY2RGB)

    return Image.fromarray(img_np)