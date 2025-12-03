# src/app.py
import streamlit as st
import os
import sys

# 路徑修正
current_file_path = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import Config
from src.tools.rag import ingest_file, rag_tool, reset_vector_store, remove_file_from_db
from src.tools.search import search_tool
from src.graph import agent_workflow
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# --- [UX 優化] 工具名稱對照表 ---
TOOL_DISPLAY_NAMES = {
    "google_search": "🌏 正在搜尋網路... (Web Research)",
    "read_knowledge_base": "📚 正在分析內部文件 (Document Analysis)"
}

# --- System Prompt (最強合體版：深度搜尋 + 意圖導向) ---
SYSTEM_PROMPT_TEMPLATE = """
你現在是 Smart Deck 團隊的 **「首席策略分析師 (Lead Strategy Analyst)」**。
你不僅僅是一個搜尋工具，你是使用者的**「簡報顧問」**與**「前期策劃」**。

你的終極任務：協助使用者透過對話，將模糊的想法轉化為**「高資訊密度、邏輯嚴密」**的簡報素材，最後交棒給 Manager (規劃) 與 Writer (排版) 進行製作。

---

### 🌟 當前環境感知 (Context Awareness)
- **已上傳文件**：{file_count} 份 ({file_names})
- **你的下游夥伴**：
  1. **Manager**：負責寫大綱。它非常喜歡「具體數據」、「年份」、「金額」與「明確結論」。
  2. **Writer**：負責排版。僅支援PPT版型：`title`, `section`, `content`, `two_column`。

---

### 🧠 你的思考與行動協議 (Cognitive Protocol)

當收到使用者訊息時，請依照以下步驟思考，**不要像機器人一樣直接執行**：

#### Step 1: 意圖偵測 (Intent Detection)
判斷使用者現在想要什麼？
- **A. 探索/發散**：只給一個名詞（如 "AI"）。 -> **行動**：你需要引導與收斂。
- **B. 驗證/查詢**：問具體問題（如 "台積電 2024 Q3 營收"）。 -> **行動**：精準調研。
- **C. 比較/分析**：問差異（如 "油車 vs 電車"）。 -> **行動**：尋找對比維度（成本、環保、效能）。
- **D. 閒聊/打招呼**： -> **行動**：展現專業熱情，引導至簡報主題。

#### Step 2: 資訊模糊度檢查 (Ambiguity Check) **(關鍵！)**
- **若指令太模糊**（例如只說 "做一份簡報" 或 "市場分析"）：
  - 🛑 **STOP！不要搜尋！**
  - 🗣️ **Action**：請反問使用者。「您想聚焦在哪個特定市場？主要受眾是投資人還是技術人員？」
  - *展現你的顧問價值，幫助使用者釐清需求。*

- **若指令夠清晰**：
  - ✅ **GO！啟動工具。**

#### Step 3: 工具調度策略 (Tool Strategy)
- **優先級**：總是先問自己「這資料是否在已上傳的文件 (`read_knowledge_base`) 裡？」
  - 若有上傳文件 -> **優先查文件**，並引用文件內容。
  - 若文件無資料/資料過時 -> **立刻切換** `Google Search` 找外部最新資訊。
- **搜尋策略 (Search Tactics)**：
  - 1. **識別搜尋關鍵字**： 不要用使用者的原話搜尋。請將其轉化為**「高價值關鍵字」**。
  - 2. **多角度關鍵字 (Multi-Angle Keywords)**：
     - 如果主題可能有不同稱呼，**請一次產生 2~3 個不同的搜尋工具呼叫 (Parallel Function Calling)**。
     - *範例*：若使用者問 "NotebookLM 簡報功能"，你應該同時呼叫三次搜尋：
       - Query 1: `"NotebookLM audio overview features"` (官方可能用語)
       - Query 2: `"Google NotebookLM slide deck"` (常見稱呼)
       - Query 3: `"Google NotebookLM latest updates"` (廣泛資訊)
  3. **針對性**：若為了比較，搜尋 `"A vs B features"`, `"A vs B pricing"`。

#### Step 4: 回應與輸出 (Response)
- **不要只丟連結**。請將搜尋到的資訊**「消化」**過。

---

### ⚠️ 絕對禁區 (Strict Rules)
1. **嚴禁呼叫空參數**：呼叫工具時，`query` 必須填入具體內容。
2. **嚴禁瞎掰**：RAG 找不到就說找不到，然後主動建議去 Google 搜。
3. **保持對話記憶**：若使用者說「把剛剛查到的 A 和 B 整合」，請根據 Chat History 執行，不要問 A 和 B 是什麼。

現在，請以一位專業、主動且具備洞察力的分析師身分開始互動。
"""

# Init
st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")
try: Config.validate()
except Exception as e: st.error(f"環境設定錯誤: {e}"); st.stop()

if "app_initialized" not in st.session_state:
    reset_vector_store()
    st.session_state.app_initialized = True

# LLM
tools = [rag_tool, search_tool]
tool_map = {"read_knowledge_base": rag_tool, "google_search": search_tool}
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST, google_api_key=Config.GOOGLE_API_KEY, temperature=0.7
)
llm_with_tools = llm.bind_tools(tools)

