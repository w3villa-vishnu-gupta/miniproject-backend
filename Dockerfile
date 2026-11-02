FROM python:3.13-slim

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Set Python path
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Render sets $PORT dynamically (default 8000 or 10000)
ENV PORT=8000
EXPOSE 8000

# Start FastAPI using uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
