from fastapi import APIRouter, Depends

from app.api.dependencies import get_container, get_current_user
from app.application.container import Container
from app.application.dto.chat import ChatRequest, ChatResponse
from app.domain.entities.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    return await container.chat_use_case.execute(user, request)