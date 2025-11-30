# src/agents/state.py
from typing import List, Optional
from pydantic import BaseModel, Field

# --- 核心版型定義 (Layout Constitution) ---
# 這是唯一的真理來源，所有 Agent 都必須遵守此定義
VALID_LAYOUTS = [
    "title",       # 封面頁：標題 + 副標題
    "section",     # 章節頁：僅標題
    "content",     # 標準頁：標題 + 單欄條列內容
    "two_column",  # 雙欄頁：標題 + 左欄 + 右欄
    "comparison"   # 比較頁：標題 + 左比較項 + 右比較項
]

class Slide(BaseModel):
    layout: str = Field(
        description=f"版型 ID。嚴格限制為以下之一: {', '.join(VALID_LAYOUTS)}。"
    )
    title: str = Field(description="投影片標題")
    
    # [關鍵修正] 加入 default_factory=list，讓 content 變成選填
    # 這樣當 layout="section" 時，Manager 不填 content 也不會報錯
    content: List[str] = Field(
        default_factory=list,
        description="投影片內容。'content' 版型為重點列表；'two_column'/'comparison' 則依序代表 [左欄內容, 右欄內容]。若為 section 版型可為空。"
    )
    
    notes: str = Field(default="", description="演講者備忘稿 (Speaker Notes)")

class PresentationOutline(BaseModel):
    topic: str = Field(description="簡報主題")
    target_audience: str = Field(description="目標受眾")
    slides: List[Slide] = Field(description="規劃好的投影片列表")

class AgentState(BaseModel):
    user_request: str
    chat_history: str = ""
    outline: Optional[PresentationOutline] = None
    final_file_path: Optional[str] = None