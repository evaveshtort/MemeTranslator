FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY translate_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY translate_module/ /app/translate_module/

CMD ["uvicorn", "translate_module.server:app", "--host", "0.0.0.0", "--port", "8003"]