# Session
if "messages" not in st.session_state: st.session_state.messages = []
if "db_files" not in st.session_state: st.session_state.db_files = set() 
if "file_uploader_key" not in st.session_state: st.session_state.file_uploader_key = 0

# Sidebar
with st.sidebar:
    st.header("📂 資料來源")
    uploaded_files = st.file_uploader(
        "上傳 PDF/TXT", 
        type=["pdf", "txt"], 
        accept_multiple_files=True, 
        key=f"uploader_{st.session_state.file_uploader_key}"
    )
    
    # 1. 建立當前檔案清單
    if uploaded_files is None:
        uploaded_files = []
    current_filenames = {f.name for f in uploaded_files}

    # 2. 處理新增檔案 (New Files)
    new_files = [f for f in uploaded_files if f.name not in st.session_state.db_files]
    for file in new_files:
        with st.spinner(f"處理中：{file.name}..."):
            temp_path = os.path.join(Config.UPLOAD_DIR, file.name)
            if not os.path.exists(Config.UPLOAD_DIR):
                os.makedirs(Config.UPLOAD_DIR)
                
            with open(temp_path, "wb") as f: f.write(file.getbuffer())
            
            res = ingest_file(temp_path)
            
            if "✅" in res:
                st.session_state.db_files.add(file.name)
                st.session_state.messages.append(HumanMessage(content=f"[系統] {res}"))
                # [關鍵修正] 在側邊欄顯示綠色成功訊息
                st.success(res) 
            else: 
                st.error(res)

    # 3. 處理移除檔案 (Removed Files)
    removed_files = st.session_state.db_files - current_filenames
    
    if removed_files:
        for filename in removed_files:
            res = remove_file_from_db(filename)
            st.session_state.db_files.remove(filename)
            st.session_state.messages.append(HumanMessage(content=f"[系統] {res}"))
            # 在側邊欄顯示刪除訊息
            st.success(res) 

    st.divider()
    
    # Reset 按鈕
    if st.button("🗑️ Reset", type="secondary"):
        reset_vector_store()
        st.session_state.db_files = set()
        st.session_state.messages = []
        st.session_state.file_uploader_key += 1
        st.rerun()

    if st.button("✨ 生成 PPT", type="primary"):
        with st.status("🤖 AI 團隊工作中...", expanded=True) as status:
            chat_history = "\n".join([f"{type(m).__name__}: {m.content}" for m in st.session_state.messages])
            
            status.write("🧠 Manager: 正在規劃簡報架構...")
            final_state = agent_workflow.invoke({"user_request": "製作簡報", "chat_history": chat_history})
            
            status.write("✍️ Writer: 正在排版與製作投影片...")
            if final_state.get("final_file_path"):
                with open(final_state["final_file_path"], "rb") as f:
                    st.download_button("📥 下載 PPT", f, os.path.basename(final_state["final_file_path"]))
                status.update(label="✅ 完成！", state="complete")
            else: status.error("生成失敗，請檢查 Log。")

# Chat Interface
st.title("💬 Smart Deck Agent")

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"): st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"): st.markdown(msg.content)

if prompt := st.chat_input("輸入訊息 (例如：想了解的主題、上傳文件後分析)..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        status_box = st.empty()
        
        with st.spinner("思考中..."):
            try:
                # 1. 注入動態 Prompt (告知檔案狀態)
                file_count = len(st.session_state.db_files)
                file_names = ", ".join(st.session_state.db_files) if file_count > 0 else "無"
                
                dynamic_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    file_count=file_count,
                    file_names=file_names
                )
                
                messages_to_send = [SystemMessage(content=dynamic_system_prompt)] + st.session_state.messages
                
                # 2. 第一次呼叫 LLM
                response = llm_with_tools.invoke(messages_to_send)
                st.session_state.messages.append(response)

                # 3. 工具迴圈 (蒐集資訊)
                while response.tool_calls:
                    for tool_call in response.tool_calls:
                        name = tool_call["name"]
                        args = tool_call["args"]
                        query_val = args.get("query", "")
                        
                        # [防呆] 若 LLM 給空參數，直接用使用者的 Prompt (即主題)
                        # if not query_val:
                        #     query_val = prompt
                        #     tool_call["args"]["query"] = prompt 
                        
                        # [UI] 顯示親切名稱 + 查詢內容
                        display_name = TOOL_DISPLAY_NAMES.get(name, f"🔧 {name}")
                        status_box.info(f"{display_name}：{query_val}")
                        
                        # 執行工具
                        tool = tool_map.get(name)
                        output = tool.invoke(query_val) if tool else "Error: Tool not found"
                        
                        st.session_state.messages.append(
                            ToolMessage(content=str(output), tool_call_id=tool_call["id"], name=name)
                        )
                    
                    # 再次呼叫 LLM (帶著搜尋結果)
                    messages_to_send = [SystemMessage(content=dynamic_system_prompt)] + st.session_state.messages
                    response = llm_with_tools.invoke(messages_to_send)
                    st.session_state.messages.append(response)
                
                status_box.empty()
                st.markdown(response.content)

            except Exception as e:

                st.error(f"Error: {e}")
