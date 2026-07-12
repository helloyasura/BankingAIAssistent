from collections.abc import AsyncIterator

from app.domain.entities.agent_state import AgentActivity, AgentNode, AgentState
from app.domain.entities.user import User
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.infrastructure.agent.graph.builder import build_agent_graph
from app.infrastructure.agent.graph.nodes import GraphNodes


class LangGraphOrchestrator(AgentOrchestratorPort):
    def __init__(self, vector_store: VectorStorePort, llm: LLMPort) -> None:
        nodes = GraphNodes(vector_store, llm)
        self._graph = build_agent_graph(nodes)

    async def run(
        self, user: User, session_id: str, message: str, *, approved: bool = False
    ) -> AgentState:
        result = await self._graph.ainvoke(
            {
                "session_id": session_id,
                "user_id": user.id,
                "user_role": user.role.value,
                "message": message,
                "activities": [],
            }
        )
        return self._to_agent_state(session_id, result)

    async def stream(
        self, user: User, session_id: str, message: str, *, approved: bool = False
    ) -> AsyncIterator[AgentActivity | str]:
        state = await self.run(user, session_id, message, approved=approved)
        for activity in state.activities:
            yield activity
        if state.final_answer:
            yield state.final_answer

    def _to_agent_state(self, session_id: str, result: dict) -> AgentState:
        activities = [
            AgentActivity(
                node=AgentNode(item["node"]),
                status=item["status"],
                detail=item["detail"],
                metadata=item.get("metadata", {}),
            )
            for item in result.get("activities", [])
        ]
        return AgentState(
            session_id=session_id,
            activities=activities,
            final_answer=result.get("final_answer"),
            validation_passed=result.get("validation_passed"),
        )
