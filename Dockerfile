# 智知因 - 生产级API服务Dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装uvicorn（支持uvloop加速）
RUN pip install --no-cache-dir uvicorn[standard]==0.27.0

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖（优化层级）
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    cp -r /install/* /usr/local/ && \
    rm -rf /install

# 复制应用代码
COPY app/ ./app/
COPY config.py ./

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 非root用户运行（安全增强）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令 - 生产环境优化
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["uvicorn", "app.api.routes:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--limit-concurrency", "100", \
     "--limit-max-requests", "1000", \
     "--timeout-keep-alive", "60"]
