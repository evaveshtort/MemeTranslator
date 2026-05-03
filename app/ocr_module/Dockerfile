FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ocr_module/requirements.txt .

RUN pip install --no-cache-dir torch==2.11.0 \
    --index-url https://download.pytorch.org/whl/cu124
RUN grep -v "^torch" requirements.txt | pip install --no-cache-dir -r /dev/stdin

COPY ocr_module/ /app/ocr_module/

CMD ["uvicorn", "ocr_module.server:app", "--host", "0.0.0.0", "--port", "8001"]