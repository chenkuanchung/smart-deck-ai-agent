# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- 核心模型設定 ---
    MODEL_SMART = "gemini-2.5-flash-lite" # rate limit 限制, 先用輕量模型
    MODEL_FAST = "gemini-2.5-flash-lite" 
    MODEL_EMBEDDING = "models/gemini-embedding-001"
    
    # --- 工具設定 ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    ENV_MODE = os.getenv("ENV_MODE", "dev")

    # --- 檔案路徑設定 ---
    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
    OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
        if not cls.GOOGLE_SEARCH_API_KEY: print("⚠️ Warning: Missing GOOGLE_SEARCH_API_KEY")
        if not cls.GOOGLE_CSE_ID: print("⚠️ Warning: Missing GOOGLE_CSE_ID")
        
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
            
        if missing:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
        return True