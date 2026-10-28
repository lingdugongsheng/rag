# ==================== 文件说明 ====================
# 生产镜像：Python 3.11 slim，非 root 用户，健康检查内置
#
# 本版关键变化（相对上一版）：
# 【P1-1】HEALTHCHECK 从 /health 改为 /livez。
# /health 会检查智谱和硅基流动的外部 API，外部抖动会让容器被判 unhealthy
# 进而被重启，而进程本身是好的。/livez 只看进程存活，才是容器 liveness 该用的探针；
# /readyz 留给负载均衡 / K8s readinessProbe。

FROM python:3.11-slim

# 系统依赖：
# - build-essential：部分包编译需要
# - curl：健康检查
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 非 root 用户
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝代码
COPY . .

# 持久化目录和权限
RUN mkdir -p /app/chroma_db && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/livez || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]