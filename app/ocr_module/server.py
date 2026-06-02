from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json

from .service import OCRService
from .config import OCRConfig

app = FastAPI()
service = OCRService(OCRConfig())

@app.post("/ocr")
async def run_ocr(file: UploadFile):
    img = Image.open(io.BytesIO(await file.read()))
    result = service.process(img)
    return JSONResponse(content=json.loads(result.to_json()))