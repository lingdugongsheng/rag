# ==================== 文件说明 ====================
# 这是混合检索器模块，负责融合多种检索方式的结果
# 支持三种检索方式：
# 1. 向量检索（基于语义相似度）
# 2. BM25 检索（基于关键词匹配）
# 3. 知识图谱检索（基于实体关系）
# 使用 RRF（倒数排序融合）算法合并结果
#
# 本版关键变化：
# 1. search 改为 async def，三路检索用 asyncio.gather 并行
# 2. 每一路都用 asyncio.to_thread 包裹，避免阻塞事件循环
# 3. 单路失败不影响其他路，失败的那一路返回空列表

# ==================== 导入依赖 ====================
import asyncio
from typing import List, Dict
from core.config import settings
from storage.vector_store import VectorStore
from storage.bm25_index import BM25Index
from retrieval.fusion import rrf_fusion
from retrieval.graph_retriever import GraphRetriever
from core.logger import logger

# ==================== 混合检索器类 ====================
class HybridSearcher:
    """混合检索器

    融合向量检索、BM25 检索和知识图谱检索的结果
    使用 RRF 算法进行结果合并，取各检索方式的优点
    """

    def __init__(self, vector_store: VectorStore, bm25_index: BM25Index,
                 graph_retriever: GraphRetriever, embeddings):
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.graph_retriever = graph_retriever
        self.embeddings = embeddings

    async def search(self, query: str, top_k: int = None, fusion_k: int = None) -> List[Dict]:
        """执行混合检索（异步并行版）

        参数：
            query: 用户查询
            top_k: 返回结果数量（可选，默认使用配置值）
            fusion_k: RRF 算法的参数 k（可选，默认使用配置值）

        返回：
            List[Dict]: 融合后的文档列表，按相关性排序
        """
        top_k = top_k or settings.retrieval_top_k
        fusion_k = fusion_k or settings.fusion_k

        # -------------------- 三路检索（并行） --------------------
        async def _vector_search():
            try:
                # embed_query 是同步 HTTP 调用，必须移出事件循环
                query_embedding = await asyncio.to_thread(self.embeddings.embed_query, query)
                # vector_store.search 是同步方法（可能涉及磁盘 IO）
                return await asyncio.to_thread(self.vector_store.search, query_embedding, top_k)
            except Exception as e:
                logger.error("vector_search_failed", error=str(e))
                return []

        async def _bm25_search():
            try:
                return await asyncio.to_thread(self.bm25_index.search, query, top_k)
            except Exception as e:
                logger.error("bm25_search_failed", error=str(e))
                return []

        async def _graph_search():
            if not self.graph_retriever:
                return []
            try:
                return await asyncio.to_thread(self.graph_retriever.search, query, top_k)
            except Exception as e:
                logger.error("graph_search_failed", error=str(e))
                return []

        vector_results, bm25_results, graph_results = await asyncio.gather(
            _vector_search(), _bm25_search(), _graph_search()
        )

        logger.debug("vector_search_done", count=len(vector_results))
        logger.debug("bm25_search_done", count=len(bm25_results))
        logger.debug("graph_search_done", count=len(graph_results))

        # -------------------- 融合结果 --------------------
        all_lists = [lst for lst in [vector_results, bm25_results, graph_results] if lst]
        if not all_lists:
            return []

        combined = all_lists[0]
        for lst in all_lists[1:]:
            combined = rrf_fusion(combined, lst, k=fusion_k, id_field="text", top_k=top_k)

        logger.info("hybrid_search_done", query=query, result_count=len(combined))
        return combined