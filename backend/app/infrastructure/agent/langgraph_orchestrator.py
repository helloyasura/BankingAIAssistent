from collections.abc import AsyncIterator

from app.domain.entities.agent_state import AgentActivity, AgentNode, AgentState
from app.domain.entities.user import User
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.llm_port import LLMPort
from app.domain.ports.mcp_port import MCPPort
from app.domain.ports.python_analysis_port import PythonAnalysisPort
from app.domain.ports.vector_store_port import VectorStorePort
from app.domain.services.tool_authorization import ToolAuthorizationService
from app.infrastructure.agent.graph.builder import build_agent_graph
from app.infrastructure.agent.graph.nodes import GraphNodes


class LangGraphOrchestrator(AgentOrchestratorPort):
    def __init__(
        self,
        vector_store: VectorStorePort,
        llm: LLMPort,
        mcp: MCPPort,
        python_analysis: PythonAnalysisPort,
        authorization: ToolAuthorizationService | None = None,
    ) -> None:
        nodes = GraphNodes(
            vector_store,
            llm,
            mcp,
            python_analysis,
            authorization=authorization,
        )
        self._graph = build_agent_graph(nodes)

    async def run(
        self, user: User, session_id: str, message: str, *, approved: bool = False
    ) -> AgentState:
        result = await self._graph.ainvoke(self._initial_state(user, session_id, message))
        return self._to_agent_state(session_id, result)

    async def stream(
        self, user: User, session_id: str, message: str, *, approved: bool = False
    ) -> AsyncIterator[AgentActivity | str]:
        seen_activities = 0
        final_answer: str | None = None

        async for chunk in self._graph.astream(self._initial_state(user, session_id, message)):
            for node_output in chunk.values():
                activities = node_output.get("activities", [])
                while seen_activities < len(activities):
                    item = activities[seen_activities]
                    yield AgentActivity(
                        node=AgentNode(item["node"]),
                        status=item["status"],
                        detail=item["detail"],
                        metadata=item.get("metadata", {}),
                    )
                    seen_activities += 1
                if answer := node_output.get("final_answer"):
                    final_answer = answer

        if final_answer:
            yield final_answer

    def _initial_state(self, user: User, session_id: str, message: str) -> dict:
        return {
            "session_id": session_id,
            "user_id": user.id,
            "user_role": user.role.value,
            "message": message,
            "activities": [],
            "tool_results": [],
        }

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
