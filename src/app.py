# src/app.py
import streamlit as st
import os

# 載入我們的模組
from src.config import Config
from src.tools.rag import ingest_file, rag_tool
from src.tools.search import search_tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

# --- 1. 初始化設定 ---
st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")

# 確保環境變數已載入
try:
    Config.validate()
except Exception as e:
    st.error(f"環境設定錯誤: {e}")
    st.stop()

# --- 2. 初始化 LLM 與工具綁定 (真正的 AI 大腦) ---

# 定義工具箱：告訴 Gemini 它有哪些超能力
tools = [rag_tool, search_tool]

# 建立工具對照表 (用於程式執行)
tool_map = {
    "read_knowledge_base": rag_tool,
    "google_search": search_tool
}

# 初始化 LLM
# 這裡建議使用 MODEL_SMART (Pro) 或至少 Flash，因為 Function Calling 需要較好的推理能力
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST,  # 建議用 Flash 保持速度，若發現判斷不準可改用 SMART
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.7
)

# [關鍵技術] Bind Tools: 將工具綁定給模型
# 這一步之後，Gemini 就知道自己可以呼叫這些函式了
llm_with_tools = llm.bind_tools(tools)

# --- 3. Session State 管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

# --- 4. 側邊欄 (上傳區) ---
with st.sidebar:
    st.header("📂 資料來源")
    st.caption("請先上傳文件，讓 AI 擁有內部知識。")
    
    uploaded_file = st.file_uploader("選擇檔案 (PDF/TXT)", type=["pdf", "txt"])
    
    if uploaded_file and uploaded_file.name not in st.session_state.uploaded_files:
        with st.spinner("正在讀取並向量化文件..."):
            temp_path = os.path.join(os.getcwd(), uploaded_file.name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 呼叫 RAG Ingest
            result = ingest_file(temp_path)
            
            if "成功" in result:
                st.success(result)
                st.session_state.uploaded_files.append(uploaded_file.name)
            else:
                st.error(result)

    st.divider()
    
    st.header("🚀 生成行動")
    if st.button("✨ 生成 PPT 簡報", type="primary"):
        st.info("功能開發中... (這裡將串接 Manager Agent 進行大綱規劃與生成)")

# --- 5. 主聊天介面 (智慧判斷核心) ---
st.title("💬 Smart Deck Agent")
st.caption("已啟用智慧工具判斷模式 (Function Calling)。請直接輸入您的需求。")

# 顯示歷史訊息
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        # 如果這條 AI 訊息有內容 (不是純工具呼叫)，就顯示出來
        if msg.content:
            with st.chat_message("assistant"):
                st.markdown(msg.content)
    # ToolMessage (工具回傳的 Raw Data) 我們選擇不直接顯示，保持介面乾淨

# 處理使用者輸入
if prompt := st.chat_input("輸入訊息... (例如：幫我總結這份報告、查一下最新 AI 新聞)"):
    
    # 1. 紀錄並顯示使用者訊息
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. AI 思考迴圈
    with st.chat_message("assistant"):
        # 建立一個佔位符來顯示狀態 (例如：正在搜尋...)
        status_container = st.empty()
        
        with st.spinner("正在思考下一步..."):
            # Step A: 將完整對話紀錄丟給 Gemini
            response = llm_with_tools.invoke(st.session_state.messages)
            
            # 存入對話紀錄 (包含 AI 的思考與可能的工具呼叫參數)
            st.session_state.messages.append(response)

            # Step B: 判斷 Gemini 是否決定要使用工具?
            if response.tool_calls:
                # 這裡可能會有多次工具呼叫 (Parallel Function Calling)
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    call_id = tool_call["id"]
                    
                    # --- UX 優化：告訴使用者現在發生什麼事 ---
                    if tool_name == "read_knowledge_base":
                        status_container.info(f"📚 正在閱讀知識庫... (查詢: {tool_args.get('query', '...')})")
                    elif tool_name == "google_search":
                        status_container.info(f"🌐 正在搜尋網路... (關鍵字: {tool_args.get('query', '...')})")
                    
                    # --- 執行工具 ---
                    selected_tool = tool_map.get(tool_name)
                    tool_output = "工具執行失敗"
                    
                    if selected_tool:
                        try:
                            # 針對我們定義的 Tool，通常只有一個參數 (query)
                            # 這裡直接取參數值傳入
                            arg_value = next(iter(tool_args.values())) if tool_args else ""
                            tool_output = selected_tool.invoke(arg_value)
                        except Exception as e:
                            tool_output = f"Error: {e}"
                    
                    # --- 將工具結果回傳給 AI ---
                    # 這是關鍵：我們把查到的資料包成 ToolMessage 塞回給 Gemini
                    st.session_state.messages.append(
                        ToolMessage(content=str(tool_output), tool_call_id=call_id, name=tool_name)
                    )
                
                # Step C: 讓 Gemini 根據查到的資料，生成最終回答
                final_response = llm_with_tools.invoke(st.session_state.messages)
                
                # 顯示最終回答
                st.markdown(final_response.content)
                st.session_state.messages.append(final_response)
                
                # 清除狀態提示
                status_container.empty()
                
            else:
                # 如果 Gemini 覺得不用查資料 (例如只是打招呼)，直接顯示回應
                st.markdown(response.content)