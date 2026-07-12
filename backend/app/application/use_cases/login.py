from app.application.dto.chat import LoginRequest, LoginResponse
from app.domain.ports.auth_port import AuthPort
from app.infrastructure.auth.jwt_service import JwtService

class LoginUseCase:
    def __init__(self, auth_port: AuthPort, jwt_service: JwtService) -> None:

        self._auth_port = auth_port
        self._jwt = jwt_service

    async def execute(self, request: LoginRequest) -> LoginResponse | None:
        user = await self._auth_port.authenticate(request.email, request.password)
        if not user:
            return None
        return LoginResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role.value,
            access_token=self._jwt.create_token(user)
        )