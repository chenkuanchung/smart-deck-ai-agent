# src/tools/ppt_builder.py
from pptx import Presentation
import os
import ast
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
    """清除 Markdown 與多餘符號"""
    if not isinstance(text, str):
        return str(text)
    
    text = text.replace("**", "").replace("__", "")
    text = text.strip("'").strip('"')
    # 移除開頭的手動 bullet，因為我们要用母片的
    text = re.sub(r'^[\-\*•]\s*', '', text)
    
    return text.strip()

def normalize_content(data):
    """資料格式清洗"""
    if isinstance(data, list):
        return [clean_text(str(item)) for item in data]
    
    data_str = str(data).strip()
    if (data_str.startswith("[") and data_str.endswith("]")):
        try:
            parsed_list = ast.literal_eval(data_str)
            if isinstance(parsed_list, (list, tuple)):
                return [clean_text(str(item)) for item in parsed_list]
        except:
            pass

    if "|||" in data_str:
        return [clean_text(part) for part in data_str.split("|||")]

    if "\n" in data_str:
        return [clean_text(line) for line in data_str.split("\n") if line.strip()]

    return [clean_text(data_str)]

def fill_text_frame(text_frame, content_list):
    """
    [純淨版] 只填入文字並設定層級，樣式完全由母片決定
    """
    if not content_list:
        return

    text_frame.clear() 

    for item in content_list:
        if not item.strip():
            continue
        
        p = text_frame.add_paragraph()
        p.text = item
        
        # [關鍵] 設定層級為 0
        # 這告訴 PPT: "請套用母片中『第一層』的項目符號樣式"
        p.level = 0 

def create_presentation(title: str, slides_content: list, template_path="template.pptx", filename="output.pptx"):
    """建立 PPT 檔案"""
    if os.path.exists(template_path):
        prs = Presentation(template_path)
    else:
        prs = Presentation() 
        print("⚠️ 警告: 找不到 template.pptx")

    for i, page in enumerate(slides_content):
        layout_name = page.get('layout', 'content')
        
        if layout_name == 'comparison':
            config = LAYOUT_CONFIG['two_column']
        else:
            config = LAYOUT_CONFIG.get(layout_name, LAYOUT_CONFIG['content'])
        
        try:
            slide = prs.slides.add_slide(prs.slide_layouts[config['id']])
        except IndexError:
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            config = LAYOUT_CONFIG['content']
        
        # A. 標題
        title_idx = config.get('title_idx', 0)
        try:
            if slide.placeholders[title_idx].has_text_frame:
                slide.placeholders[title_idx].text = clean_text(page.get('title', ''))
        except Exception: pass

        # B. 內文
        raw_content = page.get('content', '')
        normalized_data = normalize_content(raw_content)

        if layout_name in ['two_column', 'comparison']:
            try:
                left_content = normalized_data[0] if len(normalized_data) > 0 else []
                if isinstance(left_content, str): left_content = [left_content]
                fill_text_frame(slide.placeholders[config['left_idx']].text_frame, left_content)
            except (KeyError, IndexError): pass
            
            try:
                right_content = normalized_data[1] if len(normalized_data) > 1 else []
                if isinstance(right_content, str): right_content = [right_content]
                fill_text_frame(slide.placeholders[config['right_idx']].text_frame, right_content)
            except (KeyError, IndexError): pass
        else:
            try:
                body_idx = config.get('body_idx')
                if body_idx is not None:
                    main_content = normalized_data if isinstance(normalized_data, list) else [str(normalized_data)]
                    fill_text_frame(slide.placeholders[body_idx].text_frame, main_content)
            except KeyError: pass

        # C. 備忘稿
        notes_text = page.get('notes', '')
        if notes_text and slide.has_notes_slide:
            slide.notes_slide.notes_text_frame.text = clean_text(str(notes_text))

    output_path = os.path.join(os.getcwd(), filename)
    prs.save(output_path)
    return output_path