# src/agents/workers.py
from src.agents.state import AgentState, ContentItem
from src.tools.ppt_builder import create_presentation

def writer_node(state: AgentState):
    """
    Writer 負責將 Manager 的結構化大綱轉換為 PPT。
    現在它主要扮演 Adapter 與 Cleaner 的角色，確保傳給 Builder 的資料格式無誤。
    """
    print("--- [Writer] 收到大綱，準備生成 PPT ---")
    
    outline = state.outline
    if not outline or not outline.slides:
        print("⚠️ Writer: 空大綱，停止生成")
        return {"final_file_path": None}

    final_slides_data = [] 
    
    for i, slide in enumerate(outline.slides):
        print(f"  -> 處理 Slide {i+1}: {slide.title}")
        
        # --- 資料清洗與標準化 (Sanitization) ---
        cleaned_content = []
        raw_content = slide.content if slide.content else []
        
        for item in raw_content:
            # 處理 ContentItem 物件 (標準情況)
            if isinstance(item, ContentItem):
                text_clean = item.text.replace("**", "").replace("__", "").strip()
                cleaned_content.append(ContentItem(
                    text=text_clean, level=item.level, column=item.column
                ))
            
            # 處理 Dict (若被序列化)
            elif isinstance(item, dict):
                text_clean = item.get("text", "").replace("**", "").strip()
                cleaned_content.append(ContentItem(
                    text=text_clean, 
                    level=item.get("level", 0), 
                    column=item.get("column", 0)
                ))
                
            # 處理 Str (Fallback 機制，防止 Manager 偶爾吐出字串)
            elif isinstance(item, str):
                cleaned_content.append(ContentItem(
                    text=item.replace("**", "").strip(), 
                    level=0, column=0
                ))

        slide_data = {
            "layout": slide.layout,
            "title": slide.title,
            "content": cleaned_content, # 這是清洗過的物件列表
            "notes": slide.notes
        }
        final_slides_data.append(slide_data)
        
    # --- 呼叫 PPT Builder ---
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
        import traceback
        traceback.print_exc()
        return {"final_file_path": None}