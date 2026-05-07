FROM python:3.11-slim
WORKDIR /app

# Install ffmpeg for audio conversion
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure storage directory exists
RUN mkdir -p /var/ghostwriter/documents

# Set the Python path
ENV PYTHONPATH=/app
