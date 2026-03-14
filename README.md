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
> 負責深度思考與邏輯架構，由高智商的大語言模型 (如 Gemini 2.5 Pro) 驅動。

* **結構化規劃**：將 Chat Agent 蒐集到的資訊，轉化為嚴謹的 `PresentationOutline` (Pydantic Model)。
* **真實文案產出 (Real Copywriting)**：內建強大的防呆機制，嚴格禁止使用「這裡放封面」、「結語建議」等無意義的描述性廢話，確保生成的每一句話都是能直接印在投影片上的專業文案。
* **自我反思 (Self-Reflection)**：具備 Critique 能力。在產出大綱後，會自動檢查：「數據是否夠新？」、「邏輯是否通順？」。若發現缺漏，會**自主發起二次檢索**來補強內容。
* **層級控制**：精準定義每個重點的 Level (0-2) 與 Column (左/右欄)。

### 3. 執行製作 (Writer Agent) —— **The Hands** ✍️
> **"The Builder"** - 位於 `src/agents/workers.py` (LangGraph Node)
>
> 負責將規劃好的藍圖，轉化為實際的 `.pptx` 檔案。

* **資料清洗 (Sanitization)**：修復 Markdown 格式錯誤，過濾 LLM 偶爾殘留的程式碼區塊 (Code Blocks) 與多餘符號，確保輸出內容符合 PPT 的乾淨規範。
* **版型適配 (Layout Adapter)**：根據內容屬性，自動選擇 `title`、`section`、`content` 或 `two_column` 母片版型。
* **高容錯引擎**：操作 `python-pptx` 進行最終渲染。內建佔位符與字體溢出防護機制，即使遇到使用者上傳不規範的自訂母片，也能確保系統穩定運行不崩潰。

---

## ✨ 關鍵功能 (Key Features)

### 🤝 人機協作中斷機制 (Human-in-the-Loop)
拒絕傳統 AI 簡報工具的「盲盒式生成」！本系統利用 LangGraph 的 Checkpointer 機制，會在 Manager 規劃完大綱後「自動暫停」並進入編輯模式。
使用者擁有 100% 的內容掌控權：您不僅可以直接在畫面上修改 JSON 草稿，還能呼叫**「AI 大綱微調助理」**下達局部修改指令（例如：「把第二頁拆成兩頁」或「語氣改活潑一點」），確認結構完美後再放行給 Writer 渲染。

### 🧠 雙軌檢索機制 (Hybrid Retrieval)
拒絕幻覺，確保每一頁簡報都有憑有據：
* **RAG (內部知識)**：使用 ChromaDB 解析使用者上傳的 PDF/TXT。底層實作 Session-based 記憶體快取機制，避免重複建立索引，大幅降低大文件的檢索延遲與記憶體消耗。
* **Web Search (外部聯網)**：當內部資料不足或過時，Chat Agent 與 Manager 均可觸發 Google Custom Search 抓取最新市場動態與精確數據。

### 🔄 自癒反思迴圈 (Self-Healing Reflection)
Manager Agent 不會只生成一次就交差。它會審視自己的草稿，若發現論點缺乏數據支持，或出現「這裡放圖片」、「結語」等無意義的佔位符，系統會自動執行 **"Refinement Loop"**，重新搜尋並修正大綱，確保產出的是真實且專業的簡報文案。

### 🎯 嚴格結構化輸出 (Strict Structured Output)
全系統採用 Pydantic 進行資料流與型別控制。從 Manager 的大綱規劃到 Writer 的版面渲染，全程確保 AI 不會生成「格式錯誤」或「無法解析」的內容，完美對應 PPT 的各種母片格式與縮排層級。

---

## 🛠️ 技術堆疊 (Tech Stack)

* **LLM Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/), LangChain
* **Models**:
    * **Planning & Reasoning**: Google Gemini 2.5 Pro (負責複雜邏輯推理與大綱規劃)
    * **Chat & Execution**: Google Gemini 2.5 Flash (負責快速對話與多工具調用)
    * *(💡 開發者提示：由於 2.5 系列模型在免費層級的配額極低，若您未綁定 Google Cloud 帳單，強烈建議在 `src/config.py` 中全面改用每日額度高達 1000 次的 `gemini-2.5-flash-lite`，以獲取最順暢的開發與測試體驗。)*
* **Frontend**: Streamlit (提供流暢的對話介面、檔案上傳與 LangGraph 狀態機操控)
* **Vector Database**: ChromaDB (本地持久化儲存，並結合 Session 記憶體快取優化效能)
* **PPT Engine**: python-pptx (負責底層 PPTX 的 XML 操作、佔位符解析與母片渲染)
* **Tools & Data Validation**: Google Custom Search API, PyPDFLoader, Pydantic (負責全域資料結構的嚴格型別驗證)

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

---

## 📂 專案結構 (Project Structure)

