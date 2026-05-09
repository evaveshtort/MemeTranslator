FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY translate_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and convert opus-mt-ru-en to CTranslate2 format at build time
RUN pip install --no-cache-dir transformers && \
    python -c "from huggingface_hub import snapshot_download; snapshot_download('Helsinki-NLP/opus-mt-ru-en', local_dir='/tmp/opus-mt')" && \
    ct2-marian-converter \
        --model_path /tmp/opus-mt \
        --vocab_paths /tmp/opus-mt/source.spm /tmp/opus-mt/target.spm \
        --output_dir /models/opus-mt-ru-en \
        --force && \
    rm -rf /tmp/opus-mt && \
    pip uninstall -y transformers && \
    pip cache purge

COPY translate_module/ /app/translate_module/

CMD ["uvicorn", "translate_module.server:app", "--host", "0.0.0.0", "--port", "8003"]
