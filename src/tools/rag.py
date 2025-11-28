# src/tools/rag.py
import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import Tool
from src.config import Config
import shutil

# 設定路徑
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

# 初始化 Embedding
embeddings = GoogleGenerativeAIEmbeddings(
    model=Config.MODEL_EMBEDDING,
    google_api_key=Config.GOOGLE_API_KEY
)

# 初始化 Vector Store
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
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.lower().endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            return "❌ 目前只支援 PDF 與 TXT"

        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        if splits:
            vector_store.add_documents(documents=splits)
            return f"✅ 成功：已將 {os.path.basename(file_path)} 存入知識庫。"
        else:
            return "⚠️ 檔案內容為空。"
            
    except Exception as e:
        return f"❌ 讀取失敗：{str(e)}"

# [新增功能] 根據檔名刪除資料
def remove_file_from_db(filename: str):
    """從向量資料庫中移除指定檔案的所有片段"""
    try:
        # ChromaDB 存的時候會把 file_path 寫在 metadata 的 'source' 欄位
        # 我們要還原出當初存的絕對路徑才能刪除
        file_path = os.path.join(os.getcwd(), filename)
        
        # 使用 where 條件刪除
        vector_store.delete(where={"source": file_path})
        return f"🗑️ 已從知識庫移除：{filename}"
    except Exception as e:
        return f"❌ 移除失敗：{str(e)}"

def reset_vector_store():
    """清空整個知識庫"""
    global vector_store
    try:
        try:
            vector_store.delete_collection()
        except:
            pass
        if os.path.exists(PERSIST_DIRECTORY):
            shutil.rmtree(PERSIST_DIRECTORY)
        vector_store = Chroma(
            collection_name="smart_deck_docs",
            embedding_function=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        return "✅ 知識庫已清空。"
    except Exception as e:
        return f"❌ 重置失敗: {str(e)}"

def query_knowledge_base(query: str):
    """搜尋"""
    try:
        results = vector_store.similarity_search(query, k=4)
        if not results:
            return "知識庫中找不到相關資訊。"
        return "\n\n".join([f"---片段---\n{doc.page_content}" for doc in results])
    except Exception as e:
        return f"搜尋失敗：{str(e)}"

# Tool 定義
rag_tool = Tool(
    name="read_knowledge_base",
    description="讀取已上傳的文件。用於查詢內部資料。",
    func=query_knowledge_base
)