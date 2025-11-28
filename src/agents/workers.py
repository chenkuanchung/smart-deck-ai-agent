# src/agents/workers.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.config import Config
from src.agents.state import AgentState
from src.tools.ppt_builder import create_presentation

llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.7
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
            你是一位專業簡報撰寫員。請根據以下資訊撰寫本頁內容。
            
            標題：{slide.title}
            版型：{slide.layout}
            原始指引：{slide.content}
            目標受眾：{outline.target_audience}
            
            【嚴格規範】：
            1. **禁止 Markdown**：絕對不要使用 '**'、'#' 或 '- ' 符號。
            2. **內容長度**：每點 20-40 字。
            3. **格式要求**：直接輸出純文字，每點換行。

            ### 輸出範例 (Example)：
            
            [錯誤寫法] (不要這樣寫):
            **市場優勢：**
            - 我們擁有獨家技術
            - *成本更低*

            [正確寫法] (請這樣寫):
            我們擁有業界領先的獨家專利技術
            透過製程優化成功降低了 30% 生產成本
            建立了全台最大的銷售通路網絡

            若是 'two_column' 版型，請用 '|||' 分隔兩段：
            左邊的第一個論點
            左邊的第二個論點
            |||
            右邊的第一個論點
            右邊的第二個論點
            
            請直接輸出內容：
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