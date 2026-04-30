FROM python:3.12-slim

WORKDIR /app

# Install system deps (for pg8000 and other packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run requires listening on PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Use gunicorn-style uvicorn workers for production
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"]
