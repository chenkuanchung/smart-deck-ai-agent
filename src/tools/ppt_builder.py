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
    """基礎清洗：移除 Markdown、多餘符號與字面換行"""
    if not isinstance(text, str):
        return str(text)
    
    # 處理字面上的 \n
    text = text.replace('\\n', '\n')
    # 移除 Markdown 粗體 (** 和 __)
    text = text.replace("**", "").replace("__", "")
    # 移除 List 字串殘留的引號
    text = text.strip("'").strip('"')
    
    return text

def normalize_content(data):
    """
    將內容統一轉為 List[str]，並處理換行分割
    """
    if isinstance(data, list):
        result = []
        for item in data:
            result.extend(normalize_content(item))
        return result
    
    data_str = str(data).strip()
    
    # 處理 Python List 字串 "['A', 'B']"
    if (data_str.startswith("[") and data_str.endswith("]")):
        try:
            parsed_list = ast.literal_eval(data_str)
            if isinstance(parsed_list, (list, tuple)):
                return normalize_content(parsed_list)
        except:
            pass

    # 處理 ||| 分隔
    if "|||" in data_str:
        return normalize_content(data_str.split("|||"))

    # 處理 \n 換行分割
    data_str = data_str.replace('\\n', '\n')
    if "\n" in data_str:
        return [line for line in data_str.split("\n") if line.strip()]

    return [data_str]

def fill_text_frame(text_frame, content_list):
    """
    [純淨版] 自動偵測層級並填入文字，樣式完全由母片決定
    """
    if not content_list:
        return

    text_frame.clear() 

    for line in content_list:
        if not line.strip():
            continue
        
        # 1. 偵測縮排 (Hierarchy Detection)
        # 計算開頭空白數來決定是第幾層
        leading_spaces = len(line) - len(line.lstrip())
        
        level = 0
        # 如果有 2 個以上空白，或是以 Tab 開頭，或是以 "- " 開頭，就當作第二層
        if leading_spaces >= 2 or line.startswith('\t') or line.strip().startswith('- '):
            level = 1
        
        # 2. 清洗內容 (移除開頭的 - 或 * 或 •，只留純文字)
        clean_line = re.sub(r'^[\s\-\*•]+', '', line).strip()
        
        # [關鍵修正] 在這裡再次呼叫 clean_text，確保 Markdown 粗體符號被拿掉
        clean_line = clean_text(clean_line)
        
        # 3. 填入段落
        p = text_frame.add_paragraph()
        p.text = clean_line # 只填純文字，不加符號
        p.level = level     # 設定層級，讓 PPT 母片決定縮排和符號

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
        
        # A. 標題 (這裡原本就有 clean_text)
        title_idx = config.get('title_idx', 0)
        try:
            if slide.placeholders[title_idx].has_text_frame:
                slide.placeholders[title_idx].text = clean_text(page.get('title', '')).strip()
        except Exception: pass

        # B. 內文
        raw_content = page.get('content', '')
        normalized_data = normalize_content(raw_content)

        if layout_name in ['two_column', 'comparison']:
            try:
                left_content = normalized_data[0] if len(normalized_data) > 0 else []
                if isinstance(left_content, str): left_content = normalize_content(left_content)
                fill_text_frame(slide.placeholders[config['left_idx']].text_frame, left_content)
            except (KeyError, IndexError): pass
            
            try:
                right_content = normalized_data[1] if len(normalized_data) > 1 else []
                if isinstance(right_content, str): right_content = normalize_content(right_content)
                fill_text_frame(slide.placeholders[config['right_idx']].text_frame, right_content)
            except (KeyError, IndexError): pass
        else:
            try:
                body_idx = config.get('body_idx')
                if body_idx is not None:
                    main_content = normalized_data
                    fill_text_frame(slide.placeholders[body_idx].text_frame, main_content)
            except KeyError: pass

        # C. 備忘稿
        notes_text = page.get('notes', '')
        if notes_text and slide.has_notes_slide:
            clean_notes = str(notes_text).replace('\\n', '\n').strip()
            slide.notes_slide.notes_text_frame.text = clean_notes

    output_path = os.path.join(os.getcwd(), filename)
    prs.save(output_path)
    return output_path