# Smart Deck AI Agent - 智慧簡報生成器

📖 專案簡介 (Introduction)

Smart Deck AI Agent 是一個基於 LangGraph 與 Google Gemini 的多代理（Multi-Agent）自動化簡報生成系統。

有別於市面上僅生成空泛條列式文字的工具，本專案旨在解決生成式 AI 在簡報製作上的「資訊密度不足」與「幻覺」問題。透過 RAG（檢索增強生成） 與 Google Web Search 的結合，Smart Deck 能深度理解使用者上傳的私有知識庫（PDF/TXT），並自動聯網補充最新數據，最終透過「規劃（Manager）—執行（Writer）」的協作模式，產出邏輯嚴密且排版精確的 PowerPoint 簡報。

✨ 核心亮點

高資訊密度：整合內部文件（RAG）與外部搜尋（Web Search），確保內容具備數據佐證。

Agentic Workflow：採用 Manager（規劃與反思）與 Writer（執行與排版）的職責分離架構。

自癒反思迴圈 (Self-Reflection Loop)：Manager Agent 會自我檢核大綱的邏輯性與數據完整性，若有缺漏會自動二次檢索。

精準版型控制：利用 Pydantic 結構化輸出（Structured Output）確保文字內容精準適配 PPT 版型（如雙欄比較、層級縮排）。

🏗️ 系統架構 (Architecture)

本系統採用 LangGraph 構建狀態機（State Graph），主要由以下三個代理角色組成：

Chat Assistant (前台助理)：

負責與使用者對話、意圖識別。

具備 read_knowledge_base (RAG) 與 Google Search 工具權限。

將蒐集到的資訊彙整至 Chat History。

Manager Agent (架構師/大腦)：

使用 Gemini 2.5 Pro 模型。

負責讀取對話紀錄、進行二次深度調查、規劃簡報大綱。

執行「反思迴圈」，檢查大綱是否缺乏數據或邏輯不通。

Writer Agent (排版工/手腳)：

負責資料清洗（Sanitization）與格式轉換。

使用 python-pptx 將結構化數據渲染至 template.pptx。

🛠️ 技術堆疊 (Tech Stack)

LLM Model: Google Gemini 2.5 Pro (Planning) & Flash (Response)

Orchestration: LangGraph, LangChain

Vector DB: ChromaDB (Local Persistence)

UI Framework: Streamlit

Tools: Google Custom Search API, PyPDFLoader, Python-pptx

Containerization: Docker, Docker Compose

🚀 快速開始 (Quick Start)

1. 前置需求

Python 3.10 以上

Google Cloud Project (需啟用 Custom Search API 與 Generative AI API)

專案目錄下必須包含 template.pptx 母片檔案

2. 下載專案

git clone [https://github.com/chenkuanchung/smart-deck-ai-agent.git](https://github.com/chenkuanchung/smart-deck-ai-agent.git)
cd smart-deck-ai-agent


3. 設定環境變數

請在專案根目錄建立 .env 檔案，並填入以下金鑰：

# .env
# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key

# Google Search API (用於聯網搜尋最新資訊)
GOOGLE_SEARCH_API_KEY=your_search_api_key
GOOGLE_CSE_ID=your_custom_search_engine_id

# 環境模式
ENV_MODE=dev


4. 啟動應用程式

方式 A：使用 Docker (推薦)

本專案包含完整的 Docker 支援，可一鍵啟動。

docker-compose up --build


啟動後，請瀏覽器訪問：http://localhost:8501

方式 B：本地運行

建議建立虛擬環境以避免套件衝突：

# 建立並啟用 venv
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 啟動 Streamlit
streamlit run src/app.py


📂 專案結構 (Project Structure)

smart-deck-ai-agent/
├── chromadb/               # 向量資料庫儲存目錄 (自動生成)
├── src/
│   ├── agents/
│   │   ├── manager.py      # Manager Agent (規劃與反思)
│   │   ├── workers.py      # Writer Agent (PPT 生成邏輯)
│   │   └── state.py        # LangGraph 狀態定義 (Pydantic Models)
│   ├── tools/
│   │   ├── rag.py          # RAG 檢索工具 (ChromaDB + Loader)
│   │   ├── search.py       # Google Search 工具
│   │   └── ppt_builder.py  # python-pptx 封裝函式
│   ├── app.py              # Streamlit 前端主程式
│   ├── config.py           # 設定檔與環境變數讀取
│   └── graph.py            # LangGraph 流程圖定義
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── template.pptx           # 簡報母片 (必須存在，否則會 fallback 至白底樣式)
└── README.md


📝 使用說明 (User Guide)

上傳資料：在左側邊欄上傳您的 PDF 或 TXT 文件（如產業報告、會議記錄）。

建立知識庫：系統會自動將文件向量化並存入 ChromaDB。

對話探索：在對話框輸入您的需求（例如：「請根據上傳文件，分析 2025 年的 AI 趨勢」）。Chat Assistant 會結合文件內容與網路搜尋回答您。

生成 PPT：點擊左側的 「✨ 生成 PPT」 按鈕。

觀察 AI 團隊（Manager & Writer）的思考與工作狀態。

待狀態顯示「✅ 完成」後，點擊下載按鈕取得 .pptx 檔案。

🔮 未來展望 (Roadmap)

[ ] 增強文件解析：整合 OCR 技術以支援掃描版 PDF。

[ ] 數據可視化：支援讀取數據並自動生成統計圖表 (Charts)。

[ ] 多模態生成：整合圖像生成模型 (如 Imagen) 自動配圖。

[ ] 持久化記憶：引入 Redis 實現跨 Session 的使用者偏好記憶。

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

Note: 本專案高度依賴 template.pptx 的母片設定來對應 Title, Content 與 Two-Column 版型。請勿隨意刪除該檔案。
