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

# Import
from src.config import Config
from src.tools.rag import ingest_file, rag_tool, reset_vector_store, remove_file_from_db
from src.tools.search import search_tool
from src.graph import agent_workflow
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# --- System Prompt (前端 Chat Agent 專用) ---
# [關鍵優化] 加入「對話範例 (Few-Shot)」教導 Agent 正確的工具使用時機
SYSTEM_PROMPT = """
你不再只是一個簡單的問答機器人，你是 **Smart Deck 團隊的「首席研究分析師 (Lead Research Analyst)」**。

### 你的核心目標：
你的工作是為後端的 Manager 提供**「高資訊密度 (High Information Density)」**的簡報素材。
使用者告訴你主題（例如「生成式 AI」），你不能只給定義。你必須挖掘出能支撐一份 10 頁專業簡報的深度內容。

### 你的思考與行動準則 (Research Protocol)：
1. **拒絕淺層資訊**：不要只給「是什麼」，要給「為什麼」、「多少錢」、「成長率多少」、「誰在做」。
2. **數據優先 (Data First)**：簡報需要說服力。搜尋時優先尋找：
   - **具體數字** (Market Size, CAGR, Revenue)
   - **時間戳記** (2024 Q3 最新報告, 2025 預測)
   - **具體案例** (Company Use Cases, Competitor Analysis)
3. **多角度拆解 (Multi-hop Reasoning)**：
   - 當使用者說「我要做關於 X 的簡報」時，不要只搜尋 "X"。
   - **你必須主動拆解搜尋**（即使你需要多呼叫幾次 google_search）：
     - 搜尋 1: "X 2024 市場規模與成長率"
     - 搜尋 2: "X 的主要應用場景與案例"
     - 搜尋 3: "X 的技術挑戰與缺點"
     - 搜尋 4: "X 的領導廠商與競品比較"

### 工具使用策略 (Tool Use Policy)：
- **read_knowledge_base**: 當使用者問及內部文件、上傳的 PDF 細節時使用。
- **google_search**: 
   - **不要只搜名詞**。例如不要搜 "AI"，要搜 "AI 2024 trends statistical report"。
   - 如果第一次搜尋結果太過空泛，**請主動換個關鍵字再搜一次**，直到你收集到足夠的數據。

### 應對模糊指令：
- 若使用者只說「幫我查」，請反問：「我們要聚焦在哪個面向？例如技術架構、市場分析，還是競爭對手？」
- 但若使用者說「我要做關於 [主題] 的簡報」，**請直接啟動全方位搜尋**，不需要再問使用者，展現你的主動性。

### 對話範例 (Few-Shot Examples)：

User: "我想做一份關於電動車電池的簡報"
AI Thought: 使用者要簡報，我不能只給定義。我需要市場數據、技術分類(固態vs鋰離子)、主要廠商。
AI Action: 
   1. google_search("EV battery market size 2024 2030 CAGR")
   2. google_search("Solid-state battery vs Lithium-ion pros cons")
   3. google_search("Top EV battery manufacturers market share 2024")
AI Response: (彙整所有數據，提供結構化的回答，包含數據來源與年份)

User: "搜尋這份文件的重點"
AI: (呼叫工具) read_knowledge_base(query="文件 核心結論 與 關鍵數據")
"""

# 1. Init
st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")
try:
    Config.validate()
except Exception as e:
    st.error(f"環境設定錯誤: {e}")
    st.stop()

# --- 初始化檢查邏輯 (Reset on Refresh) ---
if "app_initialized" not in st.session_state:
    print("🔄 偵測到新 Session 或頁面刷新，正在執行環境重置...")
    reset_vector_store()
    st.session_state.app_initialized = True

# 2. LLM (Chat Agent - 擁有所有工具)
# 前端 Chat Agent 還是需要 RAG，這樣使用者問「PDF裡寫什麼？」它才答得出來
tools = [rag_tool, search_tool]
tool_map = {"read_knowledge_base": rag_tool, "google_search": search_tool}

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST,
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.3
)
llm_with_tools = llm.bind_tools(tools)

# 3. Session State
if "messages" not in st.session_state:
    st.session_state.messages = [SystemMessage(content=SYSTEM_PROMPT)]

