FROM python:3.10-slim

WORKDIR /app

# 🇨🇳 CHINA FIX 1: Use Aliyun Debian Mirror (Speeds up apt-get)
# We replace default sources with Aliyun mirrors before running updates
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 🇨🇳 CHINA FIX 2: Set HF Mirror
ENV HF_ENDPOINT=https://hf-mirror.com

# Install system dependencies (Now fast!)
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# 🇨🇳 CHINA FIX 3: Use Aliyun PyPI Mirror (Speeds up pip install)
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir -r backend/requirements.txt && \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ waitress

COPY backend/ backend/
COPY run.py .

EXPOSE 5001

CMD ["python", "run.py"]