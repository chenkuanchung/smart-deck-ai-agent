# src/tools/search.py
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool
from src.config import Config

# 初始化 Google Search Wrapper
# 它會自動讀取我們在 Config 中設定好的 Key
search_wrapper = GoogleSearchAPIWrapper(
    google_api_key=Config.GOOGLE_SEARCH_API_KEY,
    google_cse_id=Config.GOOGLE_CSE_ID,
    k=5
)

def search_func(query: str):
    """
    執行 Google 搜尋並回傳結果摘要。
    為了節省 Token，我們只回傳前 5 筆結果的 Snippet。
    """
    try:
        # k=5 代表抓取前 5 筆
        return search_wrapper.run(query)
    except Exception as e:
        return f"搜尋發生錯誤: {str(e)}"

# 將函式包裝成 LangChain 的 Tool 物件
# 這樣之後的 Agent 才能夠「看到」並使用它
search_tool = Tool(
    name="google_search",
    description="用於搜尋網路上的最新資訊、新聞或技術文件。輸入應該是具體的搜尋關鍵字。",
    func=search_func
)