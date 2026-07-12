from app.domain.entities.message import Message
from app.domain.ports.memory_port import MemoryPort
from app.infrastructure.memory.in_memory import InMemoryMemoryAdapter
from app.infrastructure.memory.sqlite_long_term import SqliteLongTermMemoryStore


class CompositeMemoryAdapter(MemoryPort):
    """Short-term in-memory history plus SQLite long-term context."""

    def __init__(
        self,
        short_term: InMemoryMemoryAdapter | None = None,
        long_term: SqliteLongTermMemoryStore | None = None,
    ) -> None:
        self._short_term = short_term or InMemoryMemoryAdapter()
        self._long_term = long_term

    async def get_history(self, session_id: str, limit: int = 20) -> list[Message]:
        return await self._short_term.get_history(session_id, limit)

    async def add_message(self, session_id: str, message: Message) -> None:
        await self._short_term.add_message(session_id, message)

    async def clear_history(self, session_id: str) -> None:
        await self._short_term.clear_history(session_id)

    async def get_long_term_context(self, session_id: str) -> str:
        if not self._long_term:
            return ""
        return self._long_term.get_context(session_id)

    async def save_turn_summary(
        self, session_id: str, user_message: str, assistant_answer: str
    ) -> None:
        if not self._long_term:
            return
        summary = (
            f"User asked: {user_message[:200]}. "
            f"Assistant answered: {assistant_answer[:300]}"
        )
        self._long_term.save_summary(session_id, summary)
        if len(user_message) > 20:
            self._long_term.add_fact(
                session_id,
                f"Recent topic: {user_message[:120]}",
            )
