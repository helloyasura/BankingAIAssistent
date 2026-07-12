from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.container import Container
from app.domain.entities.user import User

_bearer = HTTPBearer()


def get_container(request: Request) -> Container:
    return request.app.state.container


async def get_current_user(
    container: Container = Depends(get_container),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    payload = container.jwt_service.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await container.auth_port.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
