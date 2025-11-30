# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline, Slide
from src.tools.rag import rag_tool

# --- 設定工具 ---
# Manager 專注於內部文件分析，不需要 Google Search (那是 Chat Agent 的工作)
tools = [rag_tool]

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.2 
)

# 綁定工具，讓 Manager 知道它有能力閱讀文件
llm_with_tools = llm.bind_tools(tools)

def manager_node(state: AgentState):
    """
    [Manager] 簡報總監 (主動分析版)
    任務：
    1. 優先從「上傳的文件」中分析出簡報主題與架構。
    2. 參考「對話紀錄」中的使用者指示或外部搜尋結果。
    3. 規劃 PPT 結構。
    """
    print("--- [Manager] 開始思考與規劃 ---")
    
    # --- 階段一：主動調查 (Investigation) ---
    # 目標：決定是否需要深入閱讀文件 (幾乎總是需要)
    
    # [修正] System Prompt 只放「規則」與「思考邏輯」
    investigation_system = """
    你是一位專業的簡報架構師。你的核心任務是規劃一份 PowerPoint 的結構。
    
    【決策依據】：
    1. **檔案內容優先 (File Centric)**：簡報的主題 (Topic) 與核心內容，通常隱藏在使用者上傳的文件中。你必須把它挖掘出來。
    2. **對話紀錄輔助 (Chat Context)**：對話紀錄可能包含使用者對簡報風格的要求，或是 Chat Agent 已經透過 Google 搜尋補充的外部資訊。

    【你的思考步驟】：
    - **Step 1: 判斷主題**
      - 如果使用者沒有明確指定簡報主題（例如只說「幫我做簡報」），**你必須主動呼叫 `read_knowledge_base`**。
      - Query 策略：查詢 "分析這份文件的核心主題、目標受眾、關鍵結論與章節架構"。
      
    - **Step 2: 檢查細節**
      - 如果使用者有指定特定主題，請針對該主題查詢文件中的細節。
      
    - **Step 3: 外部資訊**
      - 如果對話紀錄中有 Chat Agent 查到的外部資訊，請在心中記下，稍後規劃時使用。
    """
    
    # [修正] 將動態內容 (Request & History) 放入 HumanMessage
    # 這確保了 API 的 contents 欄位不為空
    user_context = f"""
    【當前狀態】：
    1. 使用者請求：{state.user_request}
    2. 對話紀錄：
    {state.chat_history if state.chat_history else "(無對話紀錄)"}
    
    請判斷下一步行動（直接回應或呼叫工具）。
    """
    
    # 組合 Prompt (System + Human)
    messages = [
        SystemMessage(content=investigation_system),
        HumanMessage(content=user_context)
    ]
    
    # 讓 LLM 決定行動
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        print(f"⚠️ Manager Investigation Error: {e}")
        # 如果第一階段失敗，建立一個空的 response 讓流程繼續 (雖然這很少發生)
        response = type('obj', (object,), {'tool_calls': []})()

    context_data = "" 
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print("  -> Manager 決定深入閱讀文件以分析主題...")
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            print(f"     使用的工具: {tool_name}, 參數: {tool_args}")
            
            if tool_name == "read_knowledge_base":
                try:
                    q = tool_args.get("query", "分析文件核心主題與架構")
                    tool_result = rag_tool.invoke(q)
                except Exception as e:
                    tool_result = f"RAG Error: {e}"
            else:
                tool_result = "Manager 僅支援 RAG 工具"
            
            context_data += f"\n【文件深度檢索結果】:\n{tool_result}\n"
    else:
        print("  -> Manager 認為資訊已充足 (可能使用者在對話中已經把內容講得很清楚)。")

    # --- 階段二：結構規劃 (Planning) ---
    print("--- [Manager] 綜合資訊產生大綱 ---")
    
    planning_system = """
    你現在擁有充足的背景資訊，請規劃一份 PowerPoint 大綱。
    
    【規劃準則】：
    1. **主題定案 (Topic Definition)**：
       - 如果使用者未指定，請根據【文件深度檢索結果】自動歸納出最合適的簡報主題。
       - 主題必須具體（例如：「2024 Q3 財務分析報告」優於「財務簡報」）。
       
    2. **內容權重**：
       - **核心骨幹**：必須來自上傳的文件內容。
       - **補充枝葉**：使用對話紀錄中的外部搜尋資訊來豐富內容（如市場現況、競品比較）。
       
    3. **結構要求**：
       - 投影片至少 5-10 頁。
       - **notes**: 每一頁都 **必須** 撰寫演講者備忘稿，這很重要。
       - **layout**: 必須是 'title', 'section', 'content', 'two_column' 之一。
    
    請直接產出 JSON。
    """
    
    # 同樣地，這裡也要確保 contents 不為空
    planning_user_msg = f"""
    【文件深度檢索結果 (RAG)】：
    {context_data if context_data else "無額外文件檢索 (依賴對話紀錄)"}
    
    【使用者對話紀錄 (含外部搜尋結果)】：
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

    # 防呆備案
    if outline is None:
        outline = PresentationOutline(
            topic="生成失敗",
            target_audience="User",
            slides=[Slide(layout="title", title="錯誤提示", content=["無法產生結構"], notes="請檢查 RAG 或 LLM 連線")]
        )
    
    return {"outline": outline}