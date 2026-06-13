# Build a partir da RAIZ do repositório (a imagem embute também o frontend):
#   docker build -f backend/Dockerfile -t prompt-master .
#   docker run -p 8000:8000 -v prompt-master-dados:/data prompt-master
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY docs ./docs

RUN mkdir -p /data
ENV DB_PATH=/data/prompts.db

EXPOSE 8000

# Shell form para a plataforma poder injetar $PORT (Render, Railway etc.).
# SQLite + escrita: manter 1 worker.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
