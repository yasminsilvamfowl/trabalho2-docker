FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Fontes DejaVu usadas no desenho do ingresso em PDF.
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py .
COPY processors ./processors

RUN useradd --create-home --uid 1000 worker
USER worker

CMD ["python", "worker.py"]
