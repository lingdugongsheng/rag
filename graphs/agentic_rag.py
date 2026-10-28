# ==================== 文件说明 ====================
# 这是 Agentic RAG 智能体的核心编排文件
# 使用 LangGraph 构建智能体流程图，定义各个节点和节点之间的连接关系
#
# 本版关键变化（相对上一版）：
# 1. 【P0-1】删除 plan -> tools 的普通边，只保留条件边。
#    同时挂普通边和条件边会让图语义冲突（Already found path），
#    且缓存命中时普通边仍可能把流程推向 tools。
# 2. 条件边统一处理：from_cache -> END，否则 -> tools。

# ==================== 导入依赖 ====================
from langgraph.graph import StateGraph, END
from graphs.states import AgentState
from graphs.nodes import GraphNodes

# ==================== AgenticRAG 类 ====================
class AgenticRAG:
    """Agentic RAG 智能体：使用 LangGraph 编排的自主决策问答系统"""

    def __init__(self, searcher, graph_retriever, llm, plan_llm, cache, generator, reranker, rewriter):
        self.nodes = GraphNodes(
            searcher=searcher,
            graph_retriever=graph_retriever,
            llm=llm,
            plan_llm=plan_llm,
            cache=cache,
            generator=generator,
            reranker=reranker,
            rewriter=rewriter,
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        """构建智能体流程图

        注意：plan 节点只有条件边，没有普通边。
        同时挂 add_edge 和 add_conditional_edges 会让图语义冲突，
        且缓存命中时普通边仍可能把流程推向 tools。
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("plan", self.nodes.plan_node)
        workflow.add_node("tools", self.nodes.tool_execution_node)
        workflow.add_node("prepare_docs", self.nodes.prepare_documents_node)
        workflow.add_node("generate", self.nodes.generate_answer_node)
        workflow.add_node("reflection", self.nodes.reflection_node)

        workflow.set_entry_point("plan")

        # plan 的唯一出边是条件边：缓存命中 -> END，否则 -> tools
        workflow.add_conditional_edges(
            "plan",
            lambda s: "end" if s.get("from_cache") else "tools",
            {"end": END, "tools": "tools"}
        )

        workflow.add_edge("tools", "prepare_docs")
        workflow.add_edge("prepare_docs", "generate")
        workflow.add_edge("generate", "reflection")

        workflow.add_conditional_edges(
            "reflection",
            lambda s: "plan" if s.get("need_retry") else "end",
            {"plan": "plan", "end": END}
        )

        return workflow.compile()