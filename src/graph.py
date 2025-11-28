# src/graph.py
from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from src.agents.manager import manager_node
from src.agents.workers import writer_node

def build_graph():
    """
    建構簡報生成的 Agent 流程圖 (Workflow)
    """
    # 1. 初始化 Graph，使用我們定義好的 State
    workflow = StateGraph(AgentState)

    # 2. 加入節點 (Nodes)
    # 節點名稱可以自訂，這裡是 "manager" 和 "writer"
    workflow.add_node("manager", manager_node)
    workflow.add_node("writer", writer_node)

    # 3. 定義流程 (Edges)
    # 入口 -> Manager
    workflow.set_entry_point("manager")
    
    # Manager 做完 -> 交給 Writer
    workflow.add_edge("manager", "writer")
    
    # Writer 做完 -> 結束 (END)
    workflow.add_edge("writer", END)

    # 4. 編譯 Graph (這會產生一個可執行的 App)
    app = workflow.compile()
    
    return app

# 建立實例，讓外部可以 import 執行
agent_workflow = build_graph()