from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
import io

from .client import ocr, remove_text, caption

app = FastAPI()

@app.post("/process")
async def process(file: UploadFile):
    """Полный пайплайн: OCR → удаление текста → описание"""
    img = Image.open(io.BytesIO(await file.read()))

    ocr_result = await ocr(img)

    clean_img = await remove_text(img, ocr_result["blocks"])

    description = await caption(clean_img)

    buf = io.BytesIO()
    clean_img.save(buf, format="PNG")
    buf.seek(0)

    return {
        "ocr": ocr_result,
        "caption": description,
        # можно вернуть и картинку, если нужно
    }