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
    """
    [Writer] 內容寫手
    """
    print("--- [Writer] 正在撰寫內容並生成 PPT ---")
    
    outline = state.outline
    
    # [關鍵修正] 防呆檢查：如果沒有大綱，直接結束，不要報錯
    if not outline or not outline.slides:
        print("⚠️ 錯誤：Writer 收到了空的大綱，停止生成。")
        return {"final_file_path": None}

    final_slides_data = [] 
    
    for i, slide in enumerate(outline.slides):
        print(f"  -> 處理第 {i+1} 頁: {slide.title} ({slide.layout})")
        
        if slide.layout in ["content", "two_column", "comparison"]:
            prompt = f"""
            你是一位專業的簡報撰寫員。請根據以下指引，撰寫這一頁的詳細內容。
            
            標題：{slide.title}
            版型：{slide.layout}
            原始指引：{slide.content}
            目標受眾：{outline.target_audience}
            
            【要求】：
            1. 語言：繁體中文。
            2. 風格：專業、精煉、條列式。
            3. 格式：
               - 'content': 一段完整的條列式文字。
               - 'two_column': 兩段文字，中間用 '|||' 分隔。
            
            請直接輸出內容。
            """
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                generated_text = response.content
            except Exception:
                generated_text = str(slide.content) # 失敗時用原始指引
            
            if slide.layout in ["two_column", "comparison"] and "|||" in generated_text:
                parts = generated_text.split("|||")
                final_content = [p.strip() for p in parts[:2]]
            else:
                final_content = generated_text
        else:
            final_content = slide.content[0] if slide.content else ""

        slide_data = {
            "layout": slide.layout,
            "title": slide.title,
            "content": final_content
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