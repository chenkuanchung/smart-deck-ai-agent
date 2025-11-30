# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline, Slide
from src.tools.rag import rag_tool

# --- 設定工具 ---
tools = [rag_tool]

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.2 
)

llm_with_tools = llm.bind_tools(tools)

def manager_node(state: AgentState):
    """
    [Manager] 簡報總監 (全方位整合版)
    任務：
    1. 綜合「文件檢索 (RAG)」與「對話紀錄 (Chat History)」的所有資訊。
    2. 只有在「完全無資訊」時才阻擋生成。
    3. 負責內容的「分頁」與「細節保留」。
    """
    print("--- [Manager] 開始思考與規劃 ---")
    
    # --- 階段一：廣泛調查 (Comprehensive Investigation) ---
    
    investigation_system = """
    你是一位專業的簡報架構師。
    
    【你的核心任務】：
    盡可能從所有可用來源中蒐集資訊，以規劃出內容豐富的簡報。
    
    【資訊來源策略】：
    1. **文件檢索 (RAG)**：這是最核心的來源。請務必呼叫 `read_knowledge_base` 來獲取上傳文件的細節。
    2. **對話紀錄 (Chat History)**：這是重要的補充來源。使用者可能在對話中提供了額外指示，或者 Chat Agent 已經幫忙查到了外部資訊。
    
    【執行步驟】：
    不管使用者有沒有在對話中提供資訊，你都應該嘗試呼叫 `read_knowledge_base`，以確保沒有遺漏上傳的檔案。
    查詢指令：「詳細列出所有文檔的具體文字內容、細節」。
    """
    
    user_context = f"""
    【當前狀態】：
    使用者請求：{state.user_request}
    
    請執行工具呼叫。
    """
    
    messages = [
        SystemMessage(content=investigation_system),
        HumanMessage(content=user_context)
    ]
    
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        print(f"⚠️ Manager Investigation Error: {e}")
        response = type('obj', (object,), {'tool_calls': []})()

    context_data = "" 
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print("  -> Manager 正在查詢文件庫...")
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            if tool_name == "read_knowledge_base":
                try:
                    q = "詳細列出所有章節的具體規範、數字、時間、金額、倍率與限制條件"
                    tool_result = rag_tool.invoke(q)
                    context_data += f"\n【文件深度檢索結果】:\n{tool_result}\n"
                except Exception as e:
                    tool_result = f"RAG Error: {e}"
    else:
        print("  ⚠️ Manager 決定不呼叫工具 (可能是對話紀錄資訊已極度充足)。")

    # --- 階段二：結構規劃 (Planning with Pagination) ---
    print("--- [Manager] 綜合資訊產生大綱 ---")
    
    # [關鍵優化] 加入「綜合參照」與「分頁處理」的指令
    planning_system = """
    你現在擁有背景資訊，請規劃一份 PowerPoint 大綱。
    
    【資訊整合邏輯 (Information Synthesis)】：
    請綜合參考【文件檢索結果】與【使用者對話紀錄】。
    - 如果文件有詳細規定，請優先採用。
    - 如果文件沒有，但對話紀錄有（例如網路搜尋結果），請採用對話紀錄。
    - 只有在「兩者皆空」的情況下，才生成錯誤提示頁面。
    
    【版型規範】：
    使用 'title', 'section', 'content', 'two_column', 'comparison'。
    
    【內容填寫鐵律 (Content Rules)】：
    1. **數據保留**：具體數字、時間、倍率、金額必須完整保留。
    2. **分頁處理 (Pagination)**：
       - 如果某個章節的重點超過 7-8 點，或者文字量過大，**請主動拆分為兩頁**。
       - 例如：「工時規範 (1/2)」、「工時規範 (2/2)」。
       - 嚴禁為了塞進一頁而刪減重要細節。
    3. **條列式呈現**：將長條款拆解為多個字串放入 `content` list。
    
    請直接產出 JSON。
    """
    
    planning_user_msg = f"""
    【文件深度檢索結果 (RAG)】：
    {context_data if context_data else "無文件資訊 (請檢查對話紀錄)"}
    
    【使用者對話紀錄 (Chat History)】：
    {state.chat_history}
    
    【使用者原始需求】：
    {state.user_request}
    """
    
    structured_llm = llm.with_structured_output(PresentationOutline)
    
    final_messages = [
        SystemMessage(content=planning_system),
        HumanMessage(content=planning_user_msg)
    ]
    
    try:
        outline = structured_llm.invoke(final_messages)
    except Exception as e:
        print(f"⚠️ Manager Planning Error: {e}")
        outline = None

    if outline is None:
        outline = PresentationOutline(
            topic="生成失敗",
            target_audience="User",
            slides=[Slide(layout="title", title="錯誤提示", content=["無法產生結構"], notes="請檢查系統")]
        )
    
    return {"outline": outline}