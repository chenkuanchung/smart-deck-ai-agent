# src/graph.py
from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from src.agents.manager import manager_node
from src.agents.workers import writer_node

def build_graph():
    """
    建構簡報生成的 Agent 流程圖 (Workflow)
    
    【架構說明】：
    採用線性流程：Manager (規劃+反思) -> Writer (執行+排版) -> End
    
    1. Manager Node: 
       - 負責所有「大腦」工作，包括 RAG 檢索、架構規劃、自我反思 (Self-Reflection)。
       - 輸出：完整的 PresentationOutline 物件。
       
    2. Writer Node:
       - 負責所有「手腳」工作，包括資料清洗、格式轉換、PPT 渲染。
       - 輸出：PPT 檔案路徑。
    """
    # 1. 初始化 Graph
    workflow = StateGraph(AgentState)

    # 2. 加入節點
    workflow.add_node("manager", manager_node)
    workflow.add_node("writer", writer_node)

    # 3. 定義流程
    # 入口 -> Manager (大腦)
    workflow.set_entry_point("manager")
    
    # Manager -> Writer (手腳)
    # 這裡使用直接連接，因為 Manager 內部已經處理了錯誤捕捉，保證會產出 Outline (即使是錯誤提示頁)
    workflow.add_edge("manager", "writer")
    
    # Writer -> 結束
    workflow.add_edge("writer", END)

    # 4. 編譯
    app = workflow.compile()
    
    return app

# 建立實例
agent_workflow = build_graph()