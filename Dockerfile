# 1. Base image nhẹ
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# 2. Cài dependencies hệ thống cho Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget unzip gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdbus-1-3 libx11-xcb1 \
    libxcomposite1 libxdamage1 libxrandr2 libgtk-3-0 libasound2 libgbm1 libxss1 libxtst6 \
 && rm -rf /var/lib/apt/lists/*

# 3. Tạo workdir và copy requirements
WORKDIR /app
COPY requirements.txt /app/

# 4. Cài Python packages và Chromium
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && playwright install --with-deps chromium

# 5. Copy code vào container
COPY main.py /app/

# 6. Expose port 3344
EXPOSE 3344

# 7. Start FastAPI server trên port 3344
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3344"]
