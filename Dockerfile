FROM python:3.11-slim

# tesseract-ocr is the actual OCR engine; pytesseract is just a wrapper around it
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# SQLite file (and saved screenshots) should live on a persistent volume if
# your host supports one, otherwise they reset whenever the container
# restarts/redeploys.
EXPOSE 8080
CMD ["python", "app.py"]
