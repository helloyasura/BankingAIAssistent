from collections import defaultdict
from app.domain.entities.message import Message
from app.domain.ports.memory_port import MemoryPort

class InMemoryMemoryAdapter(MemoryPort):
    def __init__(self) -> None:
        self._store: dict[str, list[Message]] = defaultdict(list)
    async def get_history(self, session_id: str, limit: int = 20) -> list[Message]:
        return self._store[session_id][-limit:]
    
    async def add_message(self, session_id: str, message: Message) -> None:
        self._store[session_id].append(message)

    async def clear_history(self, session_id: str) -> None:
        self._store.pop(session_id, None)