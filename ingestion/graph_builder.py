# ==================== 文件说明 ====================
# 这是知识图谱构建模块，负责从文本中提取三元组（实体-关系-实体）
# 流程：
# 1. 使用 LLM 从文本中抽取三元组
# 2. 对实体进行规范化（合并相似实体）
# 3. 返回去重后的三元组列表

# ==================== 导入依赖 ====================
import json  # JSON 解析
import difflib  # 字符串相似度比较
import time  # 重试时的延迟
from typing import List, Tuple, Set  # 类型提示
from concurrent.futures import ThreadPoolExecutor, as_completed  # 多线程并行处理
from core.llm import get_llm_singleton  # 获取 LLM 单例
from core.logger import logger  # 日志工具

# ==================== 内部函数：抽取三元组 ====================
def _extract_from_text(text: str) -> List[Tuple[str, str, str]]:
    """从文本中提取三元组
    
    调用 LLM，让它从文本中识别实体和关系，返回 JSON 格式的三元组列表
    
    参数：
        text: 输入文本
        
    返回：
        List[Tuple[str, str, str]]: 三元组列表，每个三元组是 (主体, 关系, 客体)
    """
    # 获取 LLM 单例（避免重复创建）
    llm = get_llm_singleton()
    
    # 构建提示词：告诉 LLM 如何提取三元组
    prompt = f"""从以下文本中抽取所有重要的实体和关系，以 JSON 数组格式输出。
每个元素为 {{"subject": "主体", "relation": "关系", "object": "客体"}}。
关系要具体明确，如"作者"、"位于"、"属于"、"发明"、"成立于"等。
只输出 JSON 数组，不要其他内容。

文本：{text}"""
    
    # 设置重试次数（网络不稳定时重试）
    max_retries = 2
    
    # 循环尝试提取
    for attempt in range(max_retries + 1):
        try:
            # 调用 LLM 生成结果
            resp = llm.invoke(prompt)
            
            # 提取响应内容（兼容不同格式的返回值）
            content = resp.content if hasattr(resp, "content") else str(resp)
            
            # 查找 JSON 数组的起始和结束位置
            start = content.find('[')  # 找 '[' 的位置
            end = content.rfind(']') + 1  # 找最后一个 ']' 的位置，并加1
            
            # 如果没找到 JSON 数组，抛出异常
            if start == -1 or end == 0:
                raise ValueError("No JSON array found")
            
            # 解析 JSON 数组
            triplets = json.loads(content[start:end])
            
            # 转换为三元组列表（过滤掉不完整的）
            return [(t["subject"], t["relation"], t["object"]) for t in triplets if "subject" in t]
            
        except Exception as e:
            # 如果还有重试机会
            if attempt < max_retries:
                # 记录警告日志
                logger.warning(f"triplet_extraction_retry_{attempt+1}", error=str(e))
                # 等待2秒后重试
                time.sleep(2)
            else:
                # 重试用完了，记录错误日志
                logger.error("triplet_extraction_failed", error=str(e))
                # 返回空列表
                return []

# ==================== 内部函数：实体相似度计算 ====================
def _entity_similarity(a: str, b: str) -> float:
    """计算两个实体的相似度
    
    参数：
        a: 第一个实体
        b: 第二个实体
        
    返回：
        float: 相似度分数（0-1），越接近1越相似
    """
    # 去除首尾空格并转为小写
    a_clean = a.strip().lower()
    b_clean = b.strip().lower()
    
    # 如果完全相同，相似度为1.0
    if a_clean == b_clean:
        return 1.0
    
    # 如果一个是另一个的子串，相似度为0.95
    if a_clean in b_clean or b_clean in a_clean:
        return 0.95
    
    # 使用 difflib 计算编辑距离相似度
    return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()

# ==================== 内部函数：实体规范化 ====================
def _normalize_entities(triplets: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    """规范化实体名称
    
    将相似的实体合并为同一个名称，例如：
    "北京" 和 "北京市" 合并为 "北京市"（取最长的作为标准名）
    
    参数：
        triplets: 原始三元组列表
        
    返回：
        List[Tuple[str, str, str]]: 规范化后的三元组列表
    """
    # 收集所有实体
    entities: Set[str] = set()
    for s, r, o in triplets:
        entities.add(s)  # 添加主体
        entities.add(o)  # 添加客体
    
    # 聚类相似实体
    clusters = []
    for ent in entities:
        found = False
        # 检查是否能加入已有聚类
        for cluster in clusters:
            # 如果相似度大于0.8，加入这个聚类
            if _entity_similarity(ent, cluster[0]) > 0.8:
                cluster.append(ent)
                found = True
                break
        # 如果没找到相似的聚类，新建一个
        if not found:
            clusters.append([ent])
    
    # 创建实体映射（将相似实体映射到标准名）
    entity_map = {}
    for cluster in clusters:
        # 取最长的实体作为标准名（通常更完整）
        canonical = max(cluster, key=len)
        for ent in cluster:
            entity_map[ent] = canonical
    
    # 使用映射替换三元组中的实体
    normalized = []
    for s, r, o in triplets:
        # 替换主体
        new_s = entity_map.get(s, s)
        # 替换客体
        new_o = entity_map.get(o, o)
        # 添加到结果列表
        normalized.append((new_s, r, new_o))
    
    # 记录日志（原始实体数和聚类后的组数）
    logger.info(f"entity_normalization_done, original_unique={len(entities)}, after_clusters={len(clusters)}")
    
    # 返回规范化后的三元组
    return normalized

# ==================== 主函数：提取三元组 ====================
def extract_triplets(chunks: List[str]) -> List[Tuple[str, str, str]]:
    """从文档块中提取三元组（主入口函数）
    
    参数：
        chunks: 文档块列表
        
    返回：
        List[Tuple[str, str, str]]: 去重并规范化后的三元组列表
    """
    # 如果输入为空，直接返回空列表
    if not chunks:
        return []
    
    # 将所有块合并为完整文本
    full_text = " ".join(chunks)
    
    # 如果文本较短（<=2000字符），直接处理
    if len(full_text) <= 2000:
        raw = _extract_from_text(full_text)
    else:
        # 如果文本太长，分段处理
        chunk_texts = []
        current_chunk = ""
        
        # 将文本分成多个小片段（每个约1500字符）
        for text in chunks:
            if len(current_chunk) + len(text) < 1500:
                # 如果加上当前文本不会超过1500，继续累加
                current_chunk += " " + text
            else:
                # 如果超过了，保存当前片段并开始新片段
                if current_chunk:
                    chunk_texts.append(current_chunk)
                current_chunk = text
        
        # 保存最后一个片段
        if current_chunk:
            chunk_texts.append(current_chunk)
        
        # 使用多线程并行提取（最多3个线程）
        raw = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有任务
            futures = {executor.submit(_extract_from_text, ct): ct for ct in chunk_texts}
            
            # 等待所有任务完成
            for future in as_completed(futures, timeout=120):
                try:
                    # 获取结果并合并
                    raw.extend(future.result(timeout=60))
                except Exception:
                    # 单个片段失败不影响整体
                    pass
    
    # 去重（转换为集合再转回列表）
    unique_raw = list(set(raw))
    
    # 记录日志（原始数量和去重后数量）
    logger.info(f"triplets_raw_count={len(raw)}, unique={len(unique_raw)}")
    
    # 对实体进行规范化
    normalized = _normalize_entities(unique_raw)
    
    # 返回最终结果
    return normalized
