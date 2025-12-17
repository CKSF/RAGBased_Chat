FROM python:3.10-slim

WORKDIR /app

# 🇨🇳 CHINA FIX: Mirror
ENV HF_ENDPOINT=https://hf-mirror.com

# Install dependencies
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# Copy requirements from the backend folder
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt && \
    pip install waitress

# COPY STRATEGY: 
# 1. Copy the 'backend' folder into /app/backend
COPY backend/ backend/

# 2. Copy 'run.py' from root into /app/run.py
COPY run.py .

EXPOSE 5001

CMD ["python", "run.py"]