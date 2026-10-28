# ==================== 文件说明 ====================
# 这是整个 RAG 智能问答系统的入口文件
# 负责创建 FastAPI 应用、初始化所有核心组件、配置中间件和路由
#
# 本版关键变化：
# 1. query_llm 和 plan_llm 合并为单一 plan_llm（非流式），
#    避免两处各自 new ChatOpenAI，并保证改写/规划/反思共用同一实例
# 2. LangSmith 启动判断增加空字符串防护：
#    pydantic 会把空 LANGSMITH_API_KEY= 解析成 SecretStr('')，
#    它的 bool 为 True，会造成误初始化
# 3. 【健康检查优化】外部 API 检查加 30s TTL 缓存，
#    避免 /health 每次同步打外部接口被拖挂
# 4. 【健康检查优化】拆分 /livez 和 /readyz：
#    livez 只看进程存活（给容器 HEALTHCHECK 用），
#    readyz 检查内部存储 + 外部依赖（给负载均衡探针用），
#    /health 保留兼容并额外返回模型信息

# ==================== 导入依赖 ====================
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

import os
import time
import uuid
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

import structlog
from langchain_openai import ChatOpenAI

from core.config import settings
from core.logger import logger
from core.llm import get_llm_singleton, get_embeddings_singleton
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from storage.graph_store import GraphStore
from retrieval.graph_retriever import GraphRetriever
from retrieval.searchers import HybridSearcher
from retrieval.reranker import Reranker
from retrieval.rewriter import QueryRewriter
from generation.generator import Generator
from graphs.agentic_rag import AgenticRAG
from api.routes import router
from core.cache import MemoryCache

# ==================== 常量定义 ====================
GRAPH_PERSIST_PATH = "chroma_db/graph.json"
VECTOR_PERSIST_DIR = "chroma_db/vector"
BM25_PERSIST_PATH = "chroma_db/bm25.pkl"
EXTERNAL_HEALTH_TTL = 30  # 外部 API 健康检查缓存时间（秒）

os.makedirs("chroma_db", exist_ok=True)

# ==================== 外部健康检查缓存 ====================
# data 为 None 表示尚未检查过；expire_at 是下次过期的 time.time()
_external_health_cache = {"data": None, "expire_at": 0.0}
_external_health_lock = asyncio.Lock()

# ==================== 应用生命周期管理 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理器：负责初始化和清理资源"""

    langsmith_key = None
    if settings.langsmith_api_key is not None:
        # SecretStr('') 的 bool 为 True，必须显式取字符串再判断
        langsmith_key = settings.langsmith_api_key.get_secret_value()

    if settings.langsmith_tracing and langsmith_key:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
        os.environ["LANGSMITH_API_KEY"] = langsmith_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        logger.info("langsmith_enabled")
    else:
        os.environ["LANGSMITH_TRACING"] = "false"

    vector_store = VectorStore(collection_name="rag_demo", persist_dir=VECTOR_PERSIST_DIR)

    bm25_index = BM25Index()
    if os.path.exists(BM25_PERSIST_PATH):
        bm25_index.load(BM25_PERSIST_PATH)

    graph_store = GraphStore(persist_path=GRAPH_PERSIST_PATH)
    graph_retriever = GraphRetriever(graph_store)

    llm = get_llm_singleton()
    embeddings = get_embeddings_singleton()

    # 单一非流式 LLM：供 QueryRewriter / plan_node / reflection_node 共用
    # streaming=False 确保不会污染 /chat/stream 的 token 事件流
    plan_llm = ChatOpenAI(
        model=llm.model_name,
        api_key=llm.openai_api_key,
        base_url=llm.openai_api_base,
        temperature=0.2,
        streaming=False,
        request_timeout=60,
        max_retries=1,
    )

    searcher = HybridSearcher(vector_store, bm25_index, graph_retriever, embeddings)
    reranker = Reranker(embeddings)
    generator = Generator(llm)
    rewriter = QueryRewriter(plan_llm)
    cache = MemoryCache(max_size=settings.cache_max_size)

    agentic_rag = AgenticRAG(
        searcher=searcher,
        graph_retriever=graph_retriever,
        llm=llm,
        plan_llm=plan_llm,
        cache=cache,
        generator=generator,
        reranker=reranker,
        rewriter=rewriter,
    )

    app.state.agentic_rag = agentic_rag
    app.state.vector_store = vector_store
    app.state.bm25_index = bm25_index
    app.state.graph_store = graph_store
    app.state.cache = cache

    logger.info("storage_initialized")

    yield

    if graph_store:
        graph_store.save()
    if bm25_index:
        bm25_index.save(BM25_PERSIST_PATH)

    logger.info("app_shutdown")

