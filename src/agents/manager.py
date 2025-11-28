# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline, Slide

# 初始化 Gemini
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.2 
)

def manager_node(state: AgentState):
    """
    [Manager] 簡報總監
    任務：讀取對話紀錄，規劃 PPT 結構 (JSON)
    """
    print("--- [Manager] 正在根據對話紀錄規劃大綱 ---")
    
    system_prompt = """你是一位專業的簡報架構師。你的任務是根據「使用者與 AI 的對話紀錄」，規劃一份 PowerPoint 的結構。

    ### 你的核心目標：
    分析對話紀錄中的資訊，將其轉化為一份邏輯清晰的簡報大綱 JSON。

    ### 處理策略 (Strategy)：
    1. **情況 A：對話中已有明確大綱** -> 忠實還原。
    2. **情況 B：對話中僅有內容討論** -> 歸納整理並重新規劃 (5-10 頁)。

    ### 欄位填寫規則：
    1. **layout**: 必須是 'title', 'section', 'content', 'two_column' 其中之一。
    2. **notes**: **(重要)** 必須為每一頁撰寫演講者備忘稿。

    ### 輸出範例 (Output Example)：
    ```json
    {
      "topic": "專案進度報告",
      "target_audience": "部門主管",
      "slides": [
        {
          "layout": "title",
          "title": "Q3 專案進度匯報",
          "content": ["報告人：王小明"],
          "notes": "各位主管好，今天要跟各位報告 Q3 的執行狀況。"
        },
        {
          "layout": "content",
          "title": "核心成效數據",
          "content": ["營收成長 20%", "用戶數突破 100 萬"],
          "notes": "首先看到數據面，我們達成了雙位數成長。"
        },
        {
          "layout": "two_column",
          "title": "A/B 方案比較",
          "content": ["方案 A：成本低但耗時", "方案 B：成本高但快速"],
          "notes": "左邊是保守方案，右邊是激進方案，我們建議採用 B。"
        }
      ]
    }
    ```
    
    請確保輸出的 JSON 格式與上述範例結構一致。
    """

    structured_llm = llm.with_structured_output(PresentationOutline)
    
    user_msg = f"""
    【使用者原始需求】：{state.user_request}
    
    【完整對話紀錄】：
    {state.chat_history}
    
    請產出簡報大綱 JSON。
    """
    
    # 呼叫模型
    try:
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg)
        ])
    except Exception as e:
        print(f"⚠️ Manager LLM Error (詳細錯誤): {e}")
        response = None

    # 防呆機制
    if response is None:
        print("⚠️ 警告：Manager 無法生成大綱，使用預設備案。")
        response = PresentationOutline(
            topic="自動生成失敗",
            target_audience="使用者",
            slides=[
                Slide(layout="title", title="生成失敗提示", content=["AI 無法將對話轉為結構化資料", "請查看終端機錯誤"], notes="請檢查程式日誌")
            ]
        )
    
    return {"outline": response}