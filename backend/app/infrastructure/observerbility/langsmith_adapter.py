import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.config import Settings
from app.domain.ports.observability_port import ObservabilityPort


class NoOpObservabilityAdapter(ObservabilityPort):
    @asynccontextmanager
    async def trace_run(self, name: str, **metadata: Any) -> AsyncIterator[None]:
        yield


class LangSmithObservabilityAdapter(ObservabilityPort):
    def __init__(self, settings: Settings) -> None:
        if settings.langchain_tracing_v2:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if settings.langchain_api_key:
            os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        if settings.langchain_project:
            os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

    @asynccontextmanager
    async def trace_run(self, name: str, **metadata: Any) -> AsyncIterator[None]:
        from langsmith import trace

        with trace(name=name, metadata=metadata):
            yield
