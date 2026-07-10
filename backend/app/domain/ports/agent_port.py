from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from app.domain.entities.agent_state import AgentActivity, AgentState
from app.domain.entities.user import User

class AgentOrchestratorPort(ABC):
    @abstractmethod
    async def run(
        self , user:User , session_id:str, message:str, *, approved:bool = False) -> AgentState: ...

    @abstractmethod
    async def stream(
        self , user:User , session_id:str, message:str, *, approved:bool = False
    ) -> AsyncIterator[AgentActivity| str]:
        yield ""