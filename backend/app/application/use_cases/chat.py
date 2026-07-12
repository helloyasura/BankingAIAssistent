from uuid import uuid4

from app.application.dto.chat import AgentActivityDTO, ChatRequest, ChatResponse
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.user import User
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.memory_port import MemoryPort
from app.domain.services.guardrails import GuardrailService, GuardrailVerdict


class ChatUseCase:
    def __init__(
        self,
        agent: AgentOrchestratorPort,
        memory: MemoryPort,
        guardrails: GuardrailService | None = None,
    ) -> None:
        self._agent = agent
        self._memory = memory
        self._guardrails = guardrails or GuardrailService()

    async def execute(self, user: User, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or str(uuid4())

        validation = self._guardrails.validate_user_input(request.message)
        if validation.verdict == GuardrailVerdict.BLOCK:
            return ChatResponse(
                session_id=session_id,
                answer=f"I cannot process that: {validation.reason}",
                validation_passed=False,
            )

        history = await self._memory.get_history(session_id)
        await self._memory.add_message(session_id, Message(content=request.message, role=MessageRole.USER))

        state = await self._agent.run(user, session_id, request.message, approved=request.approved)

        if state.final_answer:
            await self._memory.add_message(
                session_id, Message(content=state.final_answer, role=MessageRole.ASSISTANT)
            )

        return ChatResponse(
            session_id=session_id,
            answer=state.final_answer or "No response.",
            activities=[
                AgentActivityDTO(node=a.node.value, status=a.status, detail=a.detail)
                for a in state.activities
            ],
            validation_passed=state.validation_passed,
            memory_message_count=len(history) + 1,
        )
