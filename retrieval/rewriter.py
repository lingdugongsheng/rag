# ==================== 文件说明 ====================
# 这是查询重写模块，负责优化用户的查询语句
# 查询重写的作用：
# 1. 将简短的问题扩展为更完整的搜索查询
# 2. 补充关键词，提高检索准确性
# 3. 只对短查询进行重写，长查询保持原样
#
# 本版关键变化：
# 1. rewrite 改为 async def，用 ainvoke 调用 LLM
# 2. 传入的 LLM 应为非流式实例（由 main.py 的 query_llm 提供），
#    避免在 /chat/stream 中污染 on_chat_model_stream 事件
# 3. 异常时返回原始 query，绝不因改写失败中断主流程

# ==================== 导入依赖 ====================
from core.logger import logger

# ==================== 查询重写器类 ====================
class QueryRewriter:
    """查询重写器

    使用 LLM 将简短查询扩展为更精准的搜索查询
    """

    def __init__(self, llm):
        self.llm = llm

    async def rewrite(self, query: str) -> str:
        """重写查询（异步）

        参数：
            query: 用户原始查询

        返回：
            str: 重写后的查询（或原始查询，如果不需要重写）
        """
        # 短查询才改写；长查询或已经完整的问题直接返回
        if len(query) > 20 or any(kw in query for kw in ['是什么', '如何', '怎么办', '定义', '区别']):
            logger.info("skip_rewrite", query=query)
            return query

        prompt = (
            "把下面的问题改写成更精准的搜索查询，只输出改写后的句子。\n"
            f"问题：{query}\n"
        )

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            result = content.strip().split('\n')[0]

            if result:
                logger.info("query_rewritten", original=query, rewritten=result)
                return result
        except Exception as e:
            logger.error("query_rewrite_failed", error=str(e))

        return query