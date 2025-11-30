# src/tools/rag.py
import os
import shutil
import glob
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import Tool
from src.config import Config  # 記得 import Config

# 設定路徑
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

# 初始化 Embedding
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
    # 確保路徑是絕對路徑
    file_path = os.path.abspath(file_path)
    
    if not os.path.exists(file_path):
        return f"❌ 錯誤：找不到檔案 {file_path}"
    
    try:
        # 載入器邏輯
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.lower().endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        else:
            return "❌ 目前只支援 PDF 與 TXT"

        docs = loader.load()
        # 將 source 標記為絕對路徑
        for doc in docs:
            doc.metadata["source"] = file_path
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        if splits:
            vector_store.add_documents(documents=splits)
            return f"✅ 成功：已將 {os.path.basename(file_path)} 存入知識庫。"
        else:
            return "⚠️ 檔案內容為空。"
            
    except Exception as e:
        return f"❌ 讀取失敗：{str(e)}"

def remove_file_from_db(filename: str):
    """從向量資料庫中移除指定檔案，並刪除實體檔案"""
    try:
        # [修改] 路徑指向 Config.UPLOAD_DIR
        file_path = os.path.abspath(os.path.join(Config.UPLOAD_DIR, filename))
        msg = []

        # 1. 處理資料庫刪除
        existing_docs = vector_store.get(where={"source": file_path})
        if existing_docs['ids']:
            vector_store.delete(ids=existing_docs['ids'])
            msg.append(f"資料庫紀錄已移除 ({len(existing_docs['ids'])} 筆)")
        else:
            msg.append("資料庫中無此紀錄")

        # 2. 處理實體檔案刪除
        if os.path.exists(file_path):
            os.remove(file_path)
            msg.append("實體檔案已刪除")
        else:
            msg.append("實體檔案不存在")

        return f"🗑️ {filename}: " + "，".join(msg)

    except Exception as e:
        return f"❌ 移除失敗：{str(e)}"

def reset_vector_store():
    """清空知識庫與上傳目錄"""
    global vector_store
    logs = []
    
    try:
        # 1. 清空 ChromaDB Collection
        try:
            vector_store.delete_collection()
            logs.append("Collection 已重置")
        except:
            pass

        # 重新初始化 Vector Store
        vector_store = Chroma(
            collection_name="smart_deck_docs",
            embedding_function=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        
        # 2. [修改] 直接清空 uploads 資料夾
        # 這樣做更乾淨，不需要用 glob 去過濾副檔名
        if os.path.exists(Config.UPLOAD_DIR):
            # 刪除整個資料夾
            shutil.rmtree(Config.UPLOAD_DIR)
            # 馬上重建一個空的
            os.makedirs(Config.UPLOAD_DIR)
            logs.append("Uploads 目錄已清空")
        
        return "✅ 重置完成: " + "，".join(logs)

    except Exception as e:
        return f"❌ 重置失敗: {str(e)}"

def query_knowledge_base(query: str):
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