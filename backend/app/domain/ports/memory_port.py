from abc import ABC, abstractmethod
from app.domain.entities.message import Message

class MemoryPort(ABC):
    @abstractmethod
    async def get_history(self , session_id:str , limit:int=20) -> list[Message]: ...

    @abstractmethod
    async def add_message(self , session_id:str , message:Message) -> None: ...

    @abstractmethod
    async def clear_history(self , session_id:str) -> None: ...