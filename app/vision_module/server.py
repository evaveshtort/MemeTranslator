from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
import json
import tempfile
import os

from .text_removal import remove_text
from .captioning import describe_image

app = FastAPI()

@app.post("/remove-text")
async def api_remove_text(file: UploadFile, blocks: str):
    img = Image.open(io.BytesIO(await file.read()))
    result = remove_text(img, json.loads(blocks))

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(buf, media_type="image/png")

@app.post("/caption")
async def api_caption(file: UploadFile):
    data = await file.read()
    
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        text = describe_image(tmp_path)
    finally:
        os.unlink(tmp_path)
    return {"caption": text}