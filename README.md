# 📊 Smart Deck AI Agent

> Next-Gen Presentation Generator powered by LangGraph & Gemini 2.5

結合 RAG（內部知識庫）與 Google Search（外部聯網）的智慧簡報生成代理系統。

## 📖 專案簡介 (Introduction)

**Smart Deck AI Agent** 是一個解決「生成式 AI 簡報內容空泛」問題的自動化系統。有別於傳統的單次 Prompt 生成，本專案採用 **LangGraph** 多代理（Multi-Agent）架構，模擬真實世界的專業分工：

* **策略分析師 (Manager)**：負責閱讀文件、上網查證、規劃大綱，並具備「自我反思 (Self-Reflection)」能力，能自動修正邏輯漏洞。
* **執行製作 (Writer)**：負責資料清洗、格式標準化，並調用 python-pptx 引擎生成最終檔案。

透過 **RAG (Retrieval-Augmented Generation)** 與 **Google Search** 的雙重檢索機制，確保產出的簡報既有內部數據支撐（如財報、PDF），又能結合最新的市場動態。

---

## ✨ 核心亮點 (Key Features)

### 🧠 雙軌檢索機制 (Hybrid Retrieval):
* **RAG**: 使用 ChromaDB 解析並向量化使用者上傳的 PDF/TXT 文件。
* **Web Search**: 當內部資料不足時，自動觸發 Google Custom Search 聯網補充最新資訊。

### 🔄 自癒反思迴圈 (Self-Reflection Loop):
* **Manager Agent** 不僅是規劃者，還具備 Critique 能力。在生成大綱後，會自動檢查「是否有數據缺失？」、「邏輯是否通順？」，若有不足會自動發起二次檢索與修訂。

### 🎯 精準版型控制 (Layout Aware):
* 利用 Pydantic 定義嚴格的 Structured Output，確保 AI 生成的內容能精準對應到 PPT 的標題頁、雙欄比較、內容頁等版型。

### ⚡ 最新模型驅動：
* **Planning**: 使用邏輯推理強大的 **Gemini 2.5 Pro**。
* **Response**: 使用速度極快的 **Gemini 2.5 Flash**。

---

## 🛠️ 技術堆疊 (Tech Stack)

* **LLM Orchestration**: LangGraph, LangChain
* **Models**: Google Gemini 2.5 Pro & Flash
* **Vector Database**: ChromaDB (Local Persistence)
* **Web UI**: Streamlit
* **PPT Engine**: python-pptx
* **Tools**: Google Custom Search API, PyPDFLoader

---

## 🚀 快速開始 (Quick Start)

### 1. 前置需求 (Prerequisites)
您需要申請以下 Google 服務的金鑰：

* **Google Gemini API Key**: [Get API Key](https://aistudio.google.com/)
* **Google Custom Search API** (用於聯網搜尋): [Console](https://console.cloud.google.com/)
* **Programmable Search Engine ID (CSE ID)**: [Setup](https://programmablesearchengine.google.com/)

### 2. 安裝與設定 (Installation)

#### 方法 A：使用 Docker (推薦，環境最乾淨)

```bash
# 1. Clone 專案
git clone [https://github.com/chenkuanchung/smart-deck-ai-agent.git](https://github.com/chenkuanchung/smart-deck-ai-agent.git)
cd smart-deck-ai-agent

# 2. 設定環境變數
# 請參考專案根目錄，建立 .env 檔案
touch .env
```
```Ini, TOML
.env 檔案範例：

GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_SEARCH_API_KEY=your_search_api_key
GOOGLE_CSE_ID=your_cse_id
ENV_MODE=dev
```
```bash
# 3. 啟動服務
docker-compose up --build
```
服務啟動後，請瀏覽器訪問：http://localhost:8501

#### 方法 B：本地開發 (Local Development)

```bash
# 1. 建立虛擬環境 (Python 3.10+)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 確保 template.pptx 存在於根目錄 (專案必須)

# 4. 啟動 Streamlit
streamlit run src/app.py
```

## 📂 專案結構 (Project Structure)

```Plaintext
smart-deck-ai-agent/
├── chromadb/               # 向量資料庫儲存目錄 (自動生成)
├── src/
│   ├── agents/
│   │   ├── manager.py      # [核心] Manager Agent：規劃與反思邏輯
│   │   ├── workers.py      # [執行] Writer Agent：PPT 生成與清洗
│   │   └── state.py        # LangGraph State 定義 (Pydantic Models)
│   ├── tools/
│   │   ├── rag.py          # RAG 工具 (ChromaDB Ingest & Query)
│   │   ├── search.py       # Google Search 工具封裝
│   │   └── ppt_builder.py  # python-pptx 版型對應邏輯
│   ├── app.py              # Streamlit 前端主程式
│   ├── config.py           # 設定檔與環境變數讀取
│   └── graph.py            # Agent Graph 流程圖定義
├── template.pptx           # PPT 母片 (必須包含 Title/Content/Two-Column 版型)
├── docker-compose.yml      # Docker 編排檔
├── Dockerfile              # Docker 映像檔定義
└── requirements.txt        # Python 依賴清單
```

## 📝 使用指南 (User Guide)

1.  **上傳知識庫**：
    * 在左側 Sidebar 上傳 PDF 或 TXT 文件（如產業報告、會議記錄）。
    * 系統會自動進行向量化，成功後顯示 ✅ 已存入知識庫。

2.  **對話探索**：
    * 在對話框輸入您的需求。
    * 範例：「請根據上傳文件，分析 2025 年的 AI 趨勢，並補充網路上最新的競爭對手數據。」
    * Chat Assistant 會結合文件內容與網路搜尋回答您。

3.  **生成 PPT**：
    * 點擊左側的 「✨ 生成 PPT」 按鈕。
    * 觀察 Log：您會看到 Manager 正在規劃架構，甚至觸發 **自我反思 (Self-Reflection)** 來補強數據。

4.  **下載成果**：
    * 待狀態顯示「✅ 完成」後，點擊下載按鈕取得 `.pptx` 檔案。

---

## ⚠️ 常見問題 (Troubleshooting)

**Q: 生成的 PPT 只有標題沒有內容？**
A: 請檢查您的 `template.pptx`。本系統依賴母片索引 (Layout ID) 來填入內容，預設為 0:Title, 1:Content, 2:Section, 3:Two-Column。

**Q: 出現 GoogleSearchAPIWrapper 相關錯誤？**
A: 請確認 `.env` 中的 `Google Search_API_KEY` 與 `GOOGLE_CSE_ID` 是否正確啟用且配額充足。

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

<div align="center">
Made with ❤️ by KC (Me)
</div>

