from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
import io
import base64

from .client import ocr, remove_text, caption

app = FastAPI(servers=[{"url": "/"}])

@app.post("/process")
async def process(file: UploadFile):
    #Объединенный пайплайн: OCR + удаление текста + описание
    img = Image.open(io.BytesIO(await file.read()))

    ocr_result = await ocr(img)

    clean_img = await remove_text(img, ocr_result["blocks"])

    description = await caption(clean_img)

    buf = io.BytesIO()
    clean_img.save(buf, format="PNG")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "ocr": ocr_result,
        "caption": description,
        "image_base64": img_base64
    }