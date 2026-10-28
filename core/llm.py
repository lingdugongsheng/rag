# ==================== 文件说明 ====================
# 这是 LLM（大语言模型）和 Embedding（嵌入模型）的工厂文件
# 使用单例模式创建模型实例，确保整个应用中只有一个实例，节省资源
# 所有需要使用模型的地方都通过这里获取实例

# ==================== 导入依赖 ====================
from functools import lru_cache  # 装饰器：实现缓存（让函数只执行一次）
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # LangChain 的 OpenAI 兼容接口
from core.config import settings  # 配置中心

# ==================== 大语言模型（LLM）工厂 ====================
@lru_cache()  # 缓存装饰器：第一次调用后缓存结果，后续调用直接返回缓存
def get_llm_singleton():
    """获取大语言模型的单例实例
    
    单例模式的好处：
    1. 节省资源：模型初始化很耗时耗内存，只创建一次
    2. 保持一致性：所有地方使用同一个模型实例
    3. 线程安全：lru_cache 自带线程安全
    
    返回：
        ChatOpenAI: 大语言模型实例，用于生成回答、规划、反思等
    """
    return ChatOpenAI(
        model=settings.zhipu_model,  # 使用智谱模型
        api_key=settings.zhipu_api_key.get_secret_value(),  # 安全获取 API 密钥
        base_url=settings.zhipu_base_url,  # 智谱 API 地址
        temperature=0.1,  # 温度：控制输出随机性，0.1 表示非常确定性
        streaming=True,  # 启用流式输出（用于实时返回回答）
        request_timeout=180,  # 请求超时时间（秒）
        max_retries=2,  # 失败重试次数
    )

# ==================== 嵌入模型（Embedding）工厂 ====================
@lru_cache()  # 缓存装饰器：确保只创建一个实例
def get_embeddings_singleton():
    """获取嵌入模型的单例实例
    
    嵌入模型的作用：
    1. 将文本转换为向量（数字列表）
    2. 向量可以用来计算文本之间的相似度
    3. 用于向量数据库的检索
    
    返回：
        OpenAIEmbeddings: 嵌入模型实例
    """
    return OpenAIEmbeddings(
        model=settings.embedding_model,  # 使用指定的嵌入模型
        api_key=settings.llm_api_key.get_secret_value(),  # 硅基流动 API 密钥
        base_url=settings.llm_base_url,  # 硅基流动 API 地址
        request_timeout=60,  # 请求超时时间（秒）
        max_retries=2,  # 失败重试次数
    )