if "db_files" not in st.session_state:
    st.session_state.db_files = set() 

if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# 4. 側邊欄
with st.sidebar:
    st.header("📂 資料來源")
    
    uploaded_files = st.file_uploader(
        "選擇檔案 (PDF/TXT)", 
        type=["pdf", "txt"], 
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.file_uploader_key}"
    )
    
    if uploaded_files is not None:
        current_ui_filenames = {f.name for f in uploaded_files}
        new_files = [f for f in uploaded_files if f.name not in st.session_state.db_files]
        removed_files = st.session_state.db_files - current_ui_filenames
        
        for file in new_files:
            with st.spinner(f"正在處理新檔案：{file.name}..."):
                temp_path = os.path.join(Config.UPLOAD_DIR, file.name)
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                
                result = ingest_file(temp_path)
                if "成功" in result:
                    st.success(result)
                    st.session_state.db_files.add(file.name)
                    st.session_state.messages.append(
                        HumanMessage(content=f"[系統通知] 我上傳了 '{file.name}'。")
                    )
                else:
                    st.error(result)

        for filename in removed_files:
            with st.spinner(f"正在移除檔案：{filename}..."):
                msg = remove_file_from_db(filename)
                st.warning(msg)
                st.session_state.db_files.remove(filename)
                st.session_state.messages.append(
                    HumanMessage(content=f"[系統通知] 我移除了 '{filename}'，請不要再參考它的內容。")
                )
    
    st.divider()
    
    if st.button("🗑️ Reset 全部", type="secondary"):
        reset_vector_store()
        st.session_state.db_files = set()
        st.session_state.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        st.session_state.file_uploader_key += 1
        st.rerun()

    st.header("🚀 生成行動")
    if st.button("✨ 生成 PPT 簡報", type="primary"):
        with st.status("🤖 AI 團隊工作中...", expanded=True) as status:
            chat_history = ""
            # 收集 Chat Agent 辛苦搜尋來的資訊
            for msg in st.session_state.messages:
                if isinstance(msg, HumanMessage):
                    chat_history += f"User: {msg.content}\n"
                elif isinstance(msg, AIMessage) and msg.content:
                    chat_history += f"AI: {msg.content}\n"
            
            status.write("🧠 Manager 正在分析文件並規劃架構...")
            
            # 直接呼叫 Graph，讓 Manager 自己去決定要不要讀檔
            initial_state = {"user_request": "請製作一份簡報", "chat_history": chat_history}
            final_state = agent_workflow.invoke(initial_state)
            
            status.write("✍️ Writer 撰寫與排版...")
            if final_state.get("final_file_path"):
                ppt_path = final_state["final_file_path"]
                file_name = os.path.basename(ppt_path)
                with open(ppt_path, "rb") as f:
                    st.download_button("📥 下載 PPT", f, file_name)
                status.update(label="✅ 完成！", state="complete")
            else:
                status.error("生成失敗")

# 5. 主聊天區
st.title("💬 Smart Deck Agent")

for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.markdown(msg.content)

if prompt := st.chat_input("輸入訊息..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_box = st.empty()
        with st.spinner("思考中..."):
            try:
                response = llm_with_tools.invoke(st.session_state.messages)
                st.session_state.messages.append(response)

                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        name = tool_call["name"]
                        args = tool_call["args"]
                        call_id = tool_call["id"]
                        
                        search_term = args.get("query")
                        if name == "read_knowledge_base":
                            status_box.info(f"📚 查閱資料庫: {search_term}")
                        elif name == "google_search":
                            status_box.info(f"🌐 搜尋網路: {search_term}")
                        
                        tool = tool_map.get(name)
                        output = "Error: Tool not found"
                        if tool:
                            query_val = search_term if search_term else "總結" 
                            try:
                                output = tool.invoke(query_val)
                            except Exception as e:
                                output = f"Error: {e}"
                        
                        st.session_state.messages.append(
                            ToolMessage(content=str(output), tool_call_id=call_id, name=name)
                        )
                    
                    final_res = llm_with_tools.invoke(st.session_state.messages)
                    st.markdown(final_res.content)
                    st.session_state.messages.append(final_res)
                    status_box.empty()
                else:
                    st.markdown(response.content)
            except Exception as e:

                st.error(f"Error: {e}")
