# ==================== 文件说明 ====================
# 这是知识图谱检索模块，负责从知识图谱中检索相关信息
# 检索流程：
# 1. 从查询中提取实体
# 2. 在图谱中查找实体的邻居节点
# 3. 返回相关的三元组信息

# ==================== 导入依赖 ====================
from typing import List, Dict  # 类型提示
from storage.graph_store import GraphStore  # 知识图谱存储
from core.logger import logger  # 日志工具

# ==================== 知识图谱检索器类 ====================
class GraphRetriever:
    """知识图谱检索器
    
    从知识图谱中检索与查询相关的实体和关系
    """
    
    def __init__(self, graph_store: GraphStore):
        """初始化知识图谱检索器
        
        参数：
            graph_store: 知识图谱存储实例
        """
        # 保存图谱存储实例
        self.graph_store = graph_store

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """从图谱中检索相关信息（主入口函数）
        
        参数：
            query: 用户查询
            top_k: 返回结果数量（默认5）
            
        返回：
            List[Dict]: 相关的文档列表，每个文档包含文本和元数据
        """
        # 步骤1：在图谱中搜索匹配的实体
        entities = self.graph_store.search_entity(query)
        
        # 如果没有找到匹配的实体，使用查询本身作为实体
        if not entities:
            entities = [query]
        
        # 存储检索结果
        results = []
        
        # 步骤2：遍历前3个实体，获取它们的邻居节点
        for ent in entities[:3]:
            # 获取实体的邻居（相关的实体和关系）
            neighbors = self.graph_store.get_neighbors(ent)
            # 将邻居信息添加到结果列表
            results.extend(neighbors)
        
        # 记录日志（查询和结果数量）
        logger.info("graph_retrieval_done", query=query, results=len(results))
        
        # 返回前 top_k 个结果
        return results[:top_k]
