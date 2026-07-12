from fastapi import APIRouter, Depends

from app.api.dependencies import get_container, get_current_user
from app.application.container import Container
from app.application.dto.feedback import FeedbackRequest, FeedbackResponse
from app.domain.entities.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    return await container.feedback_use_case.execute(user, request)
