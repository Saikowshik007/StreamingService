FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg for thumbnail generation
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY config.py .
COPY firebase_config.py .
COPY firebase_service.py .
COPY folder_scanner.py .
COPY folder_watcher.py .
COPY thumbnail_generator.py .

# Create media directory
RUN mkdir -p /media

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Run the application
CMD ["python", "app.py"]
