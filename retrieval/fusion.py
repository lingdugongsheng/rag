# ==================== 文件说明 ====================
# 这是结果融合模块，实现 RRF（Reciprocal Rank Fusion）算法
# RRF 算法的核心思想：
# - 一个文档在多个检索结果中排名越靠前，融合后的分数越高
# - 公式：score = 1 / (k + rank)，其中 k 是常数（通常取60）
# - 最终分数是各检索方式分数的总和
#
# 优点：
# 1. 不需要归一化，不同检索方式的分数可以直接相加
# 2. 简单高效，计算复杂度低
# 3. 对异常值不敏感

# ==================== 导入依赖 ====================
from typing import List, Dict  # 类型提示

# ==================== RRF 融合函数 ====================
def rrf_fusion(list_a: List[Dict], list_b: List[Dict], k: int = 60, id_field: str = "text", top_k: int = 10) -> List[Dict]:
    """使用 RRF（倒数排序融合）算法合并两个检索结果列表
    
    参数：
        list_a: 第一个检索结果列表
        list_b: 第二个检索结果列表
        k: RRF 算法的常数（默认60），k 越大，排名差异的影响越小
        id_field: 文档唯一标识字段（默认"text"）
        top_k: 返回结果数量（默认10）
        
    返回：
        List[Dict]: 融合后的文档列表，按 RRF 分数降序排列
    """
    # 存储每个文档的 RRF 分数
    rrf_scores: Dict[str, float] = {}
    # 存储文档的完整信息（用于最终输出）
    doc_map: Dict[str, Dict] = {}

    # 步骤1：构建文档映射（合并两个列表中的文档）
    # 遍历两个列表的所有文档
    for item in list_a + list_b:
        # 获取文档的唯一标识（优先使用指定字段，默认用 text）
        doc_id = item.get(id_field) or item.get("text")
        # 如果这个文档还没记录过
        if doc_id not in doc_map:
            # 保存文档的完整信息
            doc_map[doc_id] = item

    # 步骤2：计算 list_a 中每个文档的 RRF 分数
    # enumerate 会返回 (排名, 文档)，排名从0开始
    for rank, item in enumerate(list_a):
        # 获取文档唯一标识
        doc_id = item.get(id_field) or item.get("text")
        # RRF 公式：1 / (k + rank + 1)
        # rank + 1 是因为排名从0开始，但公式中排名应该从1开始
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

    # 步骤3：计算 list_b 中每个文档的 RRF 分数（累加到已有分数）
    for rank, item in enumerate(list_b):
        doc_id = item.get(id_field) or item.get("text")
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1.0 / (k + rank + 1)

    # 步骤4：按 RRF 分数降序排序
    # sorted 的 key 参数指定排序依据，reverse=True 表示降序
    sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # 步骤5：构建最终结果列表
    fused = []
    # 取前 top_k 个结果
    for doc_id, score in sorted_ids[:top_k]:
        # 复制文档信息（避免修改原数据）
        item = doc_map[doc_id].copy()
        # 添加 RRF 分数字段
        item["rrf_score"] = score
        # 添加到结果列表
        fused.append(item)

    # 返回融合后的结果
    return fused
