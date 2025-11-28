# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline

# 初始化 Gemini (使用快速模型規劃結構)
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
    
    # 1. 設定 System Prompt (教它版型規則)
    system_prompt = """你是一位專業的簡報架構師。你的任務是根據「使用者與 AI 的對話紀錄」，規劃一份 PowerPoint 的結構。
    
    ### 可用版型 (Layouts)：
    - 'title': 封面 (標題 + 副標題) -> 只用在第一頁。
    - 'section': 章節頁 (大標題 + 簡述) -> 用於切換主題。
    - 'content': 標準內文 (標題 + 條列重點) -> 最常用的版型。
    - 'two_column': 雙欄對照 (標題 + 左欄 + 右欄) -> 適合比較、優缺點、現況vs未來。
    
    ### 規劃原則：
    1. **邏輯連貫**：從對話紀錄中提煉出核心觀點，轉化為有邏輯的章節。
    2. **頁數控制**：除非內容極多，否則控制在 5-10 頁之間。
    3. **內容指引**：在 content 欄位中，先寫下簡短的指引（例如："列出三個主要優勢"），Writer 後續會擴寫。
    """

    # 2. 強制輸出結構化資料 (Structured Output)
    structured_llm = llm.with_structured_output(PresentationOutline)
    
    # 3. 組合 Prompt
    # 我們把 Chat History 餵給它，讓它知道剛剛發生了什麼事
    user_msg = f"""
    【使用者原始需求】：{state.user_request}
    
    【完整對話紀錄】：
    {state.chat_history}
    
    請根據以上資訊，產出簡報大綱。
    """
    
    # 4. 呼叫模型
    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_msg)
    ])
    
    return {"outline": response}