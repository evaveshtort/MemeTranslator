FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y \
    libgl1 libglib2.0-0 fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/fonts/truetype/robotoflex && \
    curl -fsSL -o /usr/share/fonts/truetype/robotoflex/RobotoFlex.ttf \
    "https://github.com/google/fonts/raw/main/ofl/robotoflex/RobotoFlex%5BGRAD%2CXOPQ%2CXTRA%2CYOPQ%2CYTAS%2CYTDE%2CYTFI%2CYTLC%2CYTUC%2Copsz%2Cslnt%2Cwdth%2Cwght%5D.ttf"

COPY translate_module/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY translate_module/ /app/translate_module/

CMD ["uvicorn", "translate_module.server:app", "--host", "0.0.0.0", "--port", "8003"]
