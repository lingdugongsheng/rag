# ==================== 文件说明 ====================
# 这是网页搜索模块，负责使用 DuckDuckGo 进行网页搜索
# 使用场景：
# 1. 知识库中没有相关信息时
# 2. 需要获取最新信息时
# 3. 需要扩展搜索范围时

# ==================== 导入依赖 ====================
from typing import List, Dict  # 类型提示
from ddgs import DDGS  # DuckDuckGo 搜索 API
from core.logger import logger  # 日志工具

# ==================== 网页搜索函数 ====================
def search_web(query: str, max_results: int = 3) -> List[Dict]:
    """使用 DuckDuckGo 进行网页搜索
    
    参数：
        query: 搜索查询
        max_results: 最大返回结果数（默认3）
        
    返回：
        List[Dict]: 搜索结果列表，每个元素包含文本和元数据
    """
    # 创建 DuckDuckGo 搜索客户端
    with DDGS() as ddgs:
        # 执行文本搜索，获取结果列表
        results = list(ddgs.text(query, max_results=max_results))
        
        # 格式化搜索结果
        docs = []
        for r in results:
            # 构建文档字典
            docs.append({
                "text": r.get("body", ""),  # 搜索结果的摘要文本
                "metadata": {
                    "source": r.get("href", ""),  # 来源链接
                    "title": r.get("title", "")   # 网页标题
                }
            })
        
        # 记录日志（查询和结果数量）
        logger.info("web_search_done", query=query, results=len(docs))
        
        # 返回格式化后的结果
        return docs
