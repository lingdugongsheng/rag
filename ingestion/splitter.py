# ==================== 文件说明 ====================
# 这是文档分块模块，负责将长文档分割成小块
# 为什么需要分块？
# 1. LLM 有上下文长度限制（如 4096 token）
# 2. 短文档更容易匹配到相关内容
# 3. 分块时保留上下文重叠，保证信息完整

# ==================== 导入依赖 ====================
from typing import List  # 类型提示
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 递归字符分块器
from langchain_core.documents import Document  # LangChain 的文档类型
from core.logger import logger  # 日志工具

# ==================== 文档分块函数 ====================
def split_documents(documents: List[Document], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Document]:
    """将文档分割成小块
    
    使用递归字符分块器，按照中文标点和换行符进行分割
    保留重叠部分，确保上下文连贯
    
    参数：
        documents: 原始文档列表
        chunk_size: 每个块的最大字符数（默认500）
        chunk_overlap: 块之间的重叠字符数（默认50）
        
    返回：
        List[Document]: 分割后的文档块列表
    """
    # 创建递归字符分块器
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,          # 每个块的最大字符数
        chunk_overlap=chunk_overlap,    # 块之间的重叠字符数
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]  # 分割优先级
        # 分割优先级说明：
        # 1. 优先按空行（段落）分割
        # 2. 然后按换行符分割
        # 3. 然后按中文句号、感叹号、问号、分号、逗号分割
        # 4. 最后按空格分割
        # 5. 如果以上都没有，按字符直接分割
    )
    
    # 调用分块器分割文档
    chunks = text_splitter.split_documents(documents)
    
    # 记录日志（输入文档数和输出块数）
    logger.info("documents_split", input_count=len(documents), output_chunks=len(chunks))
    
    # 返回分割后的文档块列表
    return chunks
