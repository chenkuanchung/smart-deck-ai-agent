# src/agents/manager.py
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import Config
from src.agents.state import AgentState, PresentationOutline, Slide, ContentItem
from src.tools.rag import rag_tool

# 使用較聰明的 Pro 模型進行規劃與反思
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.2 
)
llm_with_tools = llm.bind_tools([rag_tool])

def manager_node(state: AgentState):
    print("--- [Manager] 啟動深度規劃 ---")
    
    # 1. 廣泛調查 (Initial Investigation)
    investigation_system = "你是一位簡報架構師。請先呼叫 `read_knowledge_base` 掃描上傳文件的核心數據與章節架構。"
    try:
        response = llm_with_tools.invoke([
            SystemMessage(content=investigation_system),
            HumanMessage(content=f"User Request: {state.user_request}")
        ])
        
        rag_context = ""
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("  -> Manager 正在複查文件庫...")
            for tc in response.tool_calls:
                if tc["name"] == "read_knowledge_base":
                    try:
                        res = rag_tool.invoke("詳細列出文件中的關鍵數據、金額、年份與結論")
                        rag_context += f"\n【RAG 補充資訊】:\n{res}\n"
                    except: pass
    except Exception:
        rag_context = ""

    # [Rate Limit 保護] 延長休息時間至 10 秒
    time.sleep(10)

    # 2. 初版草稿 (Drafting)
    print("  -> 生成初版大綱...")
    # [優化] 更明確的層級指令
    draft_system = """
    請根據現有資訊規劃 PPT 大綱。
    
    【結構規範】：
    1. **ContentItem 層級控制 (Level)**：請善用多層次縮排來呈現邏輯。
       - `level=0`: 核心論點 (Main Bullet Point)。
       - `level=1`: 支撐數據、詳細說明 (Supporting Detail)。
       - `level=2`: 具體範例、引用來源 (Example/Source)。
       *適當的縮排能讓簡報更專業。*
       
    2. **欄位控制 (Column)**：
       - `column=0`: 左欄 (預設)。
       - `column=1`: 右欄 (僅用於 two_column 版型)。

    3. **數據精確**：若有數據，必須填入，不可遺漏。
    4. **分頁**：若單頁內容超過 7 點，請主動拆成 (1/2), (2/2) 兩頁。
    """
    
    base_msg = f"【RAG】:{rag_context}\n【Chat History】:{state.chat_history}\n【Req】:{state.user_request}"
    structured_llm = llm.with_structured_output(PresentationOutline)
    
    try:
        draft = structured_llm.invoke([
            SystemMessage(content=draft_system),
            HumanMessage(content=base_msg)
        ])
    except Exception as e:
        print(f"Draft Error: {e}")
        return {"outline": None}

    if not draft: return {"outline": None}

    # [Rate Limit 保護] 生成大綱很耗 Token，休息久一點
    time.sleep(10)

    # 3. 自我反思 (Reflection)
    print("  -> 進行自我反思與缺口檢查...")
    reflection_prompt = f"""
    請檢視這份大綱：{draft.model_dump_json()}
    
    【檢查】：是否有缺乏數據佐證的論點？是否有模糊不清的描述？
    
    若有缺漏，請產生一個 RAG 搜尋 Query。
    若完美，回傳 "PERFECT"。
    """
    reflect_res = llm.invoke(reflection_prompt).content.strip()

    if "PERFECT" not in reflect_res and len(reflect_res) < 150:
        print(f"  -> 發現缺口，補強搜尋: {reflect_res}")
        
        # [Rate Limit 保護]
        time.sleep(5)
        
        try:
            supp_info = rag_tool.invoke(reflect_res)
            
            print("  -> 根據新資訊修訂大綱...")
            # [Rate Limit 保護] 最後一次生成前再休息一下
            time.sleep(10)
            
            refine_system = "你是追求完美的總監。請根據補強資訊修訂大綱，將數據填補進去。請維持良好的 0-1-2 層級結構。"
            final_outline = structured_llm.invoke([
                SystemMessage(content=refine_system),
                HumanMessage(content=f"【初版】:{draft.model_dump_json()}\n【補強】:{supp_info}")
            ])
            return {"outline": final_outline}
        except Exception as e:
            print(f"Refine Error: {e}")
            return {"outline": draft}
            
    return {"outline": draft}