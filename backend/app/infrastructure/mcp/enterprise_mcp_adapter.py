import asyncio
import sys
from pathlib import Path

from app.domain.ports.mcp_port import MCPPort

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_server.server import call_tool, infer_tool_from_message  # noqa: E402


class EnterpriseMcpAdapter(MCPPort):
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        return await asyncio.to_thread(call_tool, tool_name, arguments)

    async def infer_and_call(self, message: str) -> dict:
        tool_name, arguments = infer_tool_from_message(message)
        result = await self.call_tool(tool_name, arguments)
        result["inferred_tool"] = tool_name
        return result
