from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any


class ObservabilityPort(ABC):
    @asynccontextmanager
    @abstractmethod
    async def trace_run(self, name: str, **metadata: Any) -> AsyncIterator[None]:
        yield  # pragma: no cover

    async def log_feedback(self, **metadata: Any) -> None:
        return None
