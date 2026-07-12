from langgraph.graph import END, START, StateGraph

from app.infrastructure.agent.graph.state import GraphState


def build_agent_graph(nodes):
    graph = StateGraph(GraphState)
    graph.add_node("supervisor", nodes.supervisor)
    graph.add_node("retrieval", nodes.retrieval)
    graph.add_node("research", nodes.research)
    graph.add_node("response", nodes.response)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {"retrieval": "retrieval", "research": "research"},
    )
    graph.add_edge("retrieval", "response")
    graph.add_edge("research", "response")
    graph.add_edge("response", END)
    return graph.compile()
