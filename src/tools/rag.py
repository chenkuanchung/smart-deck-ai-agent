# src/tools/rag.py
import os
import shutil
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.tools import Tool
from langchain_core.documents import Document # 用於重建文件格式
from langchain_community.retrievers import BM25Retriever # 關鍵字檢索器
from langchain.retrievers import EnsembleRetriever # 混合檢索融合器
from src.config import Config
from pydantic import BaseModel, Field

# 設定路徑
PERSIST_DIRECTORY = os.path.join(os.getcwd(), "chroma_db")

embeddings = GoogleGenerativeAIEmbeddings(
    model=Config.MODEL_EMBEDDING,
    google_api_key=Config.GOOGLE_API_KEY
)

# 定義參數架構
class RagInput(BaseModel):
    query: str = Field(description="The query string to search in the knowledge base.")

class RAGManager:
    """
    每個使用者 (Session) 專屬的 RAG 管理器。
    支援 Hybrid Search (Vector Search + BM25 Keyword Search)。
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.collection_name = f"user_{session_id.replace('-', '_')}"
        self.upload_dir = os.path.join(Config.UPLOAD_DIR, self.session_id)
        
        os.makedirs(self.upload_dir, exist_ok=True)
        
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )

    def ingest_file(self, uploaded_file_bytes: bytes, filename: str):
        """將二進位檔案寫入專屬目錄並存入向量庫"""
        file_path = os.path.join(self.upload_dir, filename)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file_bytes)
            
        try:
            if file_path.lower().endswith('.pdf'): loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith('.txt'): loader = TextLoader(file_path, encoding='utf-8')
            else: return "❌ 只支援 PDF/TXT"

            docs = loader.load()
            for doc in docs: doc.metadata["source"] = file_path
                
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
            splits = text_splitter.split_documents(docs)
            
            if splits:
                self.vector_store.add_documents(documents=splits)
                return f"✅ 已存入知識庫: {filename}"
            return "⚠️ 檔案內容為空。"
        except Exception as e:
            return f"❌ 讀取失敗：{str(e)}"

    def remove_file(self, filename: str):
        """從專屬資料庫與實體目錄中移除檔案"""
        try:
            file_path = os.path.join(self.upload_dir, filename)
            existing_docs = self.vector_store.get(where={"source": file_path})
            if existing_docs['ids']:
                self.vector_store.delete(ids=existing_docs['ids'])
            
            if os.path.exists(file_path): 
                os.remove(file_path)
            return f"🗑️ 已移除 {filename}"
        except Exception as e: 
            return f"❌ 移除失敗：{e}"

    def reset(self):
        """清空該使用者的專屬資料庫與目錄"""
        try: self.vector_store.delete_collection()
        except: pass
        
        if os.path.exists(self.upload_dir):
            shutil.rmtree(self.upload_dir)
            os.makedirs(self.upload_dir, exist_ok=True)
            
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        return "✅ 重置完成"

    def query(self, query_str: str):
        """
        執行 Hybrid Search (向量語意 + 關鍵字比對)
        """
        try:
            # 1. 檢查知識庫是否為空
            db_data = self.vector_store.get()
            if not db_data['ids']:
                return "【系統提示】：目前知識庫是空的（使用者尚未上傳任何文件）。"

            # 2. 建立 Vector Search 檢索器 (擅長抓語意)
            chroma_retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})

            # 3. 建立 BM25 檢索器 (擅長抓精確關鍵字、數字)
            # 將 Chroma 裡的原始資料即時轉為 Document 物件給 BM25 吃
            docs = [Document(page_content=doc, metadata=meta) 
                    for doc, meta in zip(db_data['documents'], db_data['metadatas'])]
            bm25_retriever = BM25Retriever.from_documents(docs)
            bm25_retriever.k = 4 

            # 4. 建立 Ensemble Retriever (混合檢索)
            # weights=[0.5, 0.5] 代表向量與關鍵字的比重各佔 50%
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, chroma_retriever],
                weights=[0.5, 0.5]
            )

            # 5. 執行融合搜尋
            results = ensemble_retriever.invoke(query_str)
            
            if not results:
                return "知識庫中找不到相關資訊。"
                
            # Ensemble 融合後可能會回傳超過 4 筆（去除重複後），我們取前 5 筆最精華的傳給 LLM
            return "\n\n".join([f"---片段---\n{doc.page_content}" for doc in results[:5]])
            
        except Exception as e:
            return f"搜尋失敗：{str(e)}"

    def get_tool(self):
        """產出綁定此 Session 的 LangChain Tool 物件"""
        return Tool(
            name="read_knowledge_base",
            description="讀取使用者已上傳的文件。若無上傳文件，請勿使用。支援精確數字與語意混合搜尋。",
            func=self.query,
            args_schema=RagInput
        )