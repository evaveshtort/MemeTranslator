FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY vision_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN iopaint start --model lama --device cpu --port 8080 --host 0.0.0.0 &sleep 180 && kill %1 || true

COPY vision_module/ /app/vision_module/

CMD ["uvicorn", "vision_module.server:app", "--host", "0.0.0.0", "--port", "8002"]