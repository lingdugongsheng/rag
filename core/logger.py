# ==================== 文件说明 ====================
# 这是日志模块，使用 structlog 实现结构化日志
# 结构化日志的好处：便于日志分析、过滤和追踪
# 根据环境自动切换不同的日志输出格式（开发环境：人类可读；生产环境：JSON）

# ==================== 导入依赖 ====================
import logging  # Python 标准日志库
import structlog  # 结构化日志库
from core.config import settings  # 配置中心

# ==================== 日志配置函数 ====================
def setup_logger():
    """配置日志系统
    
    日志处理器链：
    1. add_log_level: 添加日志级别（DEBUG/INFO/WARNING/ERROR）
    2. TimeStamper: 添加时间戳
    3. PositionalArgumentsFormatter: 处理位置参数
    4. StackInfoRenderer: 当有异常时添加堆栈信息
    5. format_exc_info: 格式化异常信息
    6. renderer: 根据环境选择输出格式
    
    开发环境（dev）：使用 ConsoleRenderer（彩色、人类可读）
    生产环境（production）：使用 JSONRenderer（便于日志系统解析）
    """
    # 根据环境选择渲染器
    if settings.environment == "production":
        # 生产环境：输出 JSON 格式，便于日志收集和分析
        renderer = structlog.processors.JSONRenderer()
    else:
        # 开发环境：输出彩色文本，便于调试
        renderer = structlog.dev.ConsoleRenderer()

    # 配置 structlog
    structlog.configure(
        processors=[
            # 处理器链：按顺序执行
            structlog.stdlib.add_log_level,  # 添加日志级别字段
            structlog.processors.TimeStamper(fmt="iso", utc=False),  # 添加时间戳（本地时区）
            structlog.stdlib.PositionalArgumentsFormatter(),  # 处理位置参数
            structlog.processors.StackInfoRenderer(),  # 添加堆栈信息
            structlog.processors.format_exc_info,  # 格式化异常信息
            renderer,  # 最终输出格式化
        ],
        wrapper_class=structlog.stdlib.BoundLogger,  # 包装类
        context_class=dict,  # 上下文数据结构
        logger_factory=structlog.stdlib.LoggerFactory(),  # 日志工厂
        cache_logger_on_first_use=True,  # 第一次使用后缓存日志器（提高性能）
    )
    
    # 配置 Python 标准日志库
    # 设置日志格式和级别
    logging.basicConfig(format="%(message)s", level=settings.log_level)

# ==================== 初始化日志系统 ====================
# 调用配置函数
setup_logger()

# 创建全局日志实例
# 其他模块通过 `from core.logger import logger` 使用
logger = structlog.get_logger()
