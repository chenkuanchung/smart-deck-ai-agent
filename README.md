# 📊 Smart Deck AI Agent

> **Next-Gen Presentation Generator powered by LangGraph & Gemini 2.5** > 結合 RAG（內部知識庫）與 Google Search（外部聯網）的智慧簡報生成代理系統。

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 專案簡介 (Introduction)

**Smart Deck AI Agent** 是一個解決「生成式 AI 簡報內容空泛」問題的實驗性專案。有別於傳統的單次 Prompt 生成，本系統採用 **多代理（Multi-Agent）架構**，模擬真實世界的專業分工：

1.  **策略分析師 (Manager)**：負責閱讀文件、上網查證、規劃大綱，並具備「自我反思 (Self-Reflection)」能力，能自動修正邏輯漏洞。
2.  **執行製作 (Writer)**：負責資料清洗、格式標準化，並調用 PPT 引擎生成最終檔案。

透過 **RAG (Retrieval-Augmented Generation)** 與 **Google Search** 的雙重檢索機制，確保產出的簡報既有內部數據支撐，又能結合最新的市場動態。

---

## ✨ 核心亮點 (Key Features)

* **🧠 雙軌檢索機制 (Hybrid Retrieval)**：
    * **RAG**: 使用 `ChromaDB` 解析並向量化使用者上傳的 PDF/TXT 文件（如財報、會議記錄）。
    * **Web Search**: 當內部資料不足時，自動觸發 `Google Custom Search` 聯網補充最新資訊（如競品動態、最新股價）。
* **🔄 自癒反思迴圈 (Self-Reflection Loop)**：
    * `Manager` Agent 不僅是規劃者，還具備 Critique 能力。在生成大綱後，會自動檢查「是否有數據缺失？」、「邏輯是否通順？」，若有不足會自動發起二次檢索與修訂。
* **🎯 精準版型控制 (Layout Aware)**：
    * 利用 Pydantic 定義嚴格的 `Structured Output`，確保 AI 生成的內容能精準對應到 PPT 的標題頁、雙欄比較、內容頁等版型，杜絕格式跑版。
* **⚡ 最新模型驅動**：
    * 規劃層 (Planning)：使用邏輯推理強大的 **Gemini 2.5 Pro**。
    * 反應層 (Response)：使用速度極快的 **Gemini 2.5 Flash**。

---

## 🏗️ 系統架構 (Architecture)

本專案基於 **LangGraph** 構建狀態機（State Graph），流程如下：

```mermaid
graph LR
    A[User Input] --> B(Chat Assistant);
    B -->|意圖識別 & RAG/Search| C{資料充足?};
    C -->|No| B;
    C -->|Yes| D[Manager Agent];
    D -->|Drafting| E[Initial Outline];
    E -->|Self-Reflection| F{Critique};
    F -->|Needs Data| B;
    F -->|Perfect| G[Writer Agent];
    G -->|Sanitization & Rendering| H[Final PPT];
