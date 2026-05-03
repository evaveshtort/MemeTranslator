from PIL import Image, ImageDraw
from iopaint.model_manager import ModelManager
from iopaint.schema import InpaintRequest
import numpy as np
import cv2

model = ModelManager(name="lama", device="cuda")

def remove_text(img: Image.Image, blocks: list) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)

    for block in blocks:
        x1, y1, x2, y2 = block["bbox"]
        draw.rectangle([x1, y1, x2, y2], fill=255)

    img_np = np.array(img)
    mask_np = np.array(mask)

    result = model(image=img_np, mask=mask_np, config=InpaintRequest())
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))