# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline, Slide

# 初始化 Gemini
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST,
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.7
)

def manager_node(state: AgentState):
    """
    [Manager] 簡報總監
    任務：讀取對話紀錄，規劃 PPT 結構 (JSON)
    """
    print("--- [Manager] 正在根據對話紀錄規劃大綱 ---")
    
    system_prompt = """你是一位專業的簡報架構師。你的任務是根據「使用者與 AI 的對話紀錄」，規劃一份 PowerPoint 的結構。
    
    ### 可用版型 (Layouts)：
    - 'title': 封面 (標題 + 副標題) -> 第一頁。
    - 'section': 章節頁 (大標題 + 簡述)。
    - 'content': 標準內文 (標題 + 條列重點)。
    - 'two_column': 雙欄對照 (標題 + 左欄 + 右欄)。
    
    ### 規劃原則：
    1. 即使對話紀錄很少，也要盡力規劃出一份基本的簡報（至少包含封面和一頁內文）。
    2. 如果資訊不足，請幫使用者「發想」合理的內容填入。
    """

    structured_llm = llm.with_structured_output(PresentationOutline)
    
    user_msg = f"""
    【使用者原始需求】：{state.user_request}
    
    【完整對話紀錄】：
    {state.chat_history}
    
    請產出簡報大綱。如果對話紀錄空白，請以「專案報告」為主題自動發想。
    """
    
    # 呼叫模型
    try:
        response = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg)
        ])
    except Exception as e:
        print(f"⚠️ Manager LLM Error: {e}")
        response = None

    # [關鍵修正] 防呆機制：如果 AI 產出失敗 (None)，手動建立一個預設大綱
    if response is None:
        print("⚠️ 警告：Manager 無法生成大綱，使用預設備案。")
        response = PresentationOutline(
            topic="自動生成失敗",
            target_audience="使用者",
            slides=[
                Slide(layout="title", title="生成失敗提示", content=["AI 無法根據目前對話規劃大綱", "請嘗試多聊幾句再試一次"], notes=""),
                Slide(layout="content", title="建議做法", content=["1. 確保已上傳文件", "2. 請先在聊天室要求 AI '總結內容'", "3. 再次點擊生成按鈕"], notes="")
            ]
        )
    
    return {"outline": response}