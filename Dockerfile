FROM python:3.11-slim

# Avoid interactive prompts and keep image small
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for WiFi RSSI reading
RUN apt-get update && apt-get install -y \
    iw \
    wireless-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Default command
CMD ["python", "src/motion_detector.py"]
