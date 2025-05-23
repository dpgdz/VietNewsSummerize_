FROM python:3.9-slim

# Cài đặt các công cụ cơ bản (nếu cần cho build C dependencies như torch, transformers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc wget curl && \
    rm -rf /var/lib/apt/lists/*

# Đặt thư mục làm việc
WORKDIR /app

# Cài đặt thư viện trước để tận dụng cache layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir sentencepiece==0.1.99

# Sao chép toàn bộ source code
COPY . .

# Expose port 8000
EXPOSE 8000

# Khởi động ứng dụng với reload nếu cần phát triển
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
