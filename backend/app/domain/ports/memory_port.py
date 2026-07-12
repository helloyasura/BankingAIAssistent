from abc import ABC, abstractmethod
from app.domain.entities.message import Message

class MemoryPort(ABC):
    @abstractmethod
    async def get_history(self , session_id:str , limit:int=20) -> list[Message]: ...

    @abstractmethod
    async def add_message(self , session_id:str , message:Message) -> None: ...

    @abstractmethod
    async def clear_history(self , session_id:str) -> None: ...

    async def get_long_term_context(self, session_id: str) -> str:
        return ""

    async def save_turn_summary(
        self, session_id: str, user_message: str, assistant_answer: str
    ) -> None:
        return None