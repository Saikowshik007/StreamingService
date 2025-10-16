FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg for thumbnail generation
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python application files
COPY *.py .

# Create media directory
RUN mkdir -p /media

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# Run the application
CMD ["python", "app.py"]
