# ==================== 文件说明 ====================
# 这是 BM25 关键词索引模块，负责基于关键词匹配进行检索
# BM25（Best Matching 25）是一种常用的信息检索算法
# 主要功能：
# 1. 对文档进行分词并建立索引
# 2. 根据查询关键词计算文档相关性分数
# 3. 支持索引的保存和加载

# ==================== 导入依赖 ====================
import pickle  # 序列化（保存和加载索引）
from typing import List, Dict  # 类型提示
import jieba  # 中文分词工具
from rank_bm25 import BM25Okapi  # BM25 算法实现
from core.logger import logger  # 日志工具

# ==================== BM25 索引类 ====================
class BM25Index:
    """BM25 关键词索引
    
    使用 BM25 算法进行关键词检索
    支持中文分词（jieba）
    """
    
    def __init__(self):
        """初始化 BM25 索引"""
        # 存储所有文档文本
        self.texts: List[str] = []
        # BM25 索引实例（初始为 None）
        self.bm25 = None

    def add_documents(self, texts: List[str]):
        """添加文档到索引
        
        参数：
            texts: 文档文本列表
        """
        # 如果文本列表为空，直接返回
        if not texts:
            return
        
        # 将新文档添加到文本列表
        self.texts.extend(texts)
        
        # 重建索引（每次添加后重新构建）
        self._rebuild_index()
        
        # 记录日志（添加数量和总数量）
        logger.info("bm25_documents_added", count=len(texts), total=len(self.texts))

    def _rebuild_index(self):
        """重建 BM25 索引（内部方法）
        
        步骤：
        1. 对所有文档进行分词
        2. 使用分词结果构建 BM25 索引
        """
        # 对每个文档进行分词（jieba.cut 返回分词结果）
        tokenized_corpus = [list(jieba.cut(text)) for text in self.texts]
        
        # 创建 BM25 索引实例
        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """根据关键词搜索文档
        
        参数：
            query: 查询文本
            top_k: 返回前 k 个最相关的文档（默认5）
            
        返回：
            List[Dict]: 文档列表，每个文档包含文本和相关性分数
        """
        # 如果索引未构建或没有文档，返回空列表
        if not self.bm25 or not self.texts:
            return []
        
        # 对查询进行分词
        tokenized_query = list(jieba.cut(query))
        
        # 使用 BM25 计算每个文档的相关性分数
        scores = self.bm25.get_scores(tokenized_query)
        
        # 将分数和索引配对（方便排序）
        indexed_scores = list(enumerate(scores))
        
        # 按分数降序排序（分数越高越相关）
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 取前 top_k 个结果
        top_indices = indexed_scores[:top_k]
        
        # 格式化结果
        results = []
        for idx, score in top_indices:
            results.append({
                "text": self.texts[idx],  # 文档文本
                "score": float(score)     # BM25 分数
            })
        
        # 返回结果列表
        return results

    def count(self) -> int:
        """获取索引中的文档数量
        
        返回：
            int: 文档数量
        """
        return len(self.texts)

    def save(self, path: str):
        """保存索引到文件
        
        参数：
            path: 文件路径
        """
        try:
            # 使用 pickle 序列化文本列表
            with open(path, 'wb') as f:
                pickle.dump(self.texts, f)
            
            # 记录日志
            logger.info("bm25_saved", path=path)
        except Exception as e:
            # 如果保存失败，记录错误日志
            logger.error("bm25_save_failed", error=str(e))

    def load(self, path: str):
        """从文件加载索引
        
        参数：
            path: 文件路径
        """
        try:
            # 使用 pickle 反序列化文本列表
            with open(path, 'rb') as f:
                self.texts = pickle.load(f)
            
            # 加载后重建索引
            self._rebuild_index()
            
            # 记录日志
            logger.info("bm25_loaded", count=len(self.texts))
        except Exception as e:
            # 如果加载失败，记录错误日志
            logger.error("bm25_load_failed", error=str(e))
