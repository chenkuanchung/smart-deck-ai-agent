# src/tools/search.py
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool
from pydantic import BaseModel, Field
from src.config import Config

# 初始化 Google Search Wrapper
# 它會自動讀取我們在 Config 中設定好的 Key
search_wrapper = GoogleSearchAPIWrapper(
    google_api_key=Config.GOOGLE_SEARCH_API_KEY,
    google_cse_id=Config.GOOGLE_CSE_ID,
    k=5
)

# 定義參數架構 (Schema)
class SearchInput(BaseModel):
    query: str = Field(description="The search query string. Cannot be empty.")

def search_func(query: str):
    """
    執行 Google 搜尋並回傳結果摘要。
    為了節省 Token，我們只回傳前 5 筆結果的 Snippet。
    """
    # [關鍵修正] 防呆機制：處理空 Query
    if not query or query.strip() == "" or query == "None":
        return "⚠️ 搜尋失敗：未提供搜尋關鍵字。請分析使用者的對話內容，提取出具體的搜尋詞（例如：'2024 AI 趨勢'），然後再試一次。"

    try:
        # k=5 代表抓取前 5 筆
        results = search_wrapper.run(query)
        
        # [優化] 如果搜尋結果為空，也要回傳明確訊息
        if not results:
            return f"找不到關於 '{query}' 的相關資訊。"
            
        return results
    except Exception as e:
        return f"搜尋發生錯誤: {str(e)}"

# 將函式包裝成 LangChain 的 Tool 物件
# 這樣之後的 Agent 才能夠「看到」並使用它
search_tool = Tool(
    name="google_search",
    description="用於搜尋網路上的最新資訊、新聞或技術文件。輸入必須是具體的搜尋關鍵字，不能為空。",
    func=search_func,
    args_schema=SearchInput
)