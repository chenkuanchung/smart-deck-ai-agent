# src/agents/workers.py
import os
import re
import traceback
from src.agents.state import AgentState, ContentItem
from src.tools.ppt_builder import create_presentation
from src.config import Config

def clean_markdown_text(text: str) -> str:
    """清除 LLM 生成的 Markdown 符號，保持 PPT 純文字排版"""
    if not text: return ""
    text = str(text)
    
    # 1. 移除 Markdown 連結 [文字](網址) -> 只保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 2. 移除粗體與斜體 (**text**, __text__, *text*)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # 3. 移除 Markdown 標題符號 (# 標題)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 4. 移除列表前綴 (- 或 *)，避免與 PPT 內建的 bullet points 衝突
    text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
    # 5. 過濾行內程式碼與程式碼區塊，徹底消滅殘留的 ` 符號
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    return text.strip()

def writer_node(state: AgentState):
    print("--- [Writer] 收到大綱，準備生成 PPT ---")
    
    outline = state.outline
    if not outline or not outline.slides:
        print("⚠️ Writer: 空大綱，停止生成")
        # ✨ 加入錯誤回報
        return {"final_file_path": None, "error_message": "Writer 節點收到空大綱，無法生成簡報。"}

    final_slides_data = [] 
    
    for i, slide in enumerate(outline.slides):
        print(f"  -> 處理 Slide {i+1}: {slide.title}")
        
        cleaned_content = []
        raw_content = slide.content if slide.content else []
        
        for item in raw_content:
            # 處理 ContentItem 物件 (標準情況)
            if isinstance(item, ContentItem):
                text_clean = clean_markdown_text(item.text) # 使用強化版清洗函數
                cleaned_content.append(ContentItem(
                    text=text_clean, level=item.level, column=item.column
                ))
            
            # 處理 Dict (若被序列化)
            elif isinstance(item, dict):
                text_clean = clean_markdown_text(item.get("text", ""))
                cleaned_content.append(ContentItem(
                    text=text_clean, 
                    level=item.get("level", 0), 
                    column=item.get("column", 0)
                ))
                
            # 處理 Str (Fallback 機制，防止 Manager 偶爾吐出字串)
            elif isinstance(item, str):
                text_clean = clean_markdown_text(item)
                cleaned_content.append(ContentItem(
                    text=text_clean, 
                    level=0, column=0
                ))

        slide_data = {
            "layout": slide.layout,
            "title": clean_markdown_text(slide.title), # 順便清洗標題
            "content": cleaned_content,
            "notes": clean_markdown_text(slide.notes) # 順便清洗備忘稿
        }
        final_slides_data.append(slide_data)
        
    # ✨ [修改] 將檔名結合 Config.OUTPUT_DIR 變成絕對路徑
    output_filename = f"presentation_{state.session_id[:8]}.pptx"
    output_filepath = os.path.join(Config.OUTPUT_DIR, output_filename)
    
    try:
        ppt_path = create_presentation(
            title=clean_markdown_text(outline.topic),
            slides_content=final_slides_data,
            template_path="template.pptx",
            filename=output_filepath
        )
        return {"final_file_path": ppt_path, "error_message": None}
    except Exception as e:
        error_msg = f"PPT 檔案生成失敗：{str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        # ✨ 失敗時將錯誤傳回前端
        return {"final_file_path": None, "error_message": error_msg}