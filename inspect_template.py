from pptx import Presentation
import os

def analyze_template(filename="template.pptx"):
    if not os.path.exists(filename):
        print(f"❌ 找不到 {filename}，將使用預設空白樣式。")
        return

    prs = Presentation(filename)
    print(f"✅ 成功讀取 {filename}")
    print("--- 版型清單 (Layouts) ---")
    
    for i, layout in enumerate(prs.slide_layouts):
        print(f"ID [{i}]: {layout.name}")

if __name__ == "__main__":
    # 如果你還沒放檔案，這行會報錯，請先放一個 template.pptx
    analyze_template()