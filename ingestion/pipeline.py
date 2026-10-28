# ==================== 文件说明 ====================
# 这是文档入库流水线模块，负责将文档完整地存入系统
# 流程：加载 → 分块 → 去重 → 建图 → 向量化入库 → 构建 BM25 → 清缓存
#
# 本版关键变化（相对上一版）：
# 【P2】BM25 移出 batch 循环，最后统一 add_documents 一次。
# 原实现每 20 条就 jieba 全量分词 + 重建 BM25Okapi，
# 5000 个 chunk 会触发 250 次全量重建，上传明显卡顿。

# ==================== 导入依赖 ====================
import hashlib
from typing import List, Set
from langchain_core.documents import Document
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from storage.graph_store import GraphStore
from core.config import settings
from core.llm import get_embeddings_singleton
from core.logger import logger
from ingestion.loaders import load_document
from ingestion.splitter import split_documents
from ingestion.graph_builder import extract_triplets

# ==================== 内部函数：计算内容哈希 ====================
def _compute_content_hash(text: str) -> str:
    """计算文本内容的 MD5 哈希值，用于内容去重"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

# ==================== 主函数：运行入库流水线 ====================
def run_ingestion(
    file_path: str,
    vector_store: VectorStore,
    bm25_index: BM25Index,
    graph_store: GraphStore = None,
    chunk_size: int = None,
    chunk_overlap: int = None,
    cache=None,
):
    """运行文档入库流水线（主入口函数）

    参数：
        file_path: 文档文件路径
        vector_store: 向量存储实例
        bm25_index: BM25 索引实例
        graph_store: 知识图谱存储实例（可选）
        chunk_size: 分块大小（可选，默认使用配置值）
        chunk_overlap: 块重叠大小（可选，默认使用配置值）
        cache: 应用级缓存实例（可选）。入库成功后清空，避免旧答案命中

    返回：
        int: 成功存储的文档块数量
    """
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    # 步骤1：加载文档
    docs = load_document(file_path)

    if not docs:
        logger.warning("empty_document", file_path=file_path)
        return 0

    # 步骤2：分块
    chunks = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # 步骤3：去重（基于内容哈希）
    seen_hashes: Set[str] = set()
    unique_chunks: List[Document] = []

    for chunk in chunks:
        h = _compute_content_hash(chunk.page_content)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique_chunks.append(chunk)

    logger.info("deduplication_done", original=len(chunks), unique=len(unique_chunks))

    if not unique_chunks:
        logger.warning("all_chunks_duplicated", file_path=file_path)
        return 0

    texts = [chunk.page_content for chunk in unique_chunks]
    metadatas = [chunk.metadata for chunk in unique_chunks]

    # 步骤4：构建知识图谱（如果提供了 graph_store）
    if graph_store:
        try:
            triplets = extract_triplets(texts)
            if triplets:
                graph_store.add_triplets(triplets)
            logger.info("graph_built", triplets=len(triplets))
        except Exception as e:
            logger.error("graph_build_failed", error=str(e))

    # 步骤5：嵌入并分批写入向量库；BM25 最后统一构建一次
    embed_model = get_embeddings_singleton()
    batch_size = 20
    total_stored = 0

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]

        try:
            batch_embs = embed_model.embed_documents(batch_texts)
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

        vector_store.add_documents(batch_texts, batch_embs, metadatas[i:i + batch_size])
        total_stored += len(batch_texts)

    # BM25 只在最后统一重建一次。
    # 原实现每 20 条就 jieba 全量分词 + 重建 BM25Okapi，
    # 5000 个 chunk 会触发 250 次全量重建，上传明显卡顿。
    if texts:
        bm25_index.add_documents(texts)

    # 步骤6：清除缓存（使用注入的 cache，而不是新建实例）
    if cache is not None:
        cache.clear()
        logger.info("cache_cleared_after_ingestion")

    logger.info("ingestion_complete", file_path=file_path, chunks_stored=total_stored)

    return total_stored