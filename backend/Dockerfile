FROM python:3.10-slim

WORKDIR /app

# 🇨🇳 CHINA FIX: Use Aliyun Debian Mirror
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 🇨🇳 CHINA FIX: Set HF Mirror
ENV HF_ENDPOINT=https://hf-mirror.com

RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*

# 🇨🇳 CHINA FIX: Use Aliyun PyPI Mirror
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir -r backend/requirements.txt && \
    pip install -i https://mirrors.aliyun.com/pypi/simple/ waitress

COPY backend/ backend/
COPY run.py .

EXPOSE 5001

CMD ["python", "run.py"]