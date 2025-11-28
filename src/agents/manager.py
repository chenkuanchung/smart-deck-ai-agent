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
    分析對話紀錄中的資訊，將其轉化為一份邏輯清晰的簡報大綱。

    ### 處理策略 (Strategy)：
    1. **情況 A：對話中已有明確大綱**
       - 若 AI 在對話中已經列出了「投影片 1... 投影片 2...」，請**優先並忠實地**採用該結構，不要隨意更改使用者的意圖。
    
    2. **情況 B：對話中僅有內容討論 (或是文件總結)**
       - 若對話只是針對內容的探討，請發揮你的專業能力，將這些資訊**歸納、整理**，並重新規劃成一份 5-10 頁的簡報結構。
       - 確保邏輯連貫（起承轉合）。

    ### 欄位填寫規則 (Field Instructions)：
    1. **layout**: 請判斷版型 ('title', 'section', 'content', 'two_column')。
    2. **title**: 填寫投影片標題。
    3. **content**: 填寫投影片內文重點 (List[str])。
    4. **notes**: 請為每一頁撰寫「演講者備忘稿」。若對話中未提及，請根據標題與內文**自動生成**適合的講稿提示（例如：「本頁重點在於說明...」）。
    
    請確保輸出的 JSON 格式絕對正確，不要遺漏任何一頁。
    """

    structured_llm = llm.with_structured_output(PresentationOutline)
    
    user_msg = f"""
    【使用者原始需求】：{state.user_request}
    
    【完整對話紀錄】：
    {state.chat_history}
    
    請根據上述紀錄，生成最終的簡報結構 JSON。
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
                Slide(layout="title", title="生成失敗提示", content=["AI 無法將對話轉為結構化資料", "請查看終端機 (Terminal) 的錯誤訊息"], notes="請檢查程式日誌"),
                Slide(layout="content", title="可能原因", content=["1. 對話紀錄過長", "2. 模型輸出格式錯誤", "3. 請嘗試更換為 Gemini Pro 模型"], notes="請嘗試縮短對話或重試")
            ]
        )
    
    return {"outline": response}