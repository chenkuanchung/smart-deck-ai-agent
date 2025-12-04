# 📊 Smart Deck AI Agent

> **Next-Gen Presentation Generator powered by LangGraph & Gemini 2.5**
>
> 結合 **前哨諮詢（Chat）**、**深度規劃（Manager）** 與 **精準執行（Writer）** 的全自動化簡報生成系統。

**Smart Deck AI Agent** 是一個解決「生成式 AI 簡報內容空泛」問題的專業級解決方案。有別於傳統「一句話生成 PPT」的單向模式，本專案模擬真實世界的專業顧問團隊，由三個不同職能的 AI Agent 協作完成任務。

---

## 🤖 核心架構：三代理協作系統 (The Triple-Agent Architecture)

本系統由三位各司其職的 AI Agent 組成，模擬從「諮詢」到「規劃」再到「製作」的專業流程：

### 1. 首席策略分析師 (Lead Strategy Analyst) —— **The Chat Agent** 🌟
> **"The Consultant"** - 位於 `src/app.py`
>
> **這是系統中工具最豐富、反應最靈活的角色。** 它不直接寫 PPT，而是作為使用者的「簡報顧問」。

* **全能工具箱**：它是唯一能同時靈活調度 `read_knowledge_base` (RAG) 與 `Google Search` (Web) 的角色，負責在前期的對話中蒐集資訊。
* **意圖偵測 (Intent Detection)**：能判斷使用者是想「探索話題」、「驗證數據」還是「比較分析」，並據此決定搜尋策略。
* **模糊檢查 (Ambiguity Check)**：當指令太籠統（如：「做個 AI 簡報」）時，它會拒絕瞎做，而是反問使用者：「目標受眾是誰？想強調技術還是市場？」
* **任務**：透過對話將模糊的想法，轉化為具備高資訊密度的素材，為後續的 Manager 鋪路。

### 2. 架構規劃師 (Manager Agent) —— **The Brain** 🧠
> **"The Planner"** - 位於 `src/agents/manager.py` (LangGraph Node)
>
> 負責深度思考與邏輯架構，由高智商的 **Gemini 2.5 Pro** 驅動。

* **結構化規劃**：將 Chat Agent 蒐集到的資訊，轉化為嚴謹的 `PresentationOutline` (Pydantic Model)。
* **自我反思 (Self-Reflection)**：具備 Critique 能力。在產出大綱後，會自動檢查：「數據是否夠新？」、「邏輯是否通順？」。若發現缺漏，會**自主發起二次檢索**來補強內容。
* **層級控制**：精準定義每個重點的 Level (0-2) 與 Column (左/右欄)。

### 3. 執行製作 (Writer Agent) —— **The Hands** ✍️
> **"The Builder"** - 位於 `src/agents/workers.py` (LangGraph Node)
>
> 負責將規劃好的藍圖，轉化為實際的 `.pptx` 檔案。

* **資料清洗 (Sanitization)**：修復 Markdown 格式錯誤，確保輸出內容符合 PPT 規範。
* **版型適配 (Layout Adapter)**：根據內容屬性，自動選擇 `title`、`section`、`content` 或 `two_column` 母片版型。
* **引擎調用**：操作 `python-pptx` 進行最終渲染。

---

## ✨ 關鍵功能 (Key Features)

### 🧠 雙軌檢索機制 (Hybrid Retrieval)
拒絕幻覺，確保每一頁簡報都有憑有據：
* **RAG (內部知識)**：使用 ChromaDB 解析使用者上傳的 PDF/TXT (如財報、內部會議記錄)。
* **Web Search (外部聯網)**：當內部資料不足或過時，Chat Agent 與 Manager 均可觸發 Google Custom Search 抓取最新市場動態。

### 🔄 自癒反思迴圈 (Self-Healing Reflection)
Manager Agent 不會只生成一次就交差。它會審視自己的草稿，若發現論點缺乏數據支持，會自動執行 **"Refinement Loop"**，重新搜尋並修正大綱。

### 🎯 嚴格結構化輸出 (Strict Structured Output)
全系統採用 Pydantic 進行資料流控制，確保 AI 不會生成「格式錯誤」或「無法解析」的內容，完美對應 PPT 母片格式。

---

## 🛠️ 技術堆疊 (Tech Stack)

* **LLM Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/), LangChain
* **Models**:
    * **Planning**: Google Gemini 2.5 Pro (高推理能力)
    * **Chat/Response**: Google Gemini 2.5 Flash (高回應速度)
* **Frontend**: Streamlit (提供 Chat Interface 與 File Uploader)
* **Vector Database**: ChromaDB (Local Persistence)
* **PPT Engine**: python-pptx
* **Tools**: Google Custom Search API, PyPDFLoader

---

## 🚀 快速開始 (Quick Start)

### 1. 前置需求 (Prerequisites)
請確保擁有以下 Google 服務金鑰：
* **Google Gemini API Key**: [AI Studio](https://aistudio.google.com/)
* **Google Custom Search API**: [Cloud Console](https://console.cloud.google.com/)
* **Search Engine ID (CSE ID)**: [Programmable Search](https://programmablesearchengine.google.com/)

### 2. 安裝與執行 (Installation)

#### 方法 A：使用 Docker (推薦) 🐳

```bash
# 1. Clone 專案
git clone https://github.com/chenkuanchung/smart-deck-ai-agent.git
cd smart-deck-ai-agent

# 2. 設定環境變數
# 請參考專案根目錄，建立 .env 檔案
touch .env
```
```Ini, TOML
# .env 檔案範例：
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
├── src/
│   ├── app.py              # [UI/Chat] 首席策略分析師 (Streamlit 主程式)
│   ├── graph.py            # [Flow] LangGraph 定義 Manager -> Writer 流程
│   ├── agents/
│   │   ├── manager.py      # [Brain] 架構規劃師 (Planning & Reflection)
│   │   ├── workers.py      # [Hand] 執行製作 (PPT Generation)
│   │   └── state.py        # [Schema] Pydantic 資料結構定義
│   ├── tools/
│   │   ├── rag.py          # [Memory] 向量資料庫操作
│   │   ├── search.py       # [Eyes] Google Search 工具
│   │   └── ppt_builder.py  # [Engine] python-pptx 封裝
│   └── config.py           # 環境變數設定
├── template.pptx           # PPT 母片 (必須包含對應 Layout)
├── docker-compose.yml
└── requirements.txt
```

## 📝 使用指南 (User Guide)

1.  **上傳知識庫**：
    * 在左側 Sidebar 上傳 PDF 或 TXT 文件（如產業報告、會議記錄）。
    * 系統會自動進行向量化，成功後顯示 ✅ 已存入知識庫。
    * Chat Agent 會優先閱讀這些文件。

2.  **對話探索**：
    * 在對話框與 *Chat Agent* 互動。
    * 範例：「請根據上傳文件，分析 2025 年的 AI 趨勢，並補充網路上最新的競爭對手數據。」
    * Chat Agent 會自動調用 RAG 查文件，並用 Google Search 補足分析師評論。

3.  **生成 PPT**：
    * 點擊左側的 「✨ 生成 PPT」 按鈕。
    * 系統會將對話上下文打包，交給 Manager Agent 進行深度規劃與反思。
    * 最後由 Writer Agent 產出檔案。

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

