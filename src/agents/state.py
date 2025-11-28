# src/agents/state.py
from typing import List, Optional
from pydantic import BaseModel, Field

# --- 1. 定義單頁投影片結構 ---
class Slide(BaseModel):
    layout: str = Field(
        description="版型 ID。必須是以下之一: 'title', 'section', 'content', 'two_column', 'comparison'"
    )
    title: str = Field(description="投影片標題")
    
    # content: 單欄是 List[str]，雙欄也是 List[str]
    content: List[str] = Field(description="投影片內容。若為單欄請提供一段文字；若為雙欄請提供兩段文字(左, 右)。")
    
    # [關鍵修正] 加入 default=""，這樣就算 AI 忘了產生 notes 也不會報錯
    notes: str = Field(default="", description="演講者備忘稿 (Speaker Notes)，給講者看的提示")

# --- 2. 定義整份簡報大綱 ---
class PresentationOutline(BaseModel):
    topic: str = Field(description="簡報主題")
    target_audience: str = Field(description="目標受眾")
    slides: List[Slide] = Field(description="規劃好的投影片列表")

# --- 3. 定義 Agent 共享狀態 ---
class AgentState(BaseModel):
    # 這裡放我們在 Graph 中流動的資料
    user_request: str                   # 原始需求 (或對話摘要)
    chat_history: str = ""              # 完整的對話紀錄 (這是 Manager 規劃的依據)
    outline: Optional[PresentationOutline] = None # Manager 產出的大綱
    final_file_path: Optional[str] = None # 最終生成的檔案路徑