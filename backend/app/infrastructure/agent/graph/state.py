from typing import TypedDict


class GraphState(TypedDict, total=False):
    session_id: str
    user_id: str
    user_role: str
    message: str
    route: str
    retrieved_chunks: list[dict]
    research_findings: list[str]
    tool_results: list[dict]
    activities: list[dict]
    final_answer: str
    validation_passed: bool