# src/agents/manager.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential # [新增] 引入重試套件
from src.config import Config
from src.agents.state import AgentState, PresentationOutline
from src.tools.rag import RAGManager

# 初始化核心模型
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.2 
)

# 企業級 API 呼叫包裝器 (遇到 429 限制時自動等待並重試，最高重試 3 次)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1.5, min=4, max=15), reraise=True)
def call_llm_with_retry(model, messages):
    return model.invoke(messages)

def manager_node(state: AgentState):
    print(f"--- [Manager] 啟動深度規劃 (Session: {state.session_id[:8]}) ---")
    
    rag_manager = RAGManager(state.session_id)
    session_rag_tool = rag_manager.get_tool()
    llm_with_tools = llm.bind_tools([session_rag_tool])
    
    # 1. 資訊盤點 (Information Synthesis)
    investigation_system = """
    你是頂級簡報架構師的「資料盤點助理」。
    你的任務是：檢查前端交接的資料，若需要確認原始文件的精確數據，請呼叫 `read_knowledge_base`。
    
    【警告與守則】：
    1. 現在是準備階段，【絕對不要在此時生成大綱】！
    2. 你絕對不可捏造數據。所有資訊必須來自【Chat History】。
    3. 若判斷資料已足夠排版，請直接回覆「資料確認完畢，可進入排版階段」。
    """
    
    context_msg = f"Chat History (前端交接資料):\n{state.chat_history}\n\nUser Request (最終目標):\n{state.user_request}"

    try:
        response = call_llm_with_retry(llm_with_tools, [
            SystemMessage(content=investigation_system),
            HumanMessage(content=context_msg)
        ])
        
        rag_context = ""
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("  -> Manager 正在向內部知識庫確認細節...")
            for tc in response.tool_calls:
                if tc["name"] == "read_knowledge_base":
                    try:
                        query = tc["args"].get("query", "提取關鍵數據")
                        res = session_rag_tool.invoke(query)
                        rag_context += f"\n【知識庫精確比對結果】:\n{res}\n"
                    except Exception as e:
                        print(f"RAG Error: {e}")
    except Exception as e:
        # ✨ 如果資訊盤點階段就炸了 (例如 429)，直接阻斷並回報
        error_msg = f"資訊盤點階段失敗 (API限制或網路錯誤)：{str(e)}"
        print(error_msg)
        return {"outline": None, "error_message": error_msg}

    # 2. 結構化輸出 (Drafting)
    print("  -> 生成大綱結構...")
    draft_system = """
    請根據【交接資料】與【知識庫比對結果】規劃 PPT 大綱。
    
    【結構規範】：
    1. **ContentItem 層級控制 (Level)**：
       - `level=0`: 核心主軸。
       - `level=1`: 支撐性論點/數據。
       - `level=2`: 補充說明/來源。
    2. **欄位控制 (Column)**：
       - `column=0`: 左欄 (預設)。
       - `column=1`: 右欄 (僅用於 two_column 版型，適合做比較或對比)。
    3. **嚴格基於事實**：嚴禁發明 Chat History 中未提及的新聞或數據。若無數據請標示(需補充數據)。
    """
    
    base_msg = f"【內部文件比對】:{rag_context}\n【Chat History】:{state.chat_history}\n【Req】:{state.user_request}"
    structured_llm = llm.with_structured_output(PresentationOutline)
    
    try:
        draft = call_llm_with_retry(structured_llm, [
            SystemMessage(content=draft_system),
            HumanMessage(content=base_msg)
        ])
    except Exception as e:
        # ✨ 關鍵修改：生成大綱解析失敗，把真實的報錯抓出來傳給前端
        error_msg = f"生成大綱結構失敗 (格式錯亂或API限制)：\n{str(e)}"
        print(error_msg)
        return {"outline": None, "error_message": error_msg}

    # ✨ 防呆：如果 LLM 回傳了空值，但沒拋出 Exception
    if not draft: 
        return {"outline": None, "error_message": "LLM 回傳了空的結果，可能因為上下文不足以產生大綱。"}

    # 3. 邏輯反思 (Logic Reflection)
    print("  -> 進行邏輯與版面反思...")
    reflection_prompt = f"""
    請檢視你剛才產出的這份大綱：{draft.model_dump_json()}
    
    身為架構師，你需要檢查「邏輯」與「排版」：
    【檢查1】：是否有「標題與內文重複」的冗餘資訊？
    【檢查2】：對於對比性內容(如A公司 vs B公司)，是否正確使用了 `two_column` 版型並分置左右欄？
    【檢查3】：單頁資訊量是否過載（超過 6 個重點）？若有，是否該拆頁？
    
    若有任何排版或邏輯瑕疵，請直接給出「具體的修改指令」。
    若結構完美，回傳 "PERFECT"。
    """

    try:
        reflect_res = call_llm_with_retry(llm, reflection_prompt).content.strip()

        if "PERFECT" not in reflect_res.upper(): 
            print(f"  -> 發現版面優化空間:\n{reflect_res}")
            
            refine_system = """
            請根據【修改指令】重組並優化你的大綱結構。
            你只需調整排版與分頁，絕對不可改變或捏造原有的數據與事實。
            """
            
            final_outline = call_llm_with_retry(structured_llm, [
                SystemMessage(content=refine_system),
                HumanMessage(content=f"【原始簡報目標】:{state.user_request}\n【初版大綱】:{draft.model_dump_json()}\n【排版優化指令】:{reflect_res}")
            ])
            # ✨ 最終成功：回傳最終大綱，並清空錯誤
            return {"outline": final_outline, "error_message": None}
            
    except Exception as e:
        # 如果在反思或修改階段炸掉，沒關係，我們至少還有初版 draft 可以用！
        # 這裡不報錯，直接把初版回傳出去，這是非常棒的降級容錯設計。
        print(f"Reflection/Refine Error: {e}. Falling back to initial draft.")
        return {"outline": draft, "error_message": None}
            
    # ✨ 最終成功：回傳初版大綱 (因為反思說 PERFECT)，並清空錯誤
    return {"outline": draft, "error_message": None}