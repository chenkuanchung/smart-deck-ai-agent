# src/app.py
import streamlit as st
import os
import sys

# --- 路徑修正 ---
current_file_path = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import
from src.config import Config
from src.tools.rag import ingest_file, rag_tool
from src.tools.search import search_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# --- NotebookLM 風格 System Prompt ---
SYSTEM_PROMPT = """
你是一個智慧型文件分析與簡報助手 (Smart Deck Agent)。你的核心任務是協助使用者理解他們上傳的文件 (PDF/TXT)，並根據這些內容生成洞察。

### 你的核心行為準則 (Core Directives)：

1.  **文件優先 (Document First)**：
    -   使用者上傳了文件到你的知識庫中。
    -   **預設假設**：使用者的問題（如「總結內容」、「重點是什麼」）**絕對**是指向這些文件的。
    -   **行動**：遇到上述問題，你必須**立刻、毫不猶豫地**呼叫 `read_knowledge_base` 工具。

2.  **禁止反問檔名**：
    -   使用者通常不記得檔名。直接根據使用者的意圖生成搜尋關鍵字（如「摘要」、「結論」）。

3.  **工具使用策略**：
    -   **read_knowledge_base**：這是你的主要武器。只要問題像是在問內部資訊，就用它。
    -   **google_search**：只有在使用者明確要求「上網查」或問「最新時事」時使用。
"""

# --- 1. 初始化設定 ---
st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")

try:
    Config.validate()
except Exception as e:
    st.error(f"環境設定錯誤: {e}")
    st.stop()

# --- 2. 初始化 LLM ---
tools = [rag_tool, search_tool]
tool_map = {
    "read_knowledge_base": rag_tool,
    "google_search": search_tool
}

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST,
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.3
)
llm_with_tools = llm.bind_tools(tools)

# --- 3. Session State 管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# --- 4. 側邊欄 (上傳區) ---
with st.sidebar:
    st.header("📂 資料來源")
    uploaded_file = st.file_uploader("選擇檔案", type=["pdf", "txt"])
    
    if uploaded_file and uploaded_file.name not in st.session_state.uploaded_files:
        with st.spinner("正在讀取並向量化文件..."):
            temp_path = os.path.join(os.getcwd(), uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            result = ingest_file(temp_path)
            
            if "成功" in result:
                st.success(result)
                st.session_state.uploaded_files.append(uploaded_file.name)
                
                # [關鍵修正] 使用 HumanMessage 取代 SystemMessage，避免 API 報錯
                st.session_state.messages.append(
                    HumanMessage(content=f"[系統通知] 我剛剛上傳了一份文件：'{uploaded_file.name}'。請將其納入知識庫並隨時準備回答相關問題。")
                )
            else:
                st.error(result)

    st.divider()
    st.header("🚀 生成行動")
    if st.button("✨ 生成 PPT 簡報", type="primary"):
        st.info("功能開發中...")

# --- 5. 主聊天介面 ---
st.title("💬 Smart Deck Agent")
st.caption("協助您分析企業內部文件，並自動生成專業簡報。")

# 顯示歷史訊息
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# 處理輸入
if prompt := st.chat_input("輸入訊息..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_container = st.empty()
        with st.spinner("正在思考..."):
            try:
                # 呼叫 LLM
                response = llm_with_tools.invoke(st.session_state.messages)
                st.session_state.messages.append(response)

                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["name"]
                        tool_args = tool_call["args"]
                        call_id = tool_call["id"]
                        
                        # UX: 顯示狀態
                        if tool_name == "read_knowledge_base":
                            q = tool_args.get('query', '摘要')
                            status_container.info(f"📚 正在閱讀文件庫... (查詢: '{q}')")
                        elif tool_name == "google_search":
                            q = tool_args.get('query', '...')
                            status_container.info(f"🌐 正在搜尋網路... (查詢: '{q}')")
                        
                        selected_tool = tool_map.get(tool_name)
                        tool_output = f"工具 {tool_name} 執行失敗"
                        if selected_tool:
                            try:
                                arg_value = next(iter(tool_args.values())) if tool_args else ""
                                tool_output = selected_tool.invoke(arg_value)
                            except Exception as e:
                                tool_output = f"Error: {e}"
                        
                        # 將結果回傳
                        st.session_state.messages.append(
                            ToolMessage(content=str(tool_output), tool_call_id=call_id, name=tool_name)
                        )
                    
                    # 再次呼叫 LLM
                    final_response = llm_with_tools.invoke(st.session_state.messages)
                    st.markdown(final_response.content)
                    st.session_state.messages.append(final_response)
                    status_container.empty()
                else:
                    st.markdown(response.content)
            
            except Exception as e:
                st.error(f"發生錯誤: {e}")