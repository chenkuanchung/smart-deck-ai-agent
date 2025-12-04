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
    investigation_system = """
    你是一位簡報架構師。請先分析使用者的需求與對話歷史，並呼叫 `read_knowledge_base` 進行全面調查。
    
    【調查重點】：
    1. **全盤理解**：不僅是數據，更要理解文件的主旨、核心論述與邏輯脈絡。
    2. **意圖對焦**：根據 User Request 與 Chat History，判斷使用者想強調什麼？是否需要將外部概念與文件內容結合？
    3. **數據保留 (Critical)**：簡報必須專業，請務必精確提取文件中的關鍵數據（例如: 營收、成長率、年份、具體金額）、專業結論與圖表描述。
    """
    # 注入 Chat History，讓 Manager 讀得懂上下文
    context_msg = f"Chat History:\n{state.chat_history}\n\nUser Request:\n{state.user_request}"

    try:
        response = llm_with_tools.invoke([
            SystemMessage(content=investigation_system),
            HumanMessage(content=context_msg)
        ])
        
        rag_context = ""
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("  -> Manager 正在複查文件庫...")
            for tc in response.tool_calls:
                if tc["name"] == "read_knowledge_base":
                    try:
                        # 使用 LLM 智慧生成的 Query，不再強制覆蓋
                        # 這樣 LLM 就可以根據對話，查出「數據」以外的「觀點」或「整合資訊」
                        query = tc["args"].get("query")

                        if not query:
                            query = "詳細列出文件中的關鍵數據、金額、年份與結論" # Fallback
                        
                        print(f"     [Query]: {query}") # Debug 看一下它查了什麼
                        res = rag_tool.invoke(query)
                        rag_context += f"\n【RAG 補充資訊 (Query: {query})】:\n{res}\n"
                    except Exception as e:
                        print(f"RAG Error: {e}")
                        pass
    except Exception as e:
        print(f"Investigation Error: {e}")
        rag_context = ""

    # [Rate Limit 保護] 延長休息時間至 5 秒
    time.sleep(5)

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
    time.sleep(5)

    # 3. 自我反思 (Reflection)
    print("  -> 進行自我反思與缺口檢查...")
    reflection_prompt = f"""
    請檢視這份大綱：{draft.model_dump_json()}
    
    【檢查1】：是否有缺乏數據佐證的論點？是否有模糊不清的描述？ 若有缺漏，請產生一個 RAG 搜尋 Query。
    【檢查2】：是否版面或版面內容不合理的地方? 例如: 不同頁面但重複論述、標題太長、標題與內文重複...等。
    
    若有缺點，請直接回傳「搜尋關鍵字」或「具體修改建議」。
    若完美，回傳 "PERFECT"。
    """
    reflect_res = llm.invoke(reflection_prompt).content.strip()

    if "PERFECT" not in reflect_res and len(reflect_res) < 200: 
        print(f"  -> 發現缺口或建議: {reflect_res}")
        
        # [Rate Limit 保護]
        time.sleep(5)
        
        try:
            # 嘗試搜尋 (針對數據缺口)
            # 即使 reflect_res 是 "修改版面建議"，丟給 RAG 跑一次也無妨，頂多找不到東西回傳空字串
            supp_info = rag_tool.invoke(reflect_res)
        except:
            supp_info = "無外部搜尋結果"

        print("  -> 根據新資訊修訂大綱...")
        time.sleep(5)
        
        # [修改] System Prompt：明確授權它可以修結構
        refine_system = """
        你是追求完美的總監。請根據【修改建議】與【補強資訊】修訂大綱。
        1. 若有數據缺口，請根據補強資訊填補。
        2. 若有版面結構建議 (如重複、太長)，請務必執行修正。
        請維持良好的 0-1-2 層級結構。
        """
        
        try:
            # 把 reflect_res (建議本體) 也傳進去，這樣 AI 才看得到 "要改哪裡"
            final_outline = structured_llm.invoke([
                SystemMessage(content=refine_system),
                HumanMessage(content=f"【初版】:{draft.model_dump_json()}\n【修改建議 (Query/Instruction)】:{reflect_res}\n【補強資訊 (RAG Result)】:{supp_info}")
            ])
            return {"outline": final_outline}
        except Exception as e:
            print(f"Refine Error: {e}")
            return {"outline": draft}
            
    return {"outline": draft}