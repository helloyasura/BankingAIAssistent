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
        response = await self._client.ainvoke([HumanMessage(content=prompt)])
        return str(response.content)

    def _fallback_answer(self, prompt: str) -> str:
        question_marker = "\n\nQuestion:"
        for marker in ("Findings:\n", "Context:\n", "Summarize themes in:\n"):
            if marker in prompt:
                body = prompt.split(marker, 1)[1]
                if question_marker in body:
                    body = body.split(question_marker, 1)[0]
                body = body.strip()
                if body:
                    if marker.startswith("Summarize"):
                        return body[:600]
                    return f"Based on the available documents:\n\n{body[:800]}"
        return "No answer could be generated without an OpenAI API key."
