# ==================== 文件说明 ====================
# 这是智能体图的节点实现文件
# 每个节点都是一个 async 函数，接收状态并返回新状态
#
# 本版关键变化（相对上一版）：
# 1. 【P0-3】generate_answer_node 改为接收 messages 列表（SystemMessage + HumanMessage），
#    不再把 system 约束拼成一条 str 传给 ChatOpenAI。
#    原实现下 LangChain 会把整段 str 包成一条 HumanMessage，
#    导致 Prompt 注入防护和引用规则降级为用户消息。
# 2. 缓存写入仍在 reflection_node，generate 不写缓存，避免重试命中旧答案。

# ==================== 导入依赖 ====================
import asyncio
import json
import re
from typing import Dict, Any, List

from core.config import settings
from core.logger import logger

# ==================== 常量 ====================
TOOL_TIMEOUT_SECONDS = 15  # 单个工具调用超时（串行/并行共用）

# ==================== GraphNodes 类 ====================
class GraphNodes:
    """图节点实现类：封装智能体的所有节点逻辑

    两个 LLM：
    - self.llm：流式 LLM，用于生成节点
    - self.plan_llm：非流式 LLM，由 main.py 注入，用于规划/反思（和 QueryRewriter 共用）
    """

    def __init__(self, searcher, graph_retriever, llm, plan_llm, cache, generator, reranker, rewriter):
        self.searcher = searcher
        self.graph_retriever = graph_retriever
        self.llm = llm
        self.plan_llm = plan_llm
        self.cache = cache
        self.generator = generator
        self.reranker = reranker
        self.rewriter = rewriter

    # -------------------- 辅助方法 --------------------

    @staticmethod
    def _make_cache_key(query: str, history: List) -> str:
        """生成缓存键（查询 + 最近 6 条历史）"""
        try:
            return json.dumps(
                {"query": query, "history": history[-6:]},
                ensure_ascii=False,
                sort_keys=True,
            )
        except Exception:
            return query

    async def _execute_with_retry(self, func, max_attempts=None):
        """带重试的异步执行（func 为无参同步可调用对象）"""
        attempts = max_attempts or settings.tool_retry_attempts
        last_exception = None

        for attempt in range(attempts + 1):
            try:
                return await asyncio.to_thread(func)
            except Exception as e:
                last_exception = e
                if attempt < attempts:
                    logger.warning(f"tool_retry_{attempt+1}", error=str(e))
                    await asyncio.sleep(settings.tool_retry_delay)
                else:
                    logger.error("tool_all_retries_failed", error=str(e))
                    raise last_exception

    async def _single_local_search(self, query: str) -> List[Dict]:
        attempts = settings.tool_retry_attempts
        for attempt in range(attempts + 1):
            try:
                return await self.searcher.search(query, top_k=settings.retrieval_top_k)
            except Exception as e:
                if attempt < attempts:
                    logger.warning(f"local_search_retry_{attempt+1}", error=str(e))
                    await asyncio.sleep(settings.tool_retry_delay)
                else:
                    logger.error("local_search_all_retries_failed", error=str(e))
                    return []
        return []

    async def _single_web_search(self, query: str) -> List[Dict]:
        if not settings.web_search_enabled:
            return []
        try:
            from retrieval.web_search import search_web
            return await self._execute_with_retry(
                lambda: search_web(query, max_results=3)
            )
        except Exception:
            return []

    async def _single_graph_search(self, query: str) -> List[Dict]:
        if not self.graph_retriever:
            return []
        try:
            return await self._execute_with_retry(
                lambda: self.graph_retriever.search(query, top_k=settings.retrieval_top_k)
            )
        except Exception:
            return []

    def _extract_json_from_text(self, text: str) -> dict:
        try:
            return json.loads(text)
        except Exception:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return {}

    # -------------------- 图节点实现 --------------------

    async def plan_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """规划节点：先查缓存（除非 skip_cache），再改写 query，最后生成工具调用计划"""
        query = state["query"]
        history = state.get("chat_history", [])
        skip_cache = state.get("skip_cache", False)

        cache_key = self._make_cache_key(query, history)

        # skip_cache=True 表示上一轮反思判定需要重试，必须跳过缓存，
        # 否则会命中上一轮刚写入的旧答案，重试形同虚设。
        if not skip_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info("[plan_node] cache hit")
                # 缓存 value 现在是 {answer, citation_map}，命中时一起恢复，
                # 保证缓存路径也能返回引用来源。
                if isinstance(cached, dict):
                    return {
                        "answer": cached.get("answer", ""),
                        "citation_map": cached.get("citation_map", {}),
                        "from_cache": True,
                        "plan": [],
                        "tool_results": {},
                        "skip_cache": False,
                    }
                # 兼容旧格式（纯字符串）
                return {
                    "answer": cached,
                    "citation_map": {},
                    "from_cache": True,
                    "plan": [],
                    "tool_results": {},
                    "skip_cache": False,
                }

        rewritten = await self.rewriter.rewrite(query)

        tools_desc = """
- local_search: 搜索本地知识库（适合常规问题）
- web_search: 互联网搜索（适合实时信息或本地无结果时）
- graph_search: 知识图谱查询（适合询问实体关系，如"谁发明了..."）
"""

        prompt = f"""你是一个智能计划助手。根据用户问题，制定检索计划。
可用工具：{tools_desc}

用户原问题：{query}
参考检索查询（由改写模块生成，可作为 step 里的 query）：{rewritten}

输出 JSON 格式：
{{"plan": [{{"tool": "工具名", "query": "搜索用查询", "reason": "理由"}}], "parallel": true/false}}
注意：只输出 JSON，不要包含解释。如果无法确定，默认使用 local_search。
JSON:"""

        try:
            resp = await self.plan_llm.ainvoke(prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            plan_data = self._extract_json_from_text(content)
            if not plan_data.get("plan"):
                raise ValueError("No plan")
        except Exception as e:
            logger.warning("[plan_node] plan extraction failed, using default", error=str(e))
            plan_data = {
                "plan": [{"tool": "local_search", "query": rewritten, "reason": "默认"}],
                "parallel": False
            }

        logger.info("[plan_node] plan generated", tools=[s["tool"] for s in plan_data.get("plan", [])])

        return {
            "plan": plan_data.get("plan", []),
            "parallel": plan_data.get("parallel", False),
            "step_index": 0,
            "tool_results": {},
            "rewritten_query": rewritten,
            # 正常检索分支重置 skip_cache，避免标志残留影响后续轮次
            "skip_cache": False,
        }

    async def tool_execution_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """工具执行节点：串行或并行执行计划中的工具

        每个工具调用都有独立超时（TOOL_TIMEOUT_SECONDS），
        超时或异常只影响该工具，返回空结果，不中断整个请求。
        """
        plan = state.get("plan", [])
        parallel = state.get("parallel", False)
        tool_results = state.get("tool_results", {})
        fallback_query = state.get("rewritten_query") or state["query"]

        if not plan:
            docs = await self._single_local_search(fallback_query)
            tool_results["local_search"] = docs
            return {"tool_results": tool_results}

        async def run_tool(tool: str, query: str):
            if tool == "local_search":
                return tool, await self._single_local_search(query)
            elif tool == "web_search":
                return tool, await self._single_web_search(query)
            elif tool == "graph_search":
                return tool, await self._single_graph_search(query)
            return tool, []

        async def run_tool_with_timeout(tool: str, query: str):
            """单工具超时 + 异常兜底：失败只返回空列表，不冒泡"""
            try:
                return await asyncio.wait_for(
                    run_tool(tool, query),
                    timeout=TOOL_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "[tool_execution] tool timeout",
                    tool=tool,
                    timeout=TOOL_TIMEOUT_SECONDS,
                )
                return tool, []
            except Exception as e:
                logger.error("[tool_execution] tool failed", tool=tool, error=str(e))
                return tool, []

        if parallel:
            tasks = [
                run_tool_with_timeout(step["tool"], step.get("query") or fallback_query)
                for step in plan
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for item in results:
                if isinstance(item, Exception):
                    logger.error("[tool_execution] tool failed", error=str(item))
                    continue
                tool, docs = item
                tool_results[tool] = docs
        else:
            for step in plan:
                tool, docs = await run_tool_with_timeout(
                    step["tool"], step.get("query") or fallback_query
                )
                tool_results[tool] = docs

        logger.info(
            "[tool_execution] results",
            tools=list(tool_results.keys()),
            counts={k: len(v) for k, v in tool_results.items()},
        )

        return {"tool_results": tool_results, "step_index": len(plan)}

    async def prepare_documents_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """文档准备节点：收集并重排序"""
        tool_results = state.get("tool_results", {})

        all_docs = []
        for docs in tool_results.values():
            all_docs.extend(docs)

        logger.info("[prepare_docs] total docs", count=len(all_docs))

        if not all_docs:
            return {"final_documents": []}

        query = state["query"]
        ranked = await asyncio.to_thread(
            self.reranker.rerank, query, all_docs, settings.rerank_top_k
        )

        return {"final_documents": ranked}

    async def generate_answer_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成回答节点（异步流式版）

        本版变化：
        1. 【P0-3】generator.build_prompt 现在返回 messages 列表，
           system 约束与用户内容分离，不再把整段 str 传进 ChatOpenAI。
           原来 str 会被 LangChain 包成一条 HumanMessage，注入防护失效。
        2. 仍不写缓存（缓存写入由 reflection_node 在"质量通过"后完成），
           避免反思重试回到 plan 时命中自己刚写入的旧答案。
        """
        if state.get("from_cache"):
            return {}

        query = state["query"]
        docs = state.get("final_documents", [])
        history = state.get("chat_history", [])

        history_text = ""
        if history:
            history_text = "对话历史：\n" + "\n".join(
                [f"{role}: {content}" for role, content in history[-6:]]
            ) + "\n"

        # [改动] build_prompt 返回 (messages, context_text, citation_map)
        messages, _context_text, citation_map = self.generator.build_prompt(
            query, docs, history_text
        )

        logger.info("[generate_answer] starting", query=query, docs_count=len(docs))

        answer = ""
        try:
            # [改动] astream 接收 messages 列表，而不是拼接后的 prompt 字符串
            async for chunk in self.llm.astream(messages):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    answer += token
        except Exception as e:
            logger.error("llm_astream_failed", error=str(e))
            answer = "抱歉，生成回答时出现错误，请稍后重试。"

        answer = self.generator.sanitize_citations(answer, citation_map)

        return {
            "answer": answer,
            "citation_map": citation_map,
        }

    async def reflection_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """反思节点：评估回答质量，决定是否重试；通过后写缓存

        缓存写入点从 generate 移到这里：
        - 非流式：判定 ok 才写缓存；retry 时显式清空中间产物并置 skip_cache
        - 流式：跳过重试，直接写缓存（用户已看到 token，重试会拼接两段答案）
        """
        query = state["query"]
        answer = state.get("answer", "")
        citation_map = state.get("citation_map", {})
        history = state.get("chat_history", [])
        retry_count = state.get("retry_count", 0)

        # 流式场景：不做重试，但要把本次结果写进缓存
        if state.get("streaming"):
            if answer:
                cache_key = self._make_cache_key(query, history)
                self.cache.set(cache_key, {
                    "answer": answer,
                    "citation_map": citation_map,
                })
            return {"need_retry": False}

        if retry_count >= settings.max_retries:
            # 达到重试上限，接受当前答案并写缓存
            if answer:
                cache_key = self._make_cache_key(query, history)
                self.cache.set(cache_key, {
                    "answer": answer,
                    "citation_map": citation_map,
                })
            return {"need_retry": False}

        # 快速路径：答案没有含糊词，直接通过
        if not any(w in answer for w in ['抱歉', '无法', '不确定', '可能', '或许']):
            logger.info("[reflection] answer looks good")
            if answer:
                cache_key = self._make_cache_key(query, history)
                self.cache.set(cache_key, {
                    "answer": answer,
                    "citation_map": citation_map,
                })
            return {"need_retry": False}

        prompt = f"""评估回答是否充分。如果答案含糊、缺乏具体信息，请输出 "retry"。
否则输出 "ok"。
问题：{query}
回答：{answer}
只输出 retry 或 ok："""

        try:
            resp = await self.plan_llm.ainvoke(prompt)
            verdict = resp.content.strip().lower()
        except Exception as e:
            logger.error("[reflection] LLM call failed", error=str(e))
            verdict = "ok"

        if verdict == "retry":
            logger.info("[reflection] need retry")
            return {
                "need_retry": True,
                "retry_count": retry_count + 1,
                "plan": [],
                "tool_results": {},
                # 显式清空上一轮产物，保证状态机语义干净
                "answer": "",
                "citation_map": {},
                "final_documents": [],
                # 关键：告诉 plan_node 本轮不要查缓存
                "skip_cache": True,
            }

        # 质量通过，写缓存
        if answer:
            cache_key = self._make_cache_key(query, history)
            self.cache.set(cache_key, {
                "answer": answer,
                "citation_map": citation_map,
            })

        return {"need_retry": False}