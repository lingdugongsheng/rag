# ==================== 文件说明 ====================
# 这是重排序模块，负责对检索结果进行精排
# 支持两种重排序方法：
# 1. Cross-Encoder（交叉编码器）：更准确但较慢
# 2. 嵌入相似度（余弦相似度）：快速但精度稍低
#
# 本版关键变化：
# 1. 文档 embedding 加 LRU 缓存（默认 2048 条），
#    同一文档多次被检索到时不再重复调用 embedding API
# 2. 未命中的文档批量 embed，命中缓存的不发请求
# 3. rerank_done 日志增加 cache_hits / cache_misses / elapsed_ms，
#    可直接在日志里看到优化效果
# 4. 【并发修复】_cache 的读写加 threading.Lock，
#    因为 rerank() 跑在 asyncio.to_thread 里，多请求并发时
#    OrderedDict 的 move_to_end / popitem 不是线程安全的
# 5. 【并发修复】hits / misses 改为本次调用的返回值，
#    不再用全局计数器差值，避免并发下统计失真
# 6. 【P1-2】embedding 返回数量与请求不一致时显式抛错，
#    避免 zip 静默截断 -> results 里留 None -> np.array 变 object ->
#    np.linalg.norm 抛异常 -> 外层 catch 后返回未排序结果（重排静默失效）。

# ==================== 导入依赖 ====================
import threading
import time
from collections import OrderedDict
from hashlib import md5
from typing import List, Dict, Optional, Tuple

import numpy as np

from core.config import settings
from core.logger import logger

# ==================== 重排序器类 ====================
class Reranker:
    """重排序器

    对检索结果进行精排，提高文档相关性
    """

    def __init__(self, embeddings, cache_size: int = 2048):
        """初始化重排序器

        参数：
            embeddings: 嵌入模型实例（用于嵌入相似度方法）
            cache_size: 文档 embedding 缓存条数上限
        """
        self.embeddings = embeddings
        self.method = settings.rerank_method

        # LRU 缓存：key 是文档文本的 md5，value 是 embedding
        self._cache: "OrderedDict[str, List[float]]" = OrderedDict()
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = threading.Lock()  # 保护 _cache 与计数器的并发访问

        if self.method == "cross_encoder":
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(settings.cross_encoder_model)
                logger.info("reranker_initialized", method="cross_encoder")
            except ImportError:
                logger.warning("sentence_transformers not available, falling back to embedding similarity")
                self.method = "embedding_similarity"
        else:
            self.method = "embedding_similarity"

    # -------------------- 缓存相关 --------------------

    @staticmethod
    def _key(text: str) -> str:
        return md5(text.encode("utf-8")).hexdigest()

    def _get_doc_embeddings_batch(self, texts: List[str]) -> Tuple[List[List[float]], int, int]:
        """批量获取文档 embedding，命中缓存的不发请求

        返回：(embeddings, 本次 hits, 本次 misses)

        并发安全策略：
        1. 锁内：查缓存、收集 miss、更新计数器
        2. 锁外：批量调用 embedding API（不阻塞其他线程读写缓存）
        3. 锁内：写回缓存，超容量时淘汰最久未用

        [改动] 第 4 步写回缓存前校验 embedding 数量：
        数量不一致时抛 RuntimeError，由 rerank() 捕获后降级为未排序结果。
        原实现用 zip 静默截断，results 里残留 None，
        np.array 变 object array，np.linalg.norm 抛异常被外层 catch，
        导致重排静默失效且日志看不出原因。
        """
        keys = [self._key(t) for t in texts]
        results: List[Optional[List[float]]] = [None] * len(texts)
        miss_indices: List[int] = []
        miss_texts: List[str] = []
        hits = 0

        with self._cache_lock:
            for i, key in enumerate(keys):
                if key in self._cache:
                    self._cache.move_to_end(key)
                    results[i] = self._cache[key]
                    hits += 1
                else:
                    miss_indices.append(i)
                    miss_texts.append(texts[i])
            self._cache_hits += hits
            self._cache_misses += len(miss_indices)

        if miss_texts:
            try:
                new_embs = self.embeddings.embed_documents(miss_texts)
            except Exception as e:
                logger.error("rerank_embedding_failed", error=str(e))
                raise

            # [改动] 数量校验：不一致立刻抛，不静默截断
            if len(new_embs) != len(miss_texts):
                raise RuntimeError(
                    f"embedding count mismatch: expected {len(miss_texts)}, got {len(new_embs)}"
                )

            with self._cache_lock:
                for idx, emb in zip(miss_indices, new_embs):
                    key = keys[idx]
                    if key in self._cache:
                        # 并发下其他线程已写入同一文档，复用现有值避免覆盖
                        self._cache.move_to_end(key)
                        results[idx] = self._cache[key]
                    else:
                        self._cache[key] = emb
                        results[idx] = emb
                        if len(self._cache) > self._cache_size:
                            self._cache.popitem(last=False)

        # 到这里 results 每个位置都应有值（若数量校验通过）
        return results, hits, len(miss_indices)  # type: ignore[return-value]

    def _current_cache_size(self) -> int:
        with self._cache_lock:
            return len(self._cache)

    # -------------------- 重排序主入口 --------------------

    def rerank(self, query: str, documents: List[Dict], top_k: int = None) -> List[Dict]:
        """对文档进行重排序

        参数：
            query: 用户查询
            documents: 待重排序的文档列表
            top_k: 返回结果数量（可选，默认使用配置值）

        返回：
            List[Dict]: 重排序后的文档列表，按相关性降序排列
        """
        top_k = top_k or settings.rerank_top_k

        if not documents:
            return []

        started = time.time()
        doc_texts = [doc.get("text", "") for doc in documents]
        hits, misses = 0, 0

        if self.method == "cross_encoder":
            try:
                pairs = [[query, txt] for txt in doc_texts]
                scores = self.cross_encoder.predict(pairs)
                for i, doc in enumerate(documents):
                    doc["rerank_score"] = float(scores[i])
            except Exception as e:
                logger.error("cross_encoder_rerank_failed", error=str(e))
                return documents[:top_k]
        else:
            try:
                # 查询向量（单条，不缓存）
                query_emb = np.array(self.embeddings.embed_query(query))

                # 文档向量（批量 + 线程安全 LRU 缓存）
                doc_embs_raw, hits, misses = self._get_doc_embeddings_batch(doc_texts)
                doc_embs = np.array(doc_embs_raw)

                # 归一化 + 余弦相似度
                query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-8)
                doc_norms = doc_embs / (np.linalg.norm(doc_embs, axis=1, keepdims=True) + 1e-8)
                scores = np.dot(doc_norms, query_norm)

                for i, doc in enumerate(documents):
                    doc["rerank_score"] = float(scores[i])
            except Exception as e:
                logger.error("rerank_embedding_failed", error=str(e))
                return documents[:top_k]

        sorted_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        elapsed_ms = int((time.time() - started) * 1000)
        logger.info(
            "rerank_done",
            query=query,
            input_count=len(documents),
            output_count=min(top_k, len(sorted_docs)),
            cache_hits=hits,
            cache_misses=misses,
            cache_size=self._current_cache_size(),
            elapsed_ms=elapsed_ms,
        )

        return sorted_docs[:top_k]