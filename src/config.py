# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # --- 核心模型設定 ---
    # Smart 模型負責 Manager 的複雜規劃與反思 (建議使用 Pro)
    MODEL_SMART = "gemini-2.5-pro"
    
    # Fast 模型負責 Chat Agent 的快速回應與 Writer 的簡單處理 (使用 Flash)
    MODEL_FAST = "gemini-2.5-flash" 
    
    MODEL_EMBEDDING = "models/text-embedding-004"
    
    # --- 工具設定 ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    ENV_MODE = os.getenv("ENV_MODE", "dev")

    # --- 檔案路徑設定 ---
    # 確保上傳與生成的檔案有地方放
    UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
        # 搜尋功能選填，但強烈建議要有
        if not cls.GOOGLE_SEARCH_API_KEY: print("⚠️ Warning: Missing GOOGLE_SEARCH_API_KEY")
        if not cls.GOOGLE_CSE_ID: print("⚠️ Warning: Missing GOOGLE_CSE_ID")
        
        # 自動建立 uploads 資料夾
        if not os.path.exists(cls.UPLOAD_DIR):
            os.makedirs(cls.UPLOAD_DIR)
            
        if missing:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
        return True