# src/tools/rag.py
import os
import shutil
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import Tool
from src.config import Config

# 設定路徑
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

embeddings = GoogleGenerativeAIEmbeddings(
    model=Config.MODEL_EMBEDDING,
    google_api_key=Config.GOOGLE_API_KEY
)

vector_store = Chroma(
    collection_name="smart_deck_docs",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY
)

def ingest_file(file_path: str):
    """讀取檔案並存入向量庫"""
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path): return f"❌ 錯誤：找不到 {file_path}"
    
    try:
        if file_path.lower().endswith('.pdf'): loader = PyPDFLoader(file_path)
        elif file_path.lower().endswith('.txt'): loader = TextLoader(file_path, encoding='utf-8')
        else: return "❌ 只支援 PDF/TXT"

        docs = loader.load()
        for doc in docs: doc.metadata["source"] = file_path
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        if splits:
            vector_store.add_documents(documents=splits)
            return f"✅ 已存入知識庫: {os.path.basename(file_path)}"
        return "⚠️ 檔案內容為空。"
    except Exception as e:
        return f"❌ 讀取失敗：{str(e)}"

def remove_file_from_db(filename: str):
    try:
        file_path = os.path.abspath(os.path.join(Config.UPLOAD_DIR, filename))
        existing_docs = vector_store.get(where={"source": file_path})
        if existing_docs['ids']:
            vector_store.delete(ids=existing_docs['ids'])
        
        if os.path.exists(file_path): os.remove(file_path)
        return f"🗑️ 已移除 {filename}"
    except Exception as e: return f"❌ 移除失敗：{e}"

def reset_vector_store():
    global vector_store
    try:
        try: vector_store.delete_collection()
        except: pass
        
        vector_store = Chroma(
            collection_name="smart_deck_docs",
            embedding_function=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        
        if os.path.exists(Config.UPLOAD_DIR):
            shutil.rmtree(Config.UPLOAD_DIR)
            os.makedirs(Config.UPLOAD_DIR)
        return "✅ 重置完成"
    except Exception as e: return f"❌ 重置失敗: {e}"

def query_knowledge_base(query: str):
    """
    查詢知識庫。
    [關鍵優化]：如果知識庫是空的，直接回傳特定字串引導 Agent 去 Google。
    """
    try:
        # 檢查 Collection 是否有資料
        # ChromaDB 的 get() 默認回傳所有 ID，如果為空 list 代表沒資料
        check_empty = vector_store.get()
        if not check_empty['ids']:
            return "【系統提示】：目前知識庫是空的（使用者尚未上傳任何文件）。請立刻改用 `Google Search` 查詢外部資訊。"

        results = vector_store.similarity_search(query, k=4)
        if not results:
            return "知識庫中找不到相關資訊。建議使用 google_search。"
        return "\n\n".join([f"---片段---\n{doc.page_content}" for doc in results])
    except Exception as e:
        return f"搜尋失敗：{str(e)}"

rag_tool = Tool(
    name="read_knowledge_base",
    description="讀取已上傳的文件。若無上傳文件，請勿使用此工具。",
    func=query_knowledge_base
)