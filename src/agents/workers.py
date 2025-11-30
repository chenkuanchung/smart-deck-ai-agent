# src/agents/workers.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.config import Config
from src.agents.state import AgentState
from src.tools.ppt_builder import create_presentation

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.1
)

def writer_node(state: AgentState):
    print("--- [Writer] 正在撰寫內容並生成 PPT ---")
    
    outline = state.outline
    if not outline or not outline.slides:
        print("⚠️ 錯誤：Writer 收到了空的大綱")
        return {"final_file_path": None}

    final_slides_data = [] 
    
    for i, slide in enumerate(outline.slides):
        print(f"  -> 處理第 {i+1} 頁: {slide.title}")
        
        if slide.layout in ["content", "two_column", "comparison"]:
            prompt = f"""
            你是一位專業的「簡報內容編輯」。你的任務是將輸入的「原始指引」整理成適合放入 PPT 的乾淨文字。
            
            【輸入資訊】：
            標題：{slide.title}
            版型：{slide.layout}
            原始指引：{slide.content}
            
            【編輯準則 (Guidelines)】：
            1. **忠實還原 (Faithfulness)**：
               - 如果「原始指引」已經是完整的句子或重點，**請直接使用，不要改寫，不要擴寫，也不要縮寫**。
               - 只有當「原始指引」太過簡略（例如只有關鍵字）時，才適度補充成通順的句子。
            
            2. **嚴格格式 (Formatting)**：
               - **禁止 Markdown**：絕對不要出現 '**'、'#'、'- '、'['、']' 等符號。
               - **層級結構**：
                 - 第一層重點：直接書寫。
                 - 第二層細節（縮排）：**請在開頭加上兩個空白** (  )。
               - **換行**：每個重點請換行。

            3. **版型處理**：
               - 若是 'two_column'：請確保輸出包含 '|||' 分隔符號，將內容分為左右兩塊。如果原始指引沒有明顯分左右，請根據邏輯自行分配。
            
            請輸出整理後的純文字內容：
            """
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                generated_text = response.content
            except Exception:
                generated_text = str(slide.content)
            
            # 處理雙欄
            if slide.layout in ["two_column", "comparison"] and "|||" in generated_text:
                parts = generated_text.split("|||")
                final_content = [p.strip() for p in parts[:2]]
            else:
                final_content = generated_text
        else:
            final_content = slide.content

        slide_data = {
            "layout": slide.layout,
            "title": slide.title,
            "content": final_content,
            "notes": slide.notes
        }
        final_slides_data.append(slide_data)
        
    print("  -> 呼叫 PPT Builder...")
    output_filename = "final_presentation.pptx"
    
    try:
        ppt_path = create_presentation(
            title=outline.topic,
            slides_content=final_slides_data,
            template_path="template.pptx",
            filename=output_filename
        )
        return {"final_file_path": ppt_path}
    except Exception as e:
        print(f"❌ PPT 生成失敗: {e}")
        return {"final_file_path": None}