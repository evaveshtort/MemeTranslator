FROM python:3.11-slim

WORKDIR /app
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

COPY api/ /app/api/

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]