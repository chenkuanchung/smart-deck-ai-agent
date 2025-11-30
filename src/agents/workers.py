# src/agents/workers.py
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.config import Config
from src.agents.state import AgentState
from src.tools.ppt_builder import create_presentation

# 使用 Flash 模型 (速度快、Token多)
llm = ChatGoogleGenerativeAI(
    model=Config.MODEL_FAST, 
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
        print(f"  -> 處理第 {i+1} 頁: {slide.title} ({slide.layout})")
        
        # Rate Limit 保護
        if i > 0:
            time.sleep(1) 

        if slide.layout in ["content", "two_column", "comparison"]:
            layout_instruction = ""
            if slide.layout == "content":
                layout_instruction = "版型：標準單欄。請保持條列式結構。"
            elif slide.layout in ["two_column", "comparison"]:
                layout_instruction = "版型：雙欄/比較。**必須**包含 '|||' 分隔符號。範例：左邊重點... ||| 右邊重點..."

            # [關鍵修正] 忠實轉錄指令
            prompt = f"""
            你是一位專業的「簡報內容排版師」。
            
            【你的任務】：
            將 Manager 提供的「原始指引」整理成 PPT 內文。
            **「原始指引」中的資訊就是真理，請完整保留，不要刪減。**
            
            【輸入資訊】：
            標題：{slide.title}
            原始指引：{slide.content}
            
            【排版指令】：
            {layout_instruction}
            
            【編輯準則】：
            1. **數據絕對完整**：如果指引中有「09:00」、「1.33倍」、「30天」等數據，**一個都不能少**。
            2. **不做摘要**：請直接將指引轉化為條列式重點，不要試圖用一句話總結。
            3. **格式清理**：移除 ** 或 # 等 Markdown 符號。
            
            請直接輸出最終內容文字：
            """
            
            try:
                response = llm.invoke([HumanMessage(content=prompt)])
                generated_text = response.content.strip()
            except Exception as e:
                print(f"    ⚠️ LLM 生成失敗: {e}")
                generated_text = str(slide.content)
            
            if slide.layout in ["two_column", "comparison"]:
                if "|||" in generated_text:
                    parts = generated_text.split("|||")
                    final_content = [p.strip() for p in parts[:2]]
                else:
                    final_content = [generated_text, ""]
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