from app.domain.entities.user import User
from app.domain.ports.auth_port import AuthPort
from app.domain.value_objects.role import Role

_USERS: dict[str, tuple[str, User]] = {
    "viewer@combank.com": (
        "viewer",
        User(
            id="1",
            email="viewer@combank.com",
            display_name="Viewer",
            role=Role.VIEWER,
        ),
    ),
    "analyst@commercialbank.com": (
        "analyst123",
        User(
            id="2",
            email="editor@combank.com",
            display_name="Editor",
            role=Role.ANALYST,
        ),
    ),
    "admin@commercialbank.com": (
        "admin123",
        User(
            id="3",
            email="admin@combank.com",
            display_name="Admin",
            role=Role.ADMINISTRATOR,
        ),
    ),
}


class HardcodedAuth(AuthPort):
    async def authenticate(self, email: str, password: str) -> User | None:
        if email not in _USERS:
            return None
        stored_password, user = _USERS[email]
        if stored_password != password:
            return None
        return user

    async def get_user_by_id(self, user_id: str) -> User | None:
        return next((user for _, user in _USERS.values() if user.id == user_id), None)

    async def get_user_by_email(self, email: str) -> User | None:
        record = _USERS.get(email)
        return record[1] if record else None
