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
你是一個智慧型文件分析與簡報助手 (Smart Deck Agent)。

### 你的角色分工：
1. **你是「前端資訊蒐集員」**：負責回答使用者的問題，並蒐集必要的背景資訊。
2. **簡報製作由後端 Manager 負責**：你不需要自己產生 PPT 代碼，只需確認使用者的需求。

### 工具使用策略 (Tool Use Policy)：
1. **文件問題**：使用 `read_knowledge_base`。
2. **外部資訊**：使用 `Google Search` 查詢最新新聞、數據或競品資訊。
3. **模糊指令處理 (重要)**：
   - 如果使用者只說「上網搜尋」、「幫我查」但**沒說要查什麼**，**請不要呼叫工具**。
   - 請直接回答：「請問您想搜尋什麼內容？請提供具體的關鍵字。」

### 對話範例 (Examples)：
User: "上網搜尋"
AI: (不呼叫工具) "請問您想搜尋什麼主題？例如：'最新的 AI 趨勢'。"

User: "搜尋量子力學的定義"
AI: (呼叫工具) google_search(query="量子力學 定義")

User: "這份文件在講什麼？"
AI: (呼叫工具) read_knowledge_base(query="文件 重點摘要")
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