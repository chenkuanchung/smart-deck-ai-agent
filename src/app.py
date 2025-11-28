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
# [新增 import] remove_file_from_db
from src.tools.rag import ingest_file, rag_tool, reset_vector_store, remove_file_from_db
from src.tools.search import search_tool
from src.graph import agent_workflow
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# System Prompt
SYSTEM_PROMPT = """
你是一個智慧型文件分析與簡報助手 (Smart Deck Agent)。
1. **文件優先**：使用者問總結或內容時，優先查 `read_knowledge_base`。
2. **工具策略**：需要外部資訊才查 `Google Search`。
3. **禁止反問**：不要問使用者檔名，直接搜尋關鍵字。
"""

# 1. Init
st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")
try:
    Config.validate()
except Exception as e:
    st.error(f"環境設定錯誤: {e}")
    st.stop()

# 2. LLM
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

# 用來追蹤「目前資料庫裡有哪些檔案」
if "db_files" not in st.session_state:
    st.session_state.db_files = set() 

# 4. 側邊欄 (智慧同步區)
with st.sidebar:
    st.header("📂 資料來源")
    
    # accept_multiple_files=True 讓我們可以一次管理多個檔案，也方便做刪除偵測
    uploaded_files = st.file_uploader(
        "選擇檔案 (PDF/TXT)", 
        type=["pdf", "txt"], 
        accept_multiple_files=True
    )
    
    # --- [核心邏輯] 自動同步機制 ---
    if uploaded_files is not None:
        # 1. 取得目前 UI 上的檔案名稱清單
        current_ui_filenames = {f.name for f in uploaded_files}
        
        # 2. 找出「新上傳」的 (UI 有，但 DB 沒記錄)
        new_files = [f for f in uploaded_files if f.name not in st.session_state.db_files]
        
        # 3. 找出「被刪除」的 (DB 有記錄，但 UI 沒有了)
        removed_files = st.session_state.db_files - current_ui_filenames
        
        # 處理新檔案
        for file in new_files:
            with st.spinner(f"正在處理新檔案：{file.name}..."):
                temp_path = os.path.join(os.getcwd(), file.name)
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

        # 處理被刪除的檔案
        for filename in removed_files:
            with st.spinner(f"正在移除檔案：{filename}..."):
                msg = remove_file_from_db(filename)
                st.warning(msg)
                st.session_state.db_files.remove(filename)
                st.session_state.messages.append(
                    HumanMessage(content=f"[系統通知] 我移除了 '{filename}'，請不要再參考它的內容。")
                )
    
    st.divider()
    
    # 清空按鈕
    if st.button("🗑️ Reset 全部", type="secondary"):
        reset_vector_store()
        st.session_state.db_files = set()
        st.session_state.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        st.rerun()

    st.header("🚀 生成行動")
    if st.button("✨ 生成 PPT 簡報", type="primary"):
        if not st.session_state.messages:
            st.warning("請先對話")
        else:
            with st.status("🤖 AI 團隊工作中...", expanded=True) as status:
                chat_history = ""
                for msg in st.session_state.messages:
                    if isinstance(msg, HumanMessage):
                        chat_history += f"User: {msg.content}\n"
                    elif isinstance(msg, AIMessage) and msg.content:
                        chat_history += f"AI: {msg.content}\n"
                
                status.write("🧠 Manager 規劃大綱...")
                initial_state = {"user_request": "製作簡報", "chat_history": chat_history}
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
                        
                        if name == "read_knowledge_base":
                            status_box.info(f"📚 查閱資料庫: {args.get('query')}")
                        elif name == "google_search":
                            status_box.info(f"🌐 搜尋網路: {args.get('query')}")
                        
                        tool = tool_map.get(name)
                        output = tool.invoke(next(iter(args.values())) if args else "") if tool else "Error"
                        
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