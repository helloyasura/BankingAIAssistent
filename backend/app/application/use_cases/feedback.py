from app.application.dto.feedback import FeedbackRequest, FeedbackResponse
from app.domain.entities.user import User
from app.domain.ports.observability_port import ObservabilityPort
from app.infrastructure.feedback.feedback_store import FeedbackStore
from app.infrastructure.observerbility.langsmith_adapter import NoOpObservabilityAdapter


class FeedbackUseCase:
    def __init__(
        self,
        store: FeedbackStore,
        observability: ObservabilityPort | None = None,
    ) -> None:
        self._store = store
        self._observability = observability or NoOpObservabilityAdapter()

    async def execute(self, user: User, request: FeedbackRequest) -> FeedbackResponse:
        record = self._store.save(
            session_id=request.session_id,
            rating=request.rating,
            message_id=request.message_id,
            comment=request.comment,
            user_id=user.id,
        )
        await self._observability.log_feedback(
            session_id=request.session_id,
            rating=request.rating,
            message_id=request.message_id,
            comment=request.comment,
            user_id=user.id,
        )
        return FeedbackResponse(
            id=record["id"],
            session_id=record["session_id"],
            rating=record["rating"],
            message_id=record.get("message_id"),
            comment=record.get("comment"),
        )
