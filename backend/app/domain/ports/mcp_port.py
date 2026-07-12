from abc import ABC, abstractmethod


class MCPPort(ABC):
    @abstractmethod
    async def call_tool(self, tool_name: str, arguments: dict) -> dict: ...

    @abstractmethod
    async def infer_and_call(self, message: str) -> dict: ...
