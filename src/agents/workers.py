# src/agents/workers.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.config import Config
from src.agents.state import AgentState
from src.tools.ppt_builder import create_presentation

# 初始化 Gemini (使用聰明模型撰寫詳細內容)
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_SMART, 
    google_api_key=Config.GOOGLE_API_KEY,
    temperature=0.7
)

def writer_node(state: AgentState):
    """
    [Writer] 內容寫手
    任務：根據大綱擴寫內容，並呼叫 PPT Builder 生成檔案
    """
    print("--- [Writer] 正在撰寫內容並生成 PPT ---")
    
    outline = state.outline
    final_slides_data = [] # 準備給 PPT Builder 的資料
    
    # 遍歷每一頁大綱
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
            2. 風格：專業、精煉、條列式 (Bullet points)。
            3. 格式：
               - 如果是 'content' (單欄)：請輸出一段完整的條列式文字。
               - 如果是 'two_column' (雙欄)：請輸出兩段文字，中間用 '|||' 分隔。例如：
                 左邊的論點...
                 |||
                 右邊的論點...
            
            請直接輸出內容，不要廢話。
            """
            response = llm.invoke([HumanMessage(content=prompt)])
            generated_text = response.content
            
            # 處理雙欄分隔
            if slide.layout in ["two_column", "comparison"] and "|||" in generated_text:
                parts = generated_text.split("|||")
                final_content = [p.strip() for p in parts[:2]] # 取前兩段
            else:
                final_content = generated_text
        else:
            # 封面或章節頁，直接使用 Manager 的規劃
            final_content = slide.content[0] if slide.content else ""

        # 組裝資料
        slide_data = {
            "layout": slide.layout,
            "title": slide.title,
            "content": final_content
        }
        final_slides_data.append(slide_data)
        
    # 呼叫工具生成檔案
    print("  -> 呼叫 PPT Builder...")
    output_filename = "final_presentation.pptx"
    ppt_path = create_presentation(
        title=outline.topic,
        slides_content=final_slides_data,
        template_path="template.pptx",
        filename=output_filename
    )
    
    return {"final_file_path": ppt_path}