# src/config.py
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

class Config:
    # --- 核心模型設定 (支援 2025 最新版) ---
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # 快速模型 (用於 RAG 聊天、規劃大綱)
    # 註：若 API 尚未支援 "gemini-2.5-flash"，請暫時改回 "gemini-1.5-flash"
    MODEL_FAST = "gemini-2.5-flash" 
    
    # 聰明模型 (用於撰寫詳細內容)
    MODEL_SMART = "gemini-2.5-pro"
    
    # Embedding 模型 (用於 RAG 向量化)
    MODEL_EMBEDDING = "models/text-embedding-004"
    
    # --- 工具設定 ---
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
    
    # --- 專案設定 ---
    ENV_MODE = os.getenv("ENV_MODE", "dev")
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
        if not cls.GOOGLE_SEARCH_API_KEY: missing.append("GOOGLE_SEARCH_API_KEY")
        if not cls.GOOGLE_CSE_ID: missing.append("GOOGLE_CSE_ID")
        
        if missing:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing)}")
        return True