# src/tools/rag.py
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import Tool
from src.config import Config

# 設定向量資料庫路徑 (會在專案根目錄產生 chroma_db 資料夾)
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

# 1. 初始化 Embedding 模型
embeddings = GoogleGenerativeAIEmbeddings(
    model=Config.MODEL_EMBEDDING,
    google_api_key=Config.GOOGLE_API_KEY
)

# 2. 初始化 Vector Store
vector_store = Chroma(
    collection_name="smart_deck_docs",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY
)

def ingest_file(file_path: str):
    """讀取檔案並存入向量庫"""
    if not os.path.exists(file_path):
        return f"❌ 錯誤：找不到檔案 {file_path}"
    
    try:
        # 判斷格式
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.lower().endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            return "❌ 目前只支援 PDF 與 TXT"

        docs = loader.load()
        
        # 切割文字
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        
        if splits:
            vector_store.add_documents(documents=splits)
            return f"✅ 成功：已將 {os.path.basename(file_path)} ({len(splits)} 片段) 存入知識庫。"
        else:
            return "⚠️ 檔案內容為空。"
            
    except Exception as e:
        return f"❌ 讀取失敗：{str(e)}"

def query_knowledge_base(query: str):
    """搜尋知識庫 (RAG 核心)"""
    try:
        # 找最相關的 4 個片段
        results = vector_store.similarity_search(query, k=4)
        if not results:
            return "知識庫中找不到相關資訊。"
        return "\n\n".join([f"---片段---\n{doc.page_content}" for doc in results])
    except Exception as e:
        return f"搜尋失敗：{str(e)}"

# 定義工具
rag_tool = Tool(
    name="read_knowledge_base",
    description="讀取已上傳的文件。用於查詢內部資料、手冊或財報。",
    func=query_knowledge_base
)