```text
smart-deck-ai-agent/
├── src/
│   ├── app.py              # [UI/Chat] 首席策略分析師 (Streamlit 主程式)
│   ├── graph.py            # [Flow] LangGraph 定義 Manager -> Writer 工作流
│   ├── agents/
│   │   ├── manager.py      # [Brain] 架構規劃師 (規劃、反思與防呆機制)
│   │   ├── workers.py      # [Hand] 執行製作 (資料清洗與 PPT 渲染)
│   │   └── state.py        # [Schema] Pydantic 嚴格資料結構定義
│   ├── tools/
│   │   ├── rag.py          # [Memory] 向量資料庫操作 (內建 Session 快取優化)
│   │   ├── search.py       # [Eyes] Google Custom Search 封裝工具
│   │   └── ppt_builder.py  # [Engine] python-pptx 核心排版引擎
│   └── config.py           # 全域設定與模型切換 (Dev/Prod Mode)
├── template.pptx           # PPT 核心母片 (必須包含對應的 Layout 與 Placeholder 索引)
├── uploads/                # [Storage] RAG 文件上傳暫存區 (運行時自動生成，支援 Docker Volume 掛載)
├── outputs/                # [Storage] 最終生成的 PPTX 存放區 (運行時自動生成，支援 Docker Volume 掛載)
├── docker-compose.yml      # 容器化部署設定 (已配置持久化儲存路徑)
├── .dockerignore           # 避免 Docker Build 過慢與映像檔肥大的排除清單
└── requirements.txt        # Python 依賴套件清單
```

---

## 📝 使用指南 (User Guide)

1.  **上傳知識庫 (Knowledge Ingestion)**：
    * 在左側 Sidebar 上傳 PDF 或 TXT 文件（如產業報告、內部會議記錄）。
    * 系統會自動進行向量化處理，成功後會顯示「✅ 已存入知識庫」。
    * Chat Agent 後續在回答時，會優先閱讀並引用這些文件。

2.  **對話探索 (Conversational Exploration)**：
    * 在中央對話框與 *Chat Agent* 進行互動。
    * 💡 *範例：「請根據上傳文件，分析 2025 年的 AI 趨勢，並補充網路上最新的競爭對手數據。」*
    * Agent 會自動判斷意圖，調用 RAG 查閱文件，並視需求使用 Google Search 補足外部最新資訊。

3.  **規劃與協作編輯 (Human-in-the-Loop)**：
    * 點擊左側生成控制台的 **「✨ 1. 規劃簡報大綱」** 按鈕。
    * 系統會將對話上下文打包給 Manager Agent 進行深度規劃，並產出 JSON 格式的簡報草稿。
    * ⚠️ **系統進入暫停模式**：此時您可以直接在畫面上修改大綱文字，或使用下方的「AI 大綱微調助理」輸入指令（如：「將第三頁拆成兩頁」）進行局部結構微調。

4.  **確認與生成 (Render & Download)**：
    * 經人工審閱與編輯確認無誤後，點擊 **「✅ 2. 確認並排版」**。
    * 系統才會正式放行，驅動 Writer Agent 進行最終的 PPTX 渲染與版型適配。
    * 待狀態顯示「✅ 完成」後，即可點擊下載按鈕取得您的 `.pptx` 簡報檔案。

---

## ⚠️ 常見問題 (Troubleshooting)

**Q: 一直出現 `429 Rate Limit` 或 `Quota exceeded` 錯誤，無法生成大綱或對話？**
A: 這是因為本系統具備「平行搜尋與推理」能力，會在瞬間發送多個請求。如果您使用的是 Gemini 免費層級 (Free Tier)，官方針對最新的 2.5 系列模型（如 `gemini-2.5-pro` 與 `gemini-2.5-flash`）設有極其嚴格的配額限制（通常為每日 20 次請求），非常容易觸發 429 錯誤。
* **🛠️ 解法 1 (免費開發推薦)**：進入 `src/config.py`，將 `MODEL_SMART` 與 `MODEL_FAST` 皆改為 `gemini-2.5-flash-lite`。該輕量版模型在免費層級擁有每日高達 1,000 次的額度，足以應付順暢的開發與測試。
* **🚀 解法 2 (解鎖完全體效能)**：前往 Google AI Studio 綁定 Google Cloud 帳單並升級至 Tier 1。這將大幅提升您的 RPM/RPD 上限，釋放 Manager Agent 規劃複雜大綱的完整潛能。

**Q: 為什麼「雙欄版型 (Two-Column)」的內容左右錯亂，或是右邊的內容不見了？**
A: 這是由於您自訂的 PPT 母片中，佔位符 (Placeholder) 的建立順序與系統預期不符。請打開您的 `template.pptx` 進入「投影片母片」檢視，並確保您的「兩項內容 (Two Content)」版型建立順序**嚴格遵守**以下規則：
1. **主標題**必須是第一順位 (`idx=0`)
2. **左欄文字框**必須是第二順位 (`idx=1`)
3. **右欄文字框**必須是第三順位 (`idx=2`)
*(💡 快速修復提示：若順序錯誤，最簡單的方法是在母片中將左右兩個文字框都刪除，先重新插入「左邊」的文字框，再插入「右邊」的文字框，存檔即可修正索引順序。)*

**Q: 生成的 PPT 只有標題，完全沒有內文？**
A: 請檢查您的 `template.pptx`。本系統依賴母片索引 (Layout ID) 來填入內容，系統預設對應的 Layout 順序為 `0:Title`, `1:Content`, `2:Section`, `3:Two-Column`。若您的母片版面配置與此不符，可能導致程式找不到對應的文字框而略過寫入。

**Q: 出現 GoogleSearchAPIWrapper 相關錯誤或無法查網頁？**
A: 請確認根目錄下 `.env` 檔案中的 `GOOGLE_SEARCH_API_KEY` 與 `GOOGLE_CSE_ID` 是否正確填寫、是否已在 Google Cloud Console 中啟用 Custom Search API，且配額是否充足。

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

<div align="center">
Made with ❤️ by KC (Me)
</div>

