# 使用Python 3.9作为基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=${PORT:-5000}
ENV LOG_DIR=/app/logs

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建必要的目录
RUN mkdir -p /app/templates && \
    mkdir -p /app/uploads && \
    mkdir -p /app/logs

# 复制项目文件
COPY requirements.txt .
COPY *.py .
COPY cursorrules.yaml .

# 特别复制模板目录
COPY templates/* /app/templates/

# 设置目录权限
RUN chmod 755 /app/templates && \
    chmod 777 /app/uploads && \
    chmod 777 /app/logs

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE ${PORT}

# 启动命令
CMD gunicorn --bind 0.0.0.0:$PORT app:app --workers 4 --timeout 120 
