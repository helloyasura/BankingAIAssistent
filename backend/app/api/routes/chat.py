import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_container, get_current_user
from app.application.container import Container
from app.application.dto.chat import ChatRequest, ChatResponse
from app.domain.entities.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


class ApprovalAction(BaseModel):
    approved: bool = True


@router.post("/approvals/{session_id}")
async def approve_session(
    session_id: str,
    action: ApprovalAction,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    if action.approved:
        ok = container.approval_gate.approve(session_id)
        if not ok:
            return {"session_id": session_id, "status": "no_pending_approval"}
        return {"session_id": session_id, "status": "approved"}
    container.approval_gate.reject(session_id)
    return {"session_id": session_id, "status": "rejected"}


@router.get("/approvals/pending")
async def list_pending_approvals(
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    pending = container.approval_gate.list_pending()
    return [
        {
            "session_id": item.session_id,
            "route": item.route,
            "message": item.message,
            "reason": item.reason,
        }
        for item in pending
    ]


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    return await container.chat_use_case.execute(user, request)


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    container: Container = Depends(get_container),
):
    async def events():
        try:
            async for event in container.chat_use_case.stream(user, request):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
