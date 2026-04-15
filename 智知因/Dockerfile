# 智知因 - Docker 构建文件
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/knowledge_base

# 暴露端口
EXPOSE 8000 8501

# 启动命令
# 默认启动后端 API
CMD ["uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8000"]
