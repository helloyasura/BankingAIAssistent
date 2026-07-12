from collections.abc import AsyncIterator
from app.domain.entities.agent_state import AgentActivity, AgentNode, AgentState
from app.domain.entities.user import User
from app.domain.ports.agent_port import AgentOrchestratorPort


class StubAgentOrchestrator(AgentOrchestratorPort):
    async def run(
        self,
        user: User,
        session_id: str,
        message: str,
        *,
        approved: bool = False,
        long_term_context: str = "",
    ) -> AgentState:
        activities = [
            AgentActivity(AgentNode.SUPERVISOR, "completed", "Routed to retrieval."),
            AgentActivity(AgentNode.RETRIEVAL, "completed", "Stub search — 0 chunks."),
            AgentActivity(AgentNode.RESPONSE, "completed", "Generated stub answer."),
        ]
        answer = f"Hello {user.display_name}! You asked: \"{message}\""
        return AgentState(session_id=session_id, activities=activities, final_answer=answer, validation_passed=True)

    async def stream(
        self,
        user: User,
        session_id: str,
        message: str,
        *,
        approved: bool = False,
        long_term_context: str = "",
    ) -> AsyncIterator[AgentActivity | str]:
        state = await self.run(
            user, session_id, message, approved=approved, long_term_context=long_term_context
        )
        for activity in state.activities:
            yield activity
        if state.final_answer:
            yield state.final_answer