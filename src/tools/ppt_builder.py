# src/tools/ppt_builder.py
from pptx import Presentation
import os

# --- 標準版型地圖 (Standard Layout Config) ---
# 根據你提供的結構分析，這些 Index 都是最標準的配置
LAYOUT_CONFIG = {
    "title": {
        "id": 0,           # 標題投影片
        "title_idx": 0,
        "body_idx": 1      # 副標題
    },
    "content": {
        "id": 1,           # 標題及內容 (標準內文頁)
        "title_idx": 0,
        "body_idx": 1      # 內文框
    },
    "section": {
        "id": 2,           # 章節標題
        "title_idx": 0,
        "body_idx": 1      # 章節描述
    },
    "two_column": {
        "id": 3,           # 兩個內容 (左右雙欄)
        "title_idx": 0,
        "left_idx": 1,     # 左欄
        "right_idx": 2     # 右欄
    },
    "comparison": {
        "id": 4,           # 比較 (有小標題)
        "title_idx": 0,
        "left_idx": 2,     # 左內文 (注意: 1是左標題)
        "right_idx": 4     # 右內文 (注意: 3是右標題)
        # 暫時先用 ID 3 的 two_column 處理比較比較簡單，這裡僅作紀錄
    }
}

def create_presentation(title: str, slides_content: list, template_path="template.pptx", filename="output.pptx"):
    """
    建立 PPT 檔案的工具函式 (標準版型適配版)
    """
    
    # 1. 載入 Template
    if os.path.exists(template_path):
        prs = Presentation(template_path)
    else:
        # 如果真的沒模板，用內建的通常也是這個順序
        prs = Presentation() 
        print("⚠️ 警告: 找不到 template.pptx，使用預設白底樣式。")

    # 2. 建立內容頁
    for i, page in enumerate(slides_content):
        # 取得版型設定
        layout_name = page.get('layout', 'content')
        
        # 為了保險，如果 Manager 指定了 comparison，我們暫時先導向 two_column (ID 3)
        # 因為 ID 4 需要填寫 4 個框框 (左右標題+左右內文)，邏輯較複雜，MVP 先用 ID 3
        if layout_name == 'comparison':
            config = LAYOUT_CONFIG['two_column']
        else:
            config = LAYOUT_CONFIG.get(layout_name, LAYOUT_CONFIG['content'])
        
        # 建立頁面
        try:
            slide = prs.slides.add_slide(prs.slide_layouts[config['id']])
        except IndexError:
            # 防呆：如果模板又換了，ID 超出範圍，回退到 ID 1
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            config = LAYOUT_CONFIG['content'] # 強制切換設定以免後面填錯
        
        # --- A. 填寫標題 ---
        title_idx = config.get('title_idx', 0)
        try:
            if slide.placeholders[title_idx].has_text_frame:
                slide.placeholders[title_idx].text = page.get('title', '')
        except Exception:
            # 如果連標題框都找不到 (例如空白頁)，就跳過
            pass

        # --- B. 填寫內文 ---
        content_data = page.get('content', '')
        if not content_data:
            continue

        # 雙欄邏輯 (針對 ID 3)
        if layout_name == 'two_column' or layout_name == 'comparison':
            if isinstance(content_data, list) and len(content_data) >= 2:
                # 填左欄
                try:
                    left_ph = slide.placeholders[config['left_idx']]
                    left_ph.text = str(content_data[0])
                except KeyError: pass
                
                # 填右欄
                try:
                    right_ph = slide.placeholders[config['right_idx']]
                    right_ph.text = str(content_data[1])
                except KeyError: pass
            else:
                # 如果資料不是 list，硬塞左欄
                try:
                    slide.placeholders[config['left_idx']].text = str(content_data)
                except KeyError: pass
        
        # 單欄邏輯 (包含封面、章節、內文)
        else:
            try:
                body_idx = config.get('body_idx')
                if body_idx is not None:
                    ph = slide.placeholders[body_idx]
                    
                    # 嘗試用 TextFrame 填寫以支援自動換行
                    if ph.has_text_frame:
                        ph.text_frame.text = str(content_data)
                        ph.text_frame.word_wrap = True
                    else:
                        ph.text = str(content_data)
            except KeyError:
                print(f"ℹ️ 第 {i+1} 頁 (Layout {config['id']}) 找不到 Index {body_idx} 的框，已跳過。")

    # 3. 儲存
    output_path = os.path.join(os.getcwd(), filename)
    prs.save(output_path)
    return output_path