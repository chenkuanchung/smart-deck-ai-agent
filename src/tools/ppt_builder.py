# src/tools/ppt_builder.py
from pptx import Presentation
import os
import re

# --- 標準版型地圖 ---
LAYOUT_CONFIG = {
    "title": {"id": 0, "title_idx": 0, "body_idx": 1},
    "content": {"id": 1, "title_idx": 0, "body_idx": 1},
    "section": {"id": 2, "title_idx": 0, "body_idx": 1},
    "two_column": {"id": 3, "title_idx": 0, "left_idx": 1, "right_idx": 2},
    "comparison": {"id": 4, "title_idx": 0, "left_idx": 2, "right_idx": 4}
}

def clean_text(text):
    """
    清除 Markdown 符號與不必要的格式
    1. 移除 **粗體** 符號
    2. 移除列表符號 (如 - 或 *)，因為 PPT 會自己加 Bullet
    3. 移除多餘空白
    """
    if not isinstance(text, str):
        return str(text)
    
    # 移除 Markdown 粗體 (**text**)
    text = text.replace("**", "")
    text = text.replace("__", "")
    
    # 移除開頭的 - 或 * (如果 PPT 版型本身就有 bullet points)
    # text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    
    return text.strip()

def format_content(content_data):
    """
    將內容資料轉為適合 PPT 顯示的純文字字串
    """
    if isinstance(content_data, list):
        # 如果是列表，用換行符號接起來，變成多行文字
        # 並且對每一行做清理
        cleaned_list = [clean_text(item) for item in content_data]
        return "\n".join(cleaned_list)
    else:
        # 如果已經是字串，直接清理
        return clean_text(str(content_data))

def create_presentation(title: str, slides_content: list, template_path="template.pptx", filename="output.pptx"):
    """
    建立 PPT 檔案 (包含 Markdown 清除與 List 格式化功能)
    """
    
    if os.path.exists(template_path):
        prs = Presentation(template_path)
    else:
        prs = Presentation() 
        print("⚠️ 警告: 找不到 template.pptx")

    for i, page in enumerate(slides_content):
        layout_name = page.get('layout', 'content')
        if layout_name == 'comparison':
            config = LAYOUT_CONFIG['two_column'] # 暫時用雙欄替代
        else:
            config = LAYOUT_CONFIG.get(layout_name, LAYOUT_CONFIG['content'])
        
        try:
            slide = prs.slides.add_slide(prs.slide_layouts[config['id']])
        except IndexError:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            config = LAYOUT_CONFIG['content']
        
        # --- A. 填寫標題 ---
        title_idx = config.get('title_idx', 0)
        try:
            if slide.placeholders[title_idx].has_text_frame:
                # 標題也要清乾淨
                slide.placeholders[title_idx].text = clean_text(page.get('title', ''))
        except Exception:
            pass

        # --- B. 填寫內文 ---
        content_data = page.get('content', '')
        if not content_data:
            continue

        # 雙欄邏輯
        if layout_name == 'two_column' or layout_name == 'comparison':
            if isinstance(content_data, list) and len(content_data) >= 2:
                # 左欄
                try:
                    left_ph = slide.placeholders[config['left_idx']]
                    left_ph.text = format_content(content_data[0])
                except KeyError: pass
                
                # 右欄
                try:
                    right_ph = slide.placeholders[config['right_idx']]
                    right_ph.text = format_content(content_data[1])
                except KeyError: pass
            else:
                # 格式不對，硬塞左欄
                try:
                    slide.placeholders[config['left_idx']].text = format_content(content_data)
                except KeyError: pass
        
        # 單欄邏輯
        else:
            try:
                body_idx = config.get('body_idx')
                if body_idx is not None:
                    ph = slide.placeholders[body_idx]
                    
                    # [關鍵] 使用 format_content 處理 list 轉字串
                    final_text = format_content(content_data)
                    
                    if ph.has_text_frame:
                        ph.text_frame.text = final_text
                        ph.text_frame.word_wrap = True
                    else:
                        ph.text = final_text
            except KeyError:
                pass

        # --- C. 填寫備忘稿 (Notes) ---
        # 如果有 notes 欄位，填入備忘稿區
        notes_text = page.get('notes', '')
        if notes_text and slide.has_notes_slide:
            text_frame = slide.notes_slide.notes_text_frame
            text_frame.text = format_content(notes_text)

    output_path = os.path.join(os.getcwd(), filename)
    prs.save(output_path)
    return output_path