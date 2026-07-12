from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt

from app.config import Settings
from app.domain.entities.user import User


class JwtService:
    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm
        self._expires = settings.jwt_expire_minutes

    def create_token(self, user: User) -> str:
        payload = {
            "sub": user.id,
            "email": user.email,
            "role": user.role.value,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self._expires),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError:
            return None
