# ==================== 文件说明 ====================
# 配置中心，pydantic-settings 从 .env 读取
#
# 本版关键变化：
# 1. max_context_chars -> max_context_tokens：
#    原字段名是"字符"、但 context.py 拿它和 token 数比较，语义混乱。
#    统一为 token 口径，由 context.py 负责估算。
# 2. 内部 class Config 改为 model_config = SettingsConfigDict(...)：
#    pydantic v2 下旧的内部 Config 类已弃用。

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional


class Settings(BaseSettings):
    # -------------------- 硅基流动（Embedding） --------------------
    llm_api_key: SecretStr
    llm_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    # -------------------- 智谱 AI（生成/规划/反思/改写） --------------------
    zhipu_api_key: SecretStr
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4-flash"

    # -------------------- 日志和环境 --------------------
    log_level: str = "INFO"
    environment: str = "dev"

    # -------------------- 检索 --------------------
    retrieval_top_k: int = 10
    rerank_top_k: int = 5
    fusion_k: int = 60

    # -------------------- 文档分块 --------------------
    chunk_size: int = 500
    chunk_overlap: int = 50

    # -------------------- 上下文和缓存 --------------------
    # 上下文预算：单位是 token（由 context.py 估算，tiktoken 缺失时降级为字符近似）
    max_context_tokens: int = 3000
    cache_max_size: int = 1000

    # -------------------- 智能体重试 --------------------
    max_retries: int = 2
    web_search_enabled: bool = True
    tool_retry_attempts: int = 2
    tool_retry_delay: float = 1.0

    # -------------------- LangSmith --------------------
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: Optional[SecretStr] = None
    langsmith_project: str = "rag-system"

    # -------------------- 重排序 --------------------
    rerank_method: str = "embedding_similarity"
    cross_encoder_model: str = "BAAI/bge-reranker-base"

    @property
    def llm_model(self):
        return self.zhipu_model

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()