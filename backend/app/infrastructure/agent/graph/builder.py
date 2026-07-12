from langgraph.graph import END, START, StateGraph

from app.domain.services.approval_gate import ApprovalGateService
from app.infrastructure.agent.graph.state import GraphState


def _route_after_supervisor(state: GraphState, approval_gate: ApprovalGateService) -> str:
    route = state.get("route", "retrieval")
    if approval_gate.requires_approval(route, state.get("message", "")):
        if approval_gate.is_approved(
            state.get("session_id", ""), request_approved=state.get("approved", False)
        ):
            return route
        return "human_approval"
    return route


def build_agent_graph(nodes, approval_gate: ApprovalGateService | None = None):
    gate = approval_gate or getattr(nodes, "_approval_gate", ApprovalGateService())
    graph = StateGraph(GraphState)
    graph.add_node("supervisor", nodes.supervisor)
    graph.add_node("human_approval", nodes.human_approval)
    graph.add_node("retrieval", nodes.retrieval)
    graph.add_node("research", nodes.research)
    graph.add_node("mcp_tools", nodes.mcp_tools)
    graph.add_node("python_analysis", nodes.python_analysis)
    graph.add_node("response", nodes.response)
    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        lambda state: _route_after_supervisor(state, gate),
        {
            "retrieval": "retrieval",
            "research": "research",
            "mcp_tools": "mcp_tools",
            "python_analysis": "python_analysis",
            "human_approval": "human_approval",
        },
    )
    graph.add_edge("retrieval", "response")
    graph.add_edge("research", "response")
    graph.add_edge("mcp_tools", "response")
    graph.add_edge("python_analysis", "response")
    graph.add_edge("human_approval", END)
    graph.add_edge("response", END)
    return graph.compile()
