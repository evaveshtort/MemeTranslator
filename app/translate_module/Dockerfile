FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY translate_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Convert opus-mt-ru-en to CTranslate2 format at build time (not at runtime)
RUN pip install --no-cache-dir transformers && \
    ct2-marian-converter --model Helsinki-NLP/opus-mt-ru-en --output_dir /models/opus-mt-ru-en --force && \
    pip uninstall -y transformers && \
    pip cache purge

COPY translate_module/ /app/translate_module/

CMD ["uvicorn", "translate_module.server:app", "--host", "0.0.0.0", "--port", "8003"]
