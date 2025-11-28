# test_rag.py
import sys
import os

# 加入 src 路徑
sys.path.append(os.getcwd())

from src.config import Config
from src.tools.rag import ingest_file, rag_tool

def test():
    print("--- 📚 開始測試 RAG (文件讀取) ---")
    
    # 1. 檢查 Config
    try:
        Config.validate()
        print(f"✅ 設定讀取成功 (Using: {Config.MODEL_EMBEDDING})")
    except Exception as e:
        print(f"❌ 設定錯誤: {e}")
        return

    # 2. 測試讀取
    filename = "sample.pdf"  # 請確保有這個檔案
    if os.path.exists(filename):
        print(f"\n📂 讀取測試檔案: {filename} ...")
        print(ingest_file(filename))
    else:
        print(f"\n⚠️ 請放入 {filename} 以進行測試")

    # 3. 測試搜尋
    query = "這份文件的重點是什麼？"
    print(f"\n🔍 問: {query}")
    answer = rag_tool.invoke(query)
    print(f"答: {answer[:150]}...") # 預覽前150字

if __name__ == "__main__":
    test()