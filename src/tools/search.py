# src/tools/search.py
import requests
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.tools import Tool, tool
from pydantic import BaseModel, Field
from src.config import Config

# 初始化 Google Search Wrapper
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
    執行 Google 搜尋並回傳結果摘要與明確的網址。
    """
    if not query or query.strip() == "" or query == "None":
        return "⚠️ 搜尋失敗：未提供搜尋關鍵字。請分析使用者的對話內容，提取出具體的搜尋詞，然後再試一次。"

    try:
        # 用 .results() 取得結構化字典，確保一定拿得到 'link'
        raw_results = search_wrapper.results(query, 5)
        
        if not raw_results:
            return f"找不到關於 '{query}' 的相關資訊。"
            
        # 格式化輸出，強制把「網址」獨立列出，讓 LLM 方便抓取
        formatted_results = []
        for idx, r in enumerate(raw_results, 1):
            title = r.get("title", "無標題")
            link = r.get("link", "")
            snippet = r.get("snippet", "無摘要")
            formatted_results.append(f"【結果 {idx}】\n標題：{title}\n網址：{link}\n摘要：{snippet}\n")
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"搜尋發生錯誤: {str(e)}"

search_tool = Tool(
    name="google_search",
    description="用於搜尋網路上的最新資訊。回傳結果包含標題、網址與摘要。若需要閱讀全文，請擷取結果中的「網址」並呼叫 read_webpage 工具。",
    func=search_func,
    args_schema=SearchInput
)

@tool
def read_webpage(url: str) -> str:
    """
    [網頁深度閱讀器]
    當你使用 google_search 找到相關網址，但摘要內容不夠完整（例如需要具體數據、完整新聞、財報細節）時，
    請將該網址 (URL) 傳入此工具，以獲取網頁的完整純文字內容。
    """
    try:
        clean_url = url.strip().strip('"').strip("'")
        target_url = f"https://r.jina.ai/{clean_url}"
        
        response = requests.get(target_url, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            return content[:10000] + "\n...(文章過長已於尾部截斷)"
        
        return f"無法讀取網頁，狀態碼：{response.status_code}"
    except Exception as e:
        return f"讀取網頁發生錯誤：{str(e)}"