# src/config.py
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

class Config:
    # 核心模型設定
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # 搜尋工具設定
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    
    # 專案設定
    ENV_MODE = os.getenv("ENV_MODE", "dev") # 預設為 dev
    
    # 確認 Key 是否存在 (除錯用)
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
        if not cls.GOOGLE_SEARCH_API_KEY: missing.append("GOOGLE_SEARCH_API_KEY")
        if not cls.GOOGLE_CSE_ID: missing.append("GOOGLE_CSE_ID")
        
        if missing:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
        return True