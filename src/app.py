# src/app.py
import streamlit as st
import os
import sys
import uuid
import json
import concurrent.futures

# 路徑修正
current_file_path = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(src_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import Config
from src.tools.rag import RAGManager
from src.tools.search import search_tool, read_webpage
from src.graph import agent_workflow
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from src.agents.state import PresentationOutline 
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from google.api_core.exceptions import ResourceExhausted 

TOOL_DISPLAY_NAMES = {
    "google_search": "🌏 正在搜尋網路... (Web Research)",
    "read_knowledge_base": "📚 正在分析內部文件 (Document Analysis)",
    "read_webpage": "📖 正在深度閱讀網頁全文 (Deep Reading)"
}

SYSTEM_PROMPT_TEMPLATE = """
你現在是 Smart Deck 團隊的 **「首席策略分析師 (Lead Strategy Analyst)」**。
你不僅僅是一個搜尋工具，你是使用者的**「簡報顧問」**與**「前期策劃」**。
你的終極任務：協助使用者透過對話，將模糊的想法轉化為**「高資訊密度、邏輯嚴密」**的簡報素材。
### 🌟 當前環境感知
- **已上傳文件**：{file_count} 份 ({file_names})
### 🧠 你的思考與行動協議
1. **意圖偵測**：若指令太模糊，請反問釐清。
2. **工具戰術**：
   - 【內部文件】：優先呼叫 `read_knowledge_base`。
   - 【外部廣搜】：呼叫 `Google Search` 獲取初步結果與網址。
   - 【外部深讀】：判斷需要詳細數據時，務必將網址傳入 `read_webpage` 閱讀內文。
3. **🔥 舉一反三與主動性**：
   - 如果網頁沒有具體數據，絕對不要雙手一攤！重新呼叫 `Google Search` 換關鍵字尋找新網址。請在背景不斷嘗試，直到挖到有價值的硬數據。
   - 請善用平行處理能力，同時呼叫多次 `read_webpage`。
4. **絕對禁區**：嚴禁呼叫空參數。嚴禁捏造數據。
"""

st.set_page_config(page_title="Smart Deck Agent", page_icon="📊", layout="wide")
try: Config.validate()
except Exception as e: st.error(f"環境設定錯誤: {e}"); st.stop()

# --- 狀態初始化 ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.db_files = set() 
    st.session_state.file_uploader_key = 0
    st.session_state.final_file_path = None 

rag_manager = RAGManager(st.session_state.session_id)
rag_tool = rag_manager.get_tool()
tools = [rag_tool, search_tool, read_webpage]
tool_map = {"read_knowledge_base": rag_tool, "google_search": search_tool, "read_webpage": read_webpage}
llm = ChatGoogleGenerativeAI(model=Config.MODEL_FAST, google_api_key=Config.GOOGLE_API_KEY, temperature=0.7)
llm_with_tools = llm.bind_tools(tools)

# 讀取目前 Graph 執行緒的狀態
thread_config = {"configurable": {"thread_id": st.session_state.session_id}}
state_snapshot = agent_workflow.get_state(thread_config)
is_paused = "writer_node" in state_snapshot.next

def get_safe_history(messages, limit=10):
    if not messages: return []
    if len(messages) <= limit:
        start_idx = 0
        while start_idx < len(messages) and not isinstance(messages[start_idx], HumanMessage): start_idx += 1
        return messages[start_idx:] if start_idx < len(messages) else []
    start_idx = len(messages) - limit
    while start_idx > 0 and not isinstance(messages[start_idx], HumanMessage): start_idx -= 1
    return messages[start_idx:]

# --- Sidebar UI ---
with st.sidebar:
    st.title("💬 Smart Deck Agent")
    st.caption(f"🔑 Session: {st.session_state.session_id[:8]}")
    st.header("📂 資料來源")
    
    uploaded_files = st.file_uploader("上傳 PDF/TXT", type=["pdf", "txt"], accept_multiple_files=True, key=f"uploader_{st.session_state.file_uploader_key}")
    current_filenames = {f.name for f in uploaded_files} if uploaded_files else set()

    new_files = [f for f in uploaded_files if f.name not in st.session_state.db_files] if uploaded_files else []
    for file in new_files:
        with st.spinner(f"處理中：{file.name}..."):
            res = rag_manager.ingest_file(file.getbuffer(), file.name)
            if "✅" in res:
                st.session_state.db_files.add(file.name)
                st.session_state.messages.append(HumanMessage(content=f"[系統] {res}"))
                st.success(res) 
            else: st.error(res)

    removed_files = st.session_state.db_files - current_filenames
    if removed_files:
        for filename in removed_files:
            res = rag_manager.remove_file(filename)
            st.session_state.db_files.remove(filename)
            st.session_state.messages.append(HumanMessage(content=f"[系統] {res}"))
            st.success(res) 

    if st.button("🗑️ Reset", type="secondary"):
        rag_manager.reset()
        st.session_state.db_files = set()
        st.session_state.messages = []
        st.session_state.file_uploader_key += 1
        st.session_state.session_id = str(uuid.uuid4()) 
        st.session_state.final_file_path = None
        st.rerun()

    st.divider()

    st.header("⚙️ 生成控制台")
    if not is_paused:
        # 【階段 1】：規劃大綱
        if st.button("✨ 1. 規劃簡報大綱", type="primary", use_container_width=True):
            if not st.session_state.messages and not st.session_state.db_files:
                st.warning("⚠️ 請先在右側與 AI 討論，或者在上傳文件後再點擊生成！")
            else:
                with st.status("🤖 🧠 Manager: 正在分析資料與規劃大綱...", expanded=True) as status:
                    
                    safe_outline_msgs = get_safe_history(st.session_state.messages, limit=12) if st.session_state.messages else []
                    chat_history_str = "\n".join([f"{type(m).__name__}: {m.content}" for m in safe_outline_msgs])
                    
                    rag_context = ""
                    if st.session_state.db_files:
                        status.update(label="📚 Manager: 正在調閱並整合知識庫文件內容...")
                        try:
                            file_names = ", ".join(st.session_state.db_files)
                            rag_result = rag_tool.invoke({"query": f"請詳細總結 {file_names} 的所有核心內容、數據與亮點，以利後續製作簡報。"})
                            rag_context = f"\n\n====================\n【系統背景提取：知識庫文件核心內容】:\n{rag_result}\n====================\n"
                        except Exception as e:
                            rag_context = f"\n\n(知識庫文件讀取發生錯誤，請依賴對話紀錄: {e})\n"
                            
                    final_chat_history = chat_history_str + rag_context
                    
                    if st.session_state.messages and st.session_state.db_files:
                        user_request_text = "請根據上述【對話紀錄】的討論脈絡，並嚴格結合【知識庫文件核心內容】的硬數據與重點，為我製作一份結構嚴謹的簡報大綱。"
                    elif st.session_state.messages:
                        user_request_text = "請根據上述【對話紀錄】的討論脈絡，為我製作一份結構嚴謹的簡報大綱。"
                    else:
                        user_request_text = "請嚴格根據上述【知識庫文件核心內容】，為我提煉並製作一份結構嚴謹的簡報大綱。"

                    initial_state = {
                        "user_request": user_request_text, 
                        "chat_history": final_chat_history,
                        "session_id": st.session_state.session_id
                    }
                    try:
                        for output in agent_workflow.stream(initial_state, config=thread_config):
                            pass 
                        status.update(label="✅ 大綱規劃完成！請在右側主畫面檢查。", state="complete")
                        st.rerun() 
                    except Exception as e:
                        error_msg = f"> ❌ **系統提示 (大綱生成失敗)**：\n> 發生異常，若為 API 配額限制請稍後重試。錯誤詳情：`{str(e)}`"
                        status.update(label="❌ 規劃失敗 (請看右側提示)", state="error")
                        st.session_state.messages.append(AIMessage(content=error_msg))
                        st.rerun() 
    else:
        # 【階段 2】：側邊欄改為極簡提示
        st.warning("⏸️ 系統暫停：大綱準備完畢！")
        st.info("👉 請在右側主畫面檢查並修改大綱內容。")
        
        if st.button("🗑️ 捨棄重來", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.final_file_path = None
            st.rerun()

    if st.session_state.get("final_file_path") and os.path.exists(st.session_state.final_file_path):
        with open(st.session_state.final_file_path, "rb") as f:
            st.download_button(
                label="📥 點此下載最新簡報 (PPTX)", data=f, file_name=os.path.basename(st.session_state.final_file_path),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", type="primary", use_container_width=True
            )

@retry(retry=retry_if_exception_type(ResourceExhausted), wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3), reraise=True)
def safe_llm_invoke(llm, messages):
    return llm.invoke(messages)

# ==========================================
# --- 畫面主體切換邏輯 ---
# ==========================================
if is_paused:
    # 🔴 暫停模式：顯示寬敞的 JSON 編輯器
    st.header("📝 簡報大綱編輯器")
    current_outline = state_snapshot.values.get("outline")
    
    if current_outline:
        edited_json = st.text_area(
            "您可以直接修改下方 JSON 內容（如標題、重點），確認無誤後再進行排版。", 
            value=current_outline.model_dump_json(indent=2), height=450
        )
        st.markdown("---")
        st.subheader("🪄 AI 大綱微調助理")
        ai_edit_instruction = st.text_input("💬 告訴 AI 你想怎麼調整 (例如：把第二頁拆成兩頁、第一頁標題改活潑一點)")
        
        if st.button("讓 AI 自動修改大綱", type="secondary"):
            if ai_edit_instruction:
                with st.spinner("🧠 AI 正在理解指示並進行局部修改..."):
                    try:
                        editor_system = "你是頂尖的簡報大綱編輯器。請根據使用者的【修改指示】，調整現有的【目前大綱】，並回傳完整的最新 JSON 結構。"
                        structured_editor = llm.with_structured_output(PresentationOutline)
                        new_outline = structured_editor.invoke([
                            SystemMessage(content=editor_system),
                            HumanMessage(content=f"【目前大綱】:\n{edited_json}\n\n【修改指示】:\n{ai_edit_instruction}")
                        ])
                        agent_workflow.update_state(thread_config, {"outline": new_outline})
                        st.rerun() 
                    except Exception as e:
                        st.error(f"修改失敗，請稍後再試: {e}")
            else:
                st.warning("⚠️ 請先輸入你想修改什麼！")
                
        st.markdown("---")
        if st.button("✅ 2. 確認並排版 (產生 PPT)", type="primary"):
            with st.status("✍️ Writer: 正在渲染投影片...", expanded=True) as status:
                try:
                    updated_outline_dict = json.loads(edited_json)
                    updated_outline = PresentationOutline(**updated_outline_dict)
                    agent_workflow.update_state(thread_config, {"outline": updated_outline})
                    
                    final_file_path = None
                    for output in agent_workflow.stream(None, config=thread_config):
                        if "writer_node" in output:
                            final_file_path = output["writer_node"].get("final_file_path")
                    
                    if final_file_path and os.path.exists(final_file_path):
                        status.update(label="🎉 簡報生成大功告成！請在左側下載。", state="complete")
                        st.session_state.final_file_path = final_file_path
                    else:
                        status.update(label="❌ 渲染失敗", state="error")
                except json.JSONDecodeError:
                    status.update(label="❌ JSON 格式錯誤，請檢查括號與引號。", state="error")
                except Exception as e:
                    status.update(label=f"❌ 錯誤: {e}", state="error")
            st.rerun()
    else:
        # ✨ 【重點防呆】：捕捉 API 失敗導致 JSON 空白的狀況
        st.error("❌ 系統未能成功生成大綱資料！")
        st.warning("這通常是因為：\n1. 您的 Google API 額度已達上限 (429 Rate Limit)。\n2. 資訊量太少，導致 AI 無法規劃出完整的結構。")
        st.info("💡 解決方案：請點擊左側的「🗑️ 捨棄重來」，稍等 1 分鐘讓 API 額度恢復後，再試一次！")

else:
    # 🔵 正常模式：顯示聊天室
    if not st.session_state.messages:
        st.markdown("""
        ## 👋 歡迎使用 Smart Deck Agent！
        我是您的專屬 AI 簡報幕僚，結合了**深度網頁爬蟲**與**內部知識庫檢索 (RAG)** 能力。

        **您可以請我做這些事：**
        * 🌍 **市場研究**：自動上網搜尋並閱讀多篇報導，為您提煉數據。
        * 📚 **內部文件**：上傳您的 PDF/TXT，我能針對專屬資料精準問答。
        * 📊 **自動生成 PPT**：討論充分後，點擊左側「✨ 1. 規劃簡報大綱」，我會產出可編輯的大綱並渲染成簡報。
        """)

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"): st.markdown(msg.content)
        elif isinstance(msg, AIMessage) and msg.content:
            if not getattr(msg, "tool_calls", None):
                with st.chat_message("assistant"): 
                    # ✨ [新增] 動態判斷訊息類型，給予對應的 UI 顏色框
                    if "❌" in msg.content and "系統提示" in msg.content:
                        st.error(msg.content)    # 渲染成原生紅框
                    elif "⚠️" in msg.content and "系統提示" in msg.content:
                        st.warning(msg.content)  # 渲染成原生黃框 (例如達最大迴圈數時)
                    else:
                        st.markdown(msg.content) # 一般對話維持純文字

    if prompt := st.chat_input("輸入訊息..."):
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"): st.markdown(prompt)

        with st.chat_message("assistant"):
            status_box = st.empty()
            with st.spinner("思考中..."):
                try:
                    file_count = len(st.session_state.db_files)
                    file_names = ", ".join(st.session_state.db_files) if file_count > 0 else "無"
                    dynamic_system_prompt = SYSTEM_PROMPT_TEMPLATE.format(file_count=file_count, file_names=file_names)
                    
                    safe_messages = get_safe_history(st.session_state.messages, limit=12)
                    messages_to_send = [SystemMessage(content=dynamic_system_prompt)] + safe_messages
                    
                    response = safe_llm_invoke(llm_with_tools, messages_to_send)
                    st.session_state.messages.append(response)

                    MAX_ITERATIONS = 3
                    current_iteration = 0

                    while response.tool_calls and current_iteration < MAX_ITERATIONS:
                        current_iteration += 1
                        
                        for tc in response.tool_calls:
                            name = tc["name"]
                            args = tc["args"]
                            display_val = args.get("query") or args.get("url") or str(args)
                            display_name = TOOL_DISPLAY_NAMES.get(name, f"🔧 {name}")
                            
                            if current_iteration == 1: action_prefix = "⚡ 正在執行"
                            elif current_iteration == 2: action_prefix = "🔄 深入追蹤線索"
                            else: action_prefix = "🕵️‍♂️ 擴大檢索範圍"
                            status_box.info(f"{action_prefix}：{display_name} ({display_val[:30]}...)")
                        
                        def execute_tool(tc):
                            tool_instance = tool_map.get(tc["name"])
                            return tool_instance.invoke(tc["args"]) if tool_instance else "Tool not found"

                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                            results = list(executor.map(execute_tool, response.tool_calls))
                        
                        for tc, res in zip(response.tool_calls, results):
                            st.session_state.messages.append(ToolMessage(content=str(res), tool_call_id=tc["id"], name=tc["name"]))
                        
                        safe_messages = get_safe_history(st.session_state.messages, limit=15)
                        messages_to_send = [SystemMessage(content=dynamic_system_prompt)] + safe_messages
                        
                        response = safe_llm_invoke(llm_with_tools, messages_to_send)
                        st.session_state.messages.append(response)
                    
                    status_box.empty()
                    
                    if current_iteration >= MAX_ITERATIONS:
                        st.session_state.messages.append(AIMessage(content="> ⚠️ **系統提示**：Agent 已達到最大探索深度 (3次)，已強制要求它根據現有資料進行總結以節省資源。"))
                        
                    st.rerun()
                except Exception as e:
                    st.session_state.messages.append(AIMessage(content=f"> ❌ **系統提示**：\n> 發生異常：`{str(e)}`"))
                    st.rerun()