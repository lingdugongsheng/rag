# ==================== 文件说明 ====================
# 这是文档加载模块，负责加载不同格式的文档
# 支持的格式：PDF、TXT、MD、DOCX
# 使用 LangChain 的文档加载器来解析文件内容

# ==================== 导入依赖 ====================
from pathlib import Path  # 文件路径处理
from typing import List  # 类型提示
from langchain_core.documents import Document  # LangChain 的文档类型
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader  # 文档加载器
from core.logger import logger  # 日志工具

# ==================== 常量定义 ====================
# 支持的文件扩展名集合
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".docx"}

# ==================== 文档加载函数 ====================
def load_document(file_path: str) -> List[Document]:
    """加载文档文件
    
    根据文件扩展名选择合适的加载器，读取文件内容并返回文档列表
    
    参数：
        file_path: 文件的绝对路径
        
    返回：
        List[Document]: 文档列表，每个 Document 包含 page_content（内容）和 metadata（元数据）
        
    抛出：
        ValueError: 如果文件格式不支持
    """
    # 获取文件扩展名（转为小写）
    suffix = Path(file_path).suffix.lower()
    
    # 检查文件格式是否支持
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"不支持的文件格式：{suffix}，目前支持 {SUPPORTED_SUFFIXES}")

    # 根据扩展名选择对应的加载器
    if suffix == ".pdf":
        # PDF 文件使用 PyPDFLoader
        loader = PyPDFLoader(file_path)
    elif suffix == ".docx":
        # DOCX 文件使用 Docx2txtLoader
        loader = Docx2txtLoader(file_path)
    else:
        # TXT 和 MD 文件使用 TextLoader
        loader = TextLoader(file_path, encoding="utf-8")

    # 调用加载器加载文档
    docs = loader.load()
    
    # 记录日志（加载的页数或段落数）
    logger.info("document_loaded", file_path=file_path, pages_or_sections=len(docs))
    
    # 返回文档列表
    return docs
