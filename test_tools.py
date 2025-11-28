# test_tools.py
import sys
import os

# 將專案根目錄加入 Python 路徑，這樣才能 import src
sys.path.append(os.getcwd())

from src.config import Config
from src.tools.search import search_tool
from src.tools.ppt_builder import create_presentation

def test():
    print("--- 🛠️ 開始工具測試 (Version 2: Template 驗證) ---")
    
    # 1. 測試設定檔讀取
    try:
        Config.validate()
        print("✅ Config 設定讀取成功！")
    except Exception as e:
        print(f"❌ Config 設定錯誤: {e}")
        return

    # 2. 測試 Google 搜尋 (簡單測試連線)
    print("\n🔍 正在測試 Google Search...")
    try:
        # 搜尋一個簡單的關鍵字
        result = search_tool.invoke("Python 3.12 release date")
        print(f"✅ 搜尋成功 (已回傳 {len(result)} 字的摘要)")
    except Exception as e:
        print(f"❌ 搜尋失敗: {e}")

    # 3. 測試 PPT 生成 (重點驗收！)
    print("\n📊 正在測試 PPT 生成 (包含單欄與雙欄)...")
    
    # 這是我們要測試的假資料，特別設計來對應你的 Template ID
    slides = [
        # 對應 ID [0]
        {
            "layout": "title", 
            "title": "Smart Deck Agent", 
            "content": "自動化簡報測試報告"
        },
        # 對應 ID [2]
        {
            "layout": "section", 
            "title": "第一章：版型測試", 
            "content": ""
        },
        # 對應 ID [3]
        {
            "layout": "content", 
            "title": "測試：一般單欄 (Content)", 
            "content": "1. 這一頁應該是單欄排版\n2. 文字應該在左邊或中間\n3. 使用的是 ID [3]"
        },
        # 對應 ID [5] - 關鍵測試點！
        {
            "layout": "two_column", 
            "title": "測試：左右雙欄 (Two Column)", 
            "content": [
                "【左欄內容】\n這是左邊的文字區塊。\n這裡適合放優點或是比較項目的 A 方。", 
                "【右欄內容】\n這是右邊的文字區塊。\n這裡適合放缺點或是比較項目的 B 方。"
            ]
        }
    ]
    
    try:
        # 這裡會讀取目錄下的 template.pptx
        path = create_presentation("測試簡報", slides, template_path="template.pptx", filename="test_output.pptx")
        
        if os.path.exists(path):
            print(f"✅ PPT 生成成功！")
            print(f"📂 檔案位置: {path}")
            print("👉 請務必打開檔案檢查：最後一頁是否真的變成了「左右兩欄」？")
        else:
            print("❌ 檔案似乎沒有被建立。")
            
    except Exception as e:
        print(f"❌ PPT 生成失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()