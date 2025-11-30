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
    
    text = text.replace('\\n', '\n')
    text = text.replace("**", "").replace("__", "")
    text = text.strip("'").strip('"')
    return text

def normalize_content(data):
    """將內容統一轉為 List[str]"""
    if isinstance(data, list):
        result = []
        for item in data:
            result.extend(normalize_content(item))
        return result
    
    data_str = str(data).strip()
    if (data_str.startswith("[") and data_str.endswith("]")):
        try:
            parsed_list = ast.literal_eval(data_str)
            if isinstance(parsed_list, (list, tuple)):
                return normalize_content(parsed_list)
        except:
            pass

    if "|||" in data_str:
        return normalize_content(data_str.split("|||"))

    data_str = data_str.replace('\\n', '\n')
    if "\n" in data_str:
        return [line for line in data_str.split("\n") if line.strip()]

    return [data_str]

def fill_text_frame(text_frame, content_list):
    """
    [修正版] 解決首行空行問題，並自動偵測層級
    """
    if not content_list:
        return

    text_frame.clear() 

    valid_lines = [line for line in content_list if line.strip()]
    
    for i, line in enumerate(valid_lines):
        # 1. 偵測縮排 (2個空白, tab, 或 "- " 開頭視為第二層)
        leading_spaces = len(line) - len(line.lstrip())
        level = 0
        if leading_spaces >= 2 or line.startswith('\t') or line.strip().startswith('- '):
            level = 1
        
        # 2. 清洗內容
        clean_line = re.sub(r'^[\s\-\*•]+', '', line).strip()
        clean_line = clean_text(clean_line)
        
        # 3. 填入段落
        if i == 0:
            p = text_frame.paragraphs[0]
        else:
            p = text_frame.add_paragraph()
            
        p.text = clean_line
        p.level = level

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
                slide.placeholders[title_idx].text = clean_text(page.get('title', '')).strip()
        except Exception: pass

        # B. 內文處理 (關鍵修正區域)
        raw_content = page.get('content', '')

        if layout_name in ['two_column', 'comparison']:
            # [修正] 針對雙欄版型，必須先分離左右內容，再分別進行標準化 (Normalize)
            # 這樣才不會把左邊的細節混到右邊，或是被無差別展平
            
            left_raw = ""
            right_raw = ""
            
            # 情況 1: raw_content 是 List (Worker 產出的標準格式)
            if isinstance(raw_content, list):
                if len(raw_content) > 0: left_raw = raw_content[0]
                if len(raw_content) > 1: right_raw = raw_content[1]
            
            # 情況 2: raw_content 是 String (可能包含 |||)
            elif isinstance(raw_content, str):
                if "|||" in raw_content:
                    parts = raw_content.split("|||")
                    left_raw = parts[0]
                    if len(parts) > 1: right_raw = parts[1]
                else:
                    left_raw = raw_content

            # 分別處理左右欄的內容拆解 (Split lines)
            left_lines = normalize_content(left_raw)
            right_lines = normalize_content(right_raw)

            try:
                fill_text_frame(slide.placeholders[config['left_idx']].text_frame, left_lines)
            except (KeyError, IndexError): pass
            
            try:
                fill_text_frame(slide.placeholders[config['right_idx']].text_frame, right_lines)
            except (KeyError, IndexError): pass
            
        else:
            # 單欄版型，直接展平即可
            normalized_data = normalize_content(raw_content)
            try:
                body_idx = config.get('body_idx')
                if body_idx is not None:
                    fill_text_frame(slide.placeholders[body_idx].text_frame, normalized_data)
            except KeyError: pass

        # C. 備忘稿
        notes_text = page.get('notes', '')
        if notes_text and slide.has_notes_slide:
            clean_notes = str(notes_text).replace('\\n', '\n').strip()
            slide.notes_slide.notes_text_frame.text = clean_notes

    output_path = os.path.join(os.getcwd(), filename)
    prs.save(output_path)
    return output_path