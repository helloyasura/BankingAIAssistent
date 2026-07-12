from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.config import Settings
from app.domain.ports.llm_port import LLMPort


class OpenAIAdapter(LLMPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = (
            ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )

    async def generate(self, prompt: str) -> str:
        if self._client is None:
            return self._fallback_answer(prompt)
        try:
            response = await self._client.ainvoke([HumanMessage(content=prompt)])
            return str(response.content)
        except Exception:
            return self._fallback_answer(prompt)

    def _fallback_answer(self, prompt: str) -> str:
        question_marker = "\n\nQuestion:"
        for marker in (
            "Tool results:\n",
            "Findings:\n",
            "Context:\n",
            "Summarize themes in:\n",
        ):
            if marker in prompt:
                body = prompt.split(marker, 1)[1]
                if question_marker in body:
                    body = body.split(question_marker, 1)[0]
                body = body.strip()
                if body:
                    if marker.startswith("Tool results"):
                        return self._format_tool_results_fallback(body)
                    if marker.startswith("Summarize"):
                        return body[:600]
                    return f"Based on the available documents:\n\n{body[:800]}"
        return "No answer could be generated without an OpenAI API key."

    def _format_tool_results_fallback(self, body: str) -> str:
        """Best-effort formatting when MCP tool results are present but OpenAI is unavailable."""
        if "'results':" in body or '"results":' in body:
            try:
                import ast

                data = ast.literal_eval(body.split("\n\n", 1)[0])
                if isinstance(data, dict) and data.get("results"):
                    lines = []
                    for item in data["results"]:
                        if isinstance(item, dict) and item.get("name"):
                            detail = item["name"]
                            if item.get("role"):
                                detail += f" ({item['role']})"
                            if item.get("department"):
                                detail += f" — {item['department']}"
                            if item.get("email"):
                                detail += f" — {item['email']}"
                            lines.append(detail)
                        else:
                            lines.append(str(item))
                    if lines:
                        return "Based on enterprise directory data:\n\n" + "\n".join(
                            f"- {line}" for line in lines
                        )
            except (SyntaxError, ValueError):
                pass
        return f"Based on tool results:\n\n{body[:800]}"
