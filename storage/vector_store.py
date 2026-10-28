# ==================== 文件说明 ====================
# 这是向量存储模块，使用 ChromaDB 作为底层存储
# 主要功能：
# 1. 添加文档向量到向量库
# 2. 搜索与查询向量最相似的文档
# 3. 支持持久化存储（重启后数据不丢失）
#
# 本版关键变化：
# 创建 collection 时显式指定 hnsw:space=cosine。
# Chroma 默认是 L2 距离，此前用 score = 1 - distance 当相似度，
# 在 L2 下分数可能为负且语义不对；改用 cosine 后，
# distance ∈ [0, 2]，score = 1 - distance 才有"越高越相似"的语义。

# ==================== 导入依赖 ====================
import uuid
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from core.logger import logger

# ==================== 向量存储类 ====================
class VectorStore:
    """向量存储

    使用 ChromaDB 存储和检索文档向量
    支持持久化和内存两种模式
    """

    def __init__(self, collection_name: str = "default", persist_dir: Optional[str] = None):
        """初始化向量存储

        参数：
            collection_name: 集合名称（相当于数据库表名）
            persist_dir: 持久化目录（如果提供，数据会保存到磁盘）
        """
        if persist_dir:
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.EphemeralClient(
                settings=ChromaSettings(anonymized_telemetry=False)
            )

        # 关键：显式指定 cosine 距离度量
        # 如果集合已存在且度量方式不同，Chroma 会沿用已有配置；
        # 想切换度量方式需要删掉旧 collection 目录后重新创建。
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            "vector_store_initialized",
            collection=collection_name,
            persist=bool(persist_dir),
            distance="cosine",
        )

    def add_documents(self, texts: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict]] = None):
        """添加文档到向量库

        参数：
            texts: 文档文本列表
            embeddings: 文档向量列表（每个向量是一个 float 列表）
            metadatas: 文档元数据列表（可选，如来源、页码等）
        """
        ids = [str(uuid.uuid4()) for _ in texts]

        if metadatas:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas
            )
        else:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts
            )

        logger.info("documents_added", count=len(texts))

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        """搜索与查询向量最相似的文档

        参数：
            query_embedding: 查询向量
            top_k: 返回最相似的前 k 个文档（默认5）

        返回：
            List[Dict]: 文档列表，每个文档包含 ID、文本、元数据和相似度分数
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        docs = []

        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # cosine 距离 ∈ [0, 2]，转换到相似度并裁剪到 [0, 1]
                score = max(0.0, min(1.0, 1.0 - distance))
                docs.append({
                    "id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": score,
                })

        return docs

    def count(self) -> int:
        """获取向量库中的文档数量

        返回：
            int: 文档数量
        """
        return self.collection.count()