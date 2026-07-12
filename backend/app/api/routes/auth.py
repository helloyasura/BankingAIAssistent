from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_container
from app.application.container import Container
from app.application.dto.chat import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, container: Container = Depends(get_container)):
    result = await container.login_use_case.execute(request)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return result