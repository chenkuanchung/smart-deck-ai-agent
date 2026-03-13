# src/graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver # 引入記憶體套件
from src.agents.state import AgentState
from src.agents.manager import manager_node
from src.agents.workers import writer_node

def build_graph():
    """
    建構簡報生成的 Agent 流程圖 (Workflow)
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("manager_node", manager_node)
    workflow.add_node("writer_node", writer_node)

    workflow.set_entry_point("manager_node")
    workflow.add_edge("manager_node", "writer_node")
    workflow.add_edge("writer_node", END)

    # 實例化記憶體機制，讓 Graph 可以記住每一步的狀態並支援暫停
    memory = MemorySaver()
    
    # 設定 checkpointer，並規定在 writer_node 執行前「強制暫停」
    app = workflow.compile(checkpointer=memory, interrupt_before=["writer_node"])
    
    return app

# 建立實例
agent_workflow = build_graph()