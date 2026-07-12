from collections.abc import AsyncIterator
from uuid import uuid4

from app.application.dto.chat import AgentActivityDTO, ChatRequest, ChatResponse
from app.domain.entities.message import Message, MessageRole
from app.domain.entities.user import User
from app.domain.ports.agent_port import AgentOrchestratorPort
from app.domain.ports.memory_port import MemoryPort
from app.domain.ports.observability_port import ObservabilityPort
from app.domain.services.guardrails import GuardrailService, GuardrailVerdict
from app.infrastructure.observerbility.langsmith_adapter import NoOpObservabilityAdapter


class ChatUseCase:
    def __init__(
        self,
        agent: AgentOrchestratorPort,
        memory: MemoryPort,
        guardrails: GuardrailService | None = None,
        observability: ObservabilityPort | None = None,
    ) -> None:
        self._agent = agent
        self._memory = memory
        self._guardrails = guardrails or GuardrailService()
        self._observability = observability or NoOpObservabilityAdapter()

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
        long_term_context = await self._memory.get_long_term_context(session_id)
        await self._memory.add_message(session_id, Message(content=request.message, role=MessageRole.USER))

        async with self._observability.trace_run(
            "chat", session_id=session_id, user_id=user.id
        ):
            state = await self._agent.run(
                user,
                session_id,
                request.message,
                approved=request.approved,
                long_term_context=long_term_context,
            )

        if state.final_answer and not state.awaiting_approval:
            await self._memory.add_message(
                session_id, Message(content=state.final_answer, role=MessageRole.ASSISTANT)
            )
            await self._memory.save_turn_summary(
                session_id, request.message, state.final_answer
            )

        return ChatResponse(
            session_id=session_id,
            answer=state.final_answer or "No response.",
            activities=[
                AgentActivityDTO(
                    node=a.node.value,
                    status=a.status,
                    detail=a.detail,
                    metadata=a.metadata,
                )
                for a in state.activities
            ],
            validation_passed=state.validation_passed,
            awaiting_approval=state.awaiting_approval,
            memory_message_count=len(history) + 1,
        )

    async def stream(self, user: User, request: ChatRequest) -> AsyncIterator[dict]:
        session_id = request.session_id or str(uuid4())

        validation = self._guardrails.validate_user_input(request.message)
        if validation.verdict == GuardrailVerdict.BLOCK:
            yield {
                "type": "answer",
                "session_id": session_id,
                "content": f"I cannot process that: {validation.reason}",
                "validation_passed": False,
            }
            return

        await self._memory.add_message(
            session_id, Message(content=request.message, role=MessageRole.USER)
        )
        long_term_context = await self._memory.get_long_term_context(session_id)

        answer_content: str | None = None
        awaiting_approval = False
        try:
            async with self._observability.trace_run(
                "chat", session_id=session_id, user_id=user.id
            ):
                async for event in self._agent.stream(
                    user,
                    session_id,
                    request.message,
                    approved=request.approved,
                    long_term_context=long_term_context,
                ):
                    if isinstance(event, str):
                        answer_content = event
                        yield {
                            "type": "answer",
                            "session_id": session_id,
                            "content": event,
                            "validation_passed": True,
                            "awaiting_approval": awaiting_approval,
                        }
                    else:
                        if event.node.value == "human_approval":
                            awaiting_approval = True
                        yield {
                            "type": "activity",
                            "session_id": session_id,
                            "activity": {
                                "node": event.node.value,
                                "status": event.status,
                                "detail": event.detail,
                            },
                        }
        except Exception as exc:
            fallback = f"Sorry, something went wrong while generating a response: {exc}"
            answer_content = fallback
            yield {"type": "answer", "session_id": session_id, "content": fallback}

        if answer_content and not awaiting_approval:
            await self._memory.add_message(
                session_id,
                Message(content=answer_content, role=MessageRole.ASSISTANT),
            )
            await self._memory.save_turn_summary(
                session_id, request.message, answer_content
            )
