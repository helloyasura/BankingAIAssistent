from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from app.domain.entities.agent_state import AgentActivity, AgentState
from app.domain.entities.user import User

class AgentOrchestratorPort(ABC):
    @abstractmethod
    async def run(
        self,
        user: User,
        session_id: str,
        message: str,
        *,
        approved: bool = False,
        long_term_context: str = "",
    ) -> AgentState: ...

    @abstractmethod
    async def stream(
        self,
        user: User,
        session_id: str,
        message: str,
        *,
        approved: bool = False,
        long_term_context: str = "",
    ) -> AsyncIterator[AgentActivity | str]:
        yield ""