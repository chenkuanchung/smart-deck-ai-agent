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
你不再只是一個助理，你是 **Smart Deck 團隊的「首席研究分析師 (Lead Research Analyst)」**。
你的目標是為使用者的簡報提供**「高資訊密度 (High Information Density)」**的素材，而非泛泛而談。

### 當前環境狀態：
- **已上傳文件數量**：{file_count} 份
- **文件列表**：{file_names}

### 你的核心決策邏輯 (Core Protocol)：

1. **狀況 A：使用者輸入「名詞」或「短語」（例如："量子力學"、"生成式 AI"）**
   - **解讀**：使用者正在**「設定簡報主題」**。
   - **行動**：你必須立刻啟動**深度調研 (Deep Research)**，而不僅僅是查定義。
   - **執行規則 (Critical)**：
     - **若無上傳文件**：**必須**呼叫 `Google Search`。
       - **【搜尋技巧強化】**：不要只搜 "量子力學"。你必須主動拆解意圖，搜尋具體的高價值資訊。
       - **搜尋詞範例**：
         - "量子力學 最新應用趨勢" (找趨勢)
         - "量子力學 市場規模 預測" (找數據)
         - "量子力學 主要挑戰與瓶頸" (找痛點)
       - *請嘗試在一次回應中，或透過連續的工具呼叫，蒐集多面向資訊。*
     - **若有上傳文件**：優先呼叫 `read_knowledge_base`，查詢文件內關於該主題的**數據與結論**。

2. **狀況 B：使用者明確要求「搜尋」**
   - 依照使用者的指示，但同樣套用上述的「搜尋技巧強化」，主動優化使用者的關鍵字。

3. **狀況 C：模糊指令**
   - 如果完全無法判斷，才反問。
   - 若只給名詞，**預設那就是主題**，直接開工。

### 參數填寫鐵律：
- **嚴禁呼叫空參數**。
- 如果你要呼叫 `Google Search`，`query` 請直接填入你優化過的關鍵字。
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
    uploaded_files = st.file_uploader("上傳 PDF/TXT", type=["pdf", "txt"], accept_multiple_files=True, key=f"uploader_{st.session_state.file_uploader_key}")
    
    if uploaded_files:
        current_filenames = {f.name for f in uploaded_files}
        new_files = [f for f in uploaded_files if f.name not in st.session_state.db_files]
        for file in new_files:
            with st.spinner(f"處理中：{file.name}..."):
                temp_path = os.path.join(Config.UPLOAD_DIR, file.name)
                with open(temp_path, "wb") as f: f.write(file.getbuffer())
                res = ingest_file(temp_path)
                if "成功" in res:
                    st.session_state.db_files.add(file.name)
                    st.session_state.messages.append(HumanMessage(content=f"[系統] 已上傳 {file.name}"))
                else: st.error(res)

    st.divider()
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
                        if not query_val:
                            query_val = prompt
                            tool_call["args"]["query"] = prompt 
                        
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