# src/agents/state.py
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field

# --- 核心版型定義 (Layout Constitution) ---
# VALID_LAYOUTS = [
#     "title",       # 封面頁：標題 + 副標題
#     "section",     # 章節頁：僅標題
#     "content",     # 標準頁：標題 + 內容
#     "two_column"   # 雙欄頁：標題 + 左欄 + 右欄
# ]

class ContentItem(BaseModel):
    text: str = Field(description="重點文字內容")
    level: int = Field(default=0, description="縮排層級 (0-8)。0=主重點, 1=子重點。")
    column: int = Field(default=0, description="欄位編號。0=預設/左欄, 1=右欄 (用於雙欄版型)。")

class Slide(BaseModel):
    layout: Literal["title", "section", "content", "two_column"] = Field(
        description="版型 ID，必須精確符合此四者之一。"
    )
    title: str = Field(description="投影片標題")
    content: List[ContentItem] = Field(default_factory=list, description="投影片內容列表")
    notes: str = Field(default="", description="演講者備忘稿 (Speaker Notes)")

class PresentationOutline(BaseModel):
    topic: str = Field(description="簡報主題")
    target_audience: str = Field(description="目標受眾")
    slides: List[Slide] = Field(description="規劃好的投影片列表")

class AgentState(BaseModel):
    """
    LangGraph 的狀態物件，在各個 Node 之間傳遞。
    """
    user_request: str
    chat_history: str = ""
    session_id: str = "default"  # 隔離不同使用者的資料
    outline: Optional[PresentationOutline] = None
    final_file_path: Optional[str] = None
    
    # 專門讓後端把錯誤訊息傳給前端的通道
    error_message: Optional[str] = None