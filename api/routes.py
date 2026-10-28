# ==================== 文件说明 ====================
# 这是 API 路由定义文件
# 负责定义所有对外的 HTTP 接口（聊天、流式输出、文件上传、任务状态查询）
#
# 本版关键变化（相对上一版）：
# 1. 【P1-1】upload_file 去掉 background_tasks / req 的 `= None` 默认值，
#    改由 FastAPI 正常注入。原写法掩盖注入失败，且与 FastAPI 契约不一致。
# 2. /chat/stream 缓存命中时，cached_answer 之后补发 citations 事件，
#    保证缓存路径下前端也能显示"参考来源"。
# 3. 上传大小限制、分块读取、task_store TTL 与容量上限保持不变。

# ==================== 导入依赖 ====================
import os
import time
import uuid
import tempfile
import json
from typing import List, Tuple, Dict
import threading

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.logger import logger
from ingestion.pipeline import run_ingestion

router = APIRouter()

# ==================== 常量 ====================
MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50MB
UPLOAD_CHUNK_SIZE = 1024 * 1024       # 1MB 分块读取
TASK_TTL_SECONDS = 3600               # 任务 1 小时后过期
MAX_TASKS = 1000                      # task_store 最多保留的任务数

# ==================== 全局变量 ====================
task_store: Dict[str, dict] = {}
task_lock = threading.Lock()

# ==================== 内部函数：task_store 清理 ====================
def _cleanup_tasks_locked():
    """清理过期/超额任务。调用方必须持有 task_lock。"""
    now = time.time()

    # 1. 清掉过期任务
    expired = [
        tid for tid, t in task_store.items()
        if now - t.get("created_at", now) > TASK_TTL_SECONDS
    ]
    for tid in expired:
        task_store.pop(tid, None)

    # 2. 如果仍然超额，按创建时间删最旧的
    if len(task_store) > MAX_TASKS:
        sorted_items = sorted(task_store.items(), key=lambda kv: kv[1].get("created_at", 0))
        overflow = len(task_store) - MAX_TASKS
        for tid, _ in sorted_items[:overflow]:
            task_store.pop(tid, None)

# ==================== 数据模型定义 ====================
class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str
    history: List[Tuple[str, str]] = []

class ChatResponse(BaseModel):
    """聊天响应模型"""
    answer: str
    from_cache: bool
    citation_map: dict

class TaskStatus(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str
    message: str = ""
    chunks_stored: int = 0

# ==================== API 端点定义 ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """同步聊天接口：接收问题，返回完整回答"""
    agentic_rag = req.app.state.agentic_rag

    try:
        logger.info("chat_request_received", query=request.query)

        result = await agentic_rag.graph.ainvoke({
            "query": request.query,
            "chat_history": request.history,
            "streaming": False,
        })

        return ChatResponse(
            answer=result.get("answer", ""),
            from_cache=result.get("from_cache", False),
            citation_map=result.get("citation_map", {})
        )

    except Exception as e:
        logger.exception("chat_error")
        raise HTTPException(status_code=500, detail=f"生成回答时出错: {str(e)}")

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """流式聊天接口：实时返回回答（逐字输出）

    事件协议（SSE，data 为 JSON）：
    - {"token": "..."}           模型逐 token 输出
    - {"cached_answer": "..."}   缓存命中，一次性返回完整答案（无 token）
    - {"citations": {...}}       回答完成，附引用来源映射
    - {"error": "..."}           流式过程中发生异常
    - [DONE]                     流结束标记
    """
    agentic_rag = req.app.state.agentic_rag

    if not agentic_rag:
        raise HTTPException(status_code=503, detail="服务未就绪")

    async def event_generator():
        try:
            async for event in agentic_rag.graph.astream_events(
                {
                    "query": request.query,
                    "chat_history": request.history,
                    "streaming": True,
                },
                version="v2"
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    token = event["data"]["chunk"].content
                    if token:
                        yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

                elif kind == "on_chain_end":
                    name = event.get("name")
                    output = event.get("data", {}).get("output")
                    if not isinstance(output, dict):
                        continue

                    if name == "plan" and output.get("from_cache") and output.get("answer"):
                        yield f"data: {json.dumps({'cached_answer': output['answer']}, ensure_ascii=False)}\n\n"
                        # 缓存命中也要把引用来源发给前端，
                        # 否则缓存路径下答案下方的"参考来源"永远为空
                        if output.get("citation_map"):
                            yield f"data: {json.dumps({'citations': output['citation_map']}, ensure_ascii=False)}\n\n"
                        continue

                    if output.get("citation_map"):
                        yield f"data: {json.dumps({'citations': output['citation_map']}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.exception("stream_error")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/upload")
async def upload_file(
    req: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    # [改动] 去掉 background_tasks / req 的 `= None` 默认值，
    # 依赖 FastAPI 正常注入。参数顺序按"无默认值在前、有默认值在后"排列。
    """文件上传接口：上传文档并异步处理

    - 仅允许 .pdf / .txt / .md / .docx
    - 最大 50MB，超过返回 413
    - 文件分块写入临时文件，避免一次性读入内存
    """
    allowed_extensions = {".pdf", ".txt", ".md", ".docx"}

    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，仅支持 {', '.join(allowed_extensions)}")

    task_id = str(uuid.uuid4())

    # 分块写入临时文件，同时检查大小
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            total = 0
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE:
                    tmp_file.close()
                    try:
                        os.unlink(tmp_file.name)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过 {MAX_UPLOAD_SIZE // (1024 * 1024)}MB 限制"
                    )
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("upload_save_failed")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 写任务状态（顺带清理过期/超额任务）
    with task_lock:
        _cleanup_tasks_locked()
        task_store[task_id] = {
            "status": "processing",
            "message": "",
            "chunks_stored": 0,
            "created_at": time.time(),
        }

    vs = req.app.state.vector_store
    bm = req.app.state.bm25_index
    gs = req.app.state.graph_store
    cache = req.app.state.cache

    def process_document(file_path: str, task_id: str, cache):
        try:
            chunks_stored = run_ingestion(file_path, vs, bm, gs, cache=cache)

            with task_lock:
                entry = task_store.get(task_id, {})
                entry.update({
                    "status": "completed",
                    "message": "",
                    "chunks_stored": chunks_stored,
                })
                entry.setdefault("created_at", time.time())
                task_store[task_id] = entry

        except Exception as e:
            logger.exception("ingestion_task_failed", task_id=task_id)
            with task_lock:
                entry = task_store.get(task_id, {})
                entry.update({
                    "status": "failed",
                    "message": str(e),
                    "chunks_stored": 0,
                })
                entry.setdefault("created_at", time.time())
                task_store[task_id] = entry

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

    background_tasks.add_task(process_document, tmp_path, task_id, cache)

    return {"task_id": task_id, "status": "processing"}

@router.get("/task/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """查询文件上传任务的处理状态"""
    with task_lock:
        _cleanup_tasks_locked()
        task = task_store.get(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatus(task_id=task_id, **task)