# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- 核心模型設定 (保持不變) ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    MODEL_FAST = "gemini-2.5-flash" 
    MODEL_SMART = "gemini-2.5-pro"
    MODEL_EMBEDDING = "models/text-embedding-004"
    
    # --- 工具設定 (保持不變) ---
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    ENV_MODE = os.getenv("ENV_MODE", "dev")

    # --- [新增] 檔案路徑設定 ---
    # 這是我們存放上傳檔案的專用資料夾
    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
        if not cls.GOOGLE_SEARCH_API_KEY: missing.append("GOOGLE_SEARCH_API_KEY")
        if not cls.GOOGLE_CSE_ID: missing.append("GOOGLE_CSE_ID")
        
        # [新增] 自動建立 uploads 資料夾，如果不存在的話
        if not os.path.exists(cls.UPLOAD_DIR):
            os.makedirs(cls.UPLOAD_DIR)
            
        if missing:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
        return True