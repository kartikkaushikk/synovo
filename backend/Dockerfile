FROM python:3.11-slim

# System dependencies for audio processing + ML
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    build-essential \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Clear execstack flag for ctranslate2 shared libs (fixes WSL/secure kernels)
RUN find /usr/local/lib/python3.11/site-packages -name 'libctranslate2-*.so*' -print0 \
    | xargs -0 --no-run-if-empty patchelf --clear-execstack

# Copy source
COPY . .

# Set PYTHONPATH so `from app.xxx` and `from workers.xxx` work
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
