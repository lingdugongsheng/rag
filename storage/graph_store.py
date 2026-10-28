# ==================== 文件说明 ====================
# 这是知识图谱存储模块，使用 NetworkX 作为底层图结构
# 主要功能：
# 1. 添加三元组（实体-关系-实体）
# 2. 获取实体的邻居节点（相关实体）
# 3. 搜索匹配的实体
# 4. 支持图谱的保存和加载

# ==================== 导入依赖 ====================
import networkx as nx  # 图结构库（有向图）
import os  # 文件系统操作
import json  # JSON 序列化
from typing import List, Dict, Tuple  # 类型提示
from core.logger import logger  # 日志工具

# ==================== 图谱存储类 ====================
class GraphStore:
    """知识图谱存储
    
    使用 NetworkX 有向图存储实体和关系
    支持持久化（JSON 格式）
    """
    
    def __init__(self, persist_path: str = None):
        """初始化图谱存储
        
        参数：
            persist_path: 持久化文件路径（如果提供，会自动加载已有数据）
        """
        # 创建有向图（DiGraph = Directed Graph）
        self.graph = nx.DiGraph()
        # 持久化路径
        self.persist_path = persist_path
        # 实体倒排索引（小写名称 -> 原始节点列表，用于快速搜索）
        self._entity_index = {}

        # 如果提供了持久化路径且文件存在，自动加载
        if persist_path and os.path.exists(persist_path):
            self.load()

    def _update_index(self, entity: str):
        """更新实体索引（内部方法）
        
        将实体添加到倒排索引，支持大小写不敏感搜索
        
        参数：
            entity: 实体名称
        """
        # 将实体名转为小写作为索引键
        key = entity.lower()
        # 如果键不存在，创建空列表；否则追加实体名
        self._entity_index.setdefault(key, []).append(entity)

    def add_triplet(self, subject: str, relation: str, object: str, metadata: Dict = None):
        """添加单个三元组
        
        参数：
            subject: 主体（源实体）
            relation: 关系
            object: 客体（目标实体）
            metadata: 元数据（可选）
        """
        # 如果主体节点不存在，创建节点
        if not self.graph.has_node(subject):
            self.graph.add_node(subject, type="entity")  # 添加节点，类型标记为实体
            self._update_index(subject)  # 更新索引
            
        # 如果客体节点不存在，创建节点
        if not self.graph.has_node(object):
            self.graph.add_node(object, type="entity")
            self._update_index(object)
            
        # 添加边（关系）
        self.graph.add_edge(subject, object, relation=relation, metadata=metadata or {})

    def add_triplets(self, triplets: List[Tuple[str, str, str]]):
        """批量添加三元组
        
        参数：
            triplets: 三元组列表，每个三元组是 (主体, 关系, 客体)
        """
        # 遍历所有三元组，逐个添加
        for sub, rel, obj in triplets:
            self.add_triplet(sub, rel, obj)
        
        # 记录日志（添加的三元组数量）
        logger.info("graph_triplets_added", count=len(triplets))
        
        # 添加后自动保存
        self.save()

    def get_neighbors(self, entity: str, hops: int = 1) -> List[Dict]:
        """获取实体的邻居节点（相关实体）
        
        参数：
            entity: 实体名称
            hops: 跳数（默认1，只获取直接邻居）
            
        返回：
            List[Dict]: 邻居信息列表
        """
        # 如果实体不存在于图中，返回空列表
        if not self.graph.has_node(entity):
            return []
        
        # 存储结果
        results = []
        
        # 获取出边（entity -> 其他实体）
        for _, obj, data in self.graph.out_edges(entity, data=True):
            results.append({
                "text": f"{entity} {data['relation']} {obj}",  # 格式化文本
                "metadata": {"source": "graph", "type": "triplet"}  # 元数据
            })
        
        # 获取入边（其他实体 -> entity）
        for sub, _, data in self.graph.in_edges(entity, data=True):
            results.append({
                "text": f"{sub} {data['relation']} {entity}",
                "metadata": {"source": "graph", "type": "triplet"}
            })
        
        # 返回前10个结果
        return results[:10]

    def search_entity(self, entity: str) -> List[str]:
        """搜索匹配的实体（支持模糊匹配）
        
        参数：
            entity: 搜索关键词
            
        返回：
            List[str]: 匹配的实体名称列表
        """
        # 使用倒排索引加速查找
        key = entity.lower()
        matched = []
        
        # 遍历索引，查找包含关键词的实体
        for idx_key, nodes in self._entity_index.items():
            if key in idx_key:
                matched.extend(nodes)
        
        # 如果没有找到匹配，回退到遍历所有节点（作为后备方案）
        if not matched:
            for node in self.graph.nodes:
                if entity.lower() in node.lower():
                    matched.append(node)
        
        # 去重并限制返回数量（最多5个）
        return list(dict.fromkeys(matched))[:5]

    def count(self) -> int:
        """获取图中的节点数量
        
        返回：
            int: 节点数量
        """
        return self.graph.number_of_nodes()

    def save(self):
        """保存图谱到文件"""
        # 如果没有指定持久化路径，不保存
        if self.persist_path:
            try:
                # 将图转换为 node-link 格式（NetworkX 的标准格式）
                data = nx.node_link_data(self.graph)
                
                # 写入 JSON 文件
                with open(self.persist_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                
                # 记录日志
                logger.info("graph_saved", path=self.persist_path)
            except Exception as e:
                # 如果保存失败，记录错误日志
                logger.error("graph_save_failed", error=str(e))

    def load(self):
        """从文件加载图谱"""
        # 如果指定了路径且文件存在
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                # 读取 JSON 文件
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 从 node-link 格式恢复图
                self.graph = nx.node_link_graph(data)
                
                # 重建倒排索引
                self._entity_index.clear()
                for node in self.graph.nodes:
                    self._update_index(node)
                
                # 记录日志
                logger.info("graph_loaded", nodes=self.graph.number_of_nodes())
            except Exception as e:
                # 如果加载失败，记录错误日志并创建空图
                logger.error("graph_load_failed", error=str(e))
                self.graph = nx.DiGraph()
