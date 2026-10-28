# ==================== 文件说明 ====================
# 上下文构建：把检索到的文档拼成 LLM 可用的上下文 + 引用映射
#
# 本版关键变化：
# 1. token 口径统一：阈值来自 settings.max_context_tokens，
#    _num_tokens_from_string 返回的也是 token 估算值。
# 2. tiktoken 缺失时降级为字符近似（中文场景 1 字 ≈ 1 token 左右），
#    只告警一次，避免每个请求刷日志。
# 3. 编码器缓存到模块级，不再每次调用都 get_encoding。

from typing import List, Dict, Tuple
from core.config import settings
from core.logger import logger

_TOKEN_ENCODER = None
_DEGRADED_LOGGED = False


def _num_tokens_from_string(string: str) -> int:
    """估算字符串 token 数。

    tiktoken 可用：用 cl100k_base 精确编码（对 GLM 是近似，但量级正确）。
    tiktoken 不可用：退化为字符数，只告警一次。
    """
    global _TOKEN_ENCODER, _DEGRADED_LOGGED
    try:
        if _TOKEN_ENCODER is None:
            import tiktoken
            _TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
        return len(_TOKEN_ENCODER.encode(string))
    except ImportError:
        if not _DEGRADED_LOGGED:
            logger.warning("tiktoken_not_available_fallback_to_char_count")
            _DEGRADED_LOGGED = True
        return len(string)


def build_context(
    documents: List[Dict],
    max_tokens: int = None,
) -> Tuple[str, Dict[int, Dict]]:
    """构建上下文文本和引用映射。

    参数：
        documents: 检索结果，每项至少含 text，可选 metadata
        max_tokens: token 预算；None 时用 settings.max_context_tokens

    返回：
        (上下文文本, 引用映射 {编号: {text, source, page}})
    """
    max_tokens = max_tokens or settings.max_context_tokens

    if not documents:
        return "暂无相关背景知识。", {}

    context_parts = []
    citation_map = {}
    current_tokens = 0

    for i, doc in enumerate(documents):
        text = doc.get("text", "")
        addition = f"[{i+1}] {text}\n\n"
        addition_tokens = _num_tokens_from_string(addition)

        # 至少放一条，避免第一条就超预算导致上下文为空
        if context_parts and current_tokens + addition_tokens > max_tokens:
            break
        if not context_parts and addition_tokens > max_tokens:
            # 单条就超预算：截断文本，保留编号和来源
            overflow = addition_tokens - max_tokens
            keep_chars = max(0, len(text) - overflow)
            addition = f"[{i+1}] {text[:keep_chars]}\n\n"
            addition_tokens = _num_tokens_from_string(addition)

        context_parts.append(addition)
        current_tokens += addition_tokens

        meta = doc.get("metadata") or {}
        citation_map[i + 1] = {
            "text": text,
            "source": meta.get("source", ""),
            "page": meta.get("page", ""),
        }

    context_text = "".join(context_parts).strip()
    return context_text, citation_map