# ==================== 创建 FastAPI 应用 ====================
app = FastAPI(
    title="Advanced RAG System",
    version="0.4.1",
    description="Agentic RAG 智能问答系统（优化版）",
    lifespan=lifespan,
)

# ==================== 中间件 ====================
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.bind_contextvars(request_id=request_id)
    logger.info("request_started", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_finished", status_code=response.status_code)
        return response
    finally:
        structlog.contextvars.unbind_contextvars("request_id")

@app.middleware("http")
async def global_exception_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"}
        )

# ==================== 路由 ====================
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# ==================== 健康检查内部实现 ====================
async def _check_external_apis():
    """检查外部 API，带 TTL 缓存，避免 /health 频繁打外部接口

    返回：(checks_dict, cached_bool)
    并发时用锁串行化，第二个请求会命中第一个请求写入的缓存。
    """
    async with _external_health_lock:
        now = time.time()
        if (
            _external_health_cache["data"] is not None
            and now < _external_health_cache["expire_at"]
        ):
            return _external_health_cache["data"], True

        async def check_api(name, base_url, api_key):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        base_url.rstrip("/") + "/models",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    if resp.status_code == 200:
                        return name, "ok"
                    return name, f"status {resp.status_code}"
            except Exception as e:
                return name, f"error: {str(e)}"

        zhipu_task = check_api(
            "zhipu_api",
            settings.zhipu_base_url,
            settings.zhipu_api_key.get_secret_value(),
        )
        sil_task = check_api(
            "siliconflow_api",
            settings.llm_base_url,
            settings.llm_api_key.get_secret_value(),
        )
        results = await asyncio.gather(zhipu_task, sil_task)

        data = {name: status for name, status in results}
        _external_health_cache["data"] = data
        _external_health_cache["expire_at"] = time.time() + EXTERNAL_HEALTH_TTL
        return data, False


async def _build_health(request: Request) -> dict:
    """构建健康检查结果（内部存储 + 外部依赖）"""
    health_status = {"status": "ok", "checks": {}}

    vs = request.app.state.vector_store
    try:
        health_status["checks"]["chromadb"] = "ok"
        health_status["doc_count"] = vs.count()
    except Exception as e:
        health_status["checks"]["chromadb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    bm = request.app.state.bm25_index
    try:
        health_status["checks"]["bm25_index"] = "ok"
        health_status["bm25_doc_count"] = bm.count()
    except Exception as e:
        health_status["checks"]["bm25_index"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    cache = getattr(request.app.state, "cache", None)
    if cache is not None:
        try:
            health_status["cache"] = cache.stats()
        except Exception as e:
            health_status["cache"] = {"error": str(e)}
            health_status["status"] = "degraded"

    ext, cached = await _check_external_apis()
    health_status["checks"].update(ext)
    health_status["external_cached"] = cached
    for st in ext.values():
        if st != "ok":
            health_status["status"] = "degraded"

    return health_status


@app.get("/livez")
async def livez():
    """liveness：进程活着即 200，不检查任何依赖

    给容器 HEALTHCHECK 使用。外部 API 抖动不应该杀容器。
    """
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request):
    """readiness：检查内部存储 + 外部依赖（外部带 30s TTL 缓存）

    给负载均衡 / K8s readinessProbe 使用。
    """
    return await _build_health(request)


@app.get("/health")
async def health(request: Request):
    """详细健康检查：保留兼容，额外返回模型信息"""
    h = await _build_health(request)
    h["models"] = {
        "generation": settings.zhipu_model,
        "embedding": settings.embedding_model,
    }
    return h