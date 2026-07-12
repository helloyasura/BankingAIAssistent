from dataclasses import dataclass, field
from datetime import datetime, timezone


_SENSITIVE_ROUTES = frozenset({"mcp_tools", "python_analysis"})
_DESTRUCTIVE_PATTERNS = (
    "delete",
    "remove",
    "drop",
    "purge",
    "wipe",
    "destroy",
)


@dataclass(slots=True)
class PendingApproval:
    session_id: str
    route: str
    message: str
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalGateService:
    """In-memory HITL gate for sensitive agent actions (POC)."""

    def __init__(self, *, auto_approve: bool = False) -> None:
        self._auto_approve = auto_approve
        self._pending: dict[str, PendingApproval] = {}
        self._approved_sessions: set[str] = set()

    @property
    def auto_approve(self) -> bool:
        return self._auto_approve

    def requires_approval(self, route: str, message: str) -> bool:
        if route not in _SENSITIVE_ROUTES:
            return False
        lowered = message.lower()
        if any(pattern in lowered for pattern in _DESTRUCTIVE_PATTERNS):
            return True
        return route in _SENSITIVE_ROUTES

    def is_approved(self, session_id: str, *, request_approved: bool = False) -> bool:
        if self._auto_approve or request_approved:
            return True
        return session_id in self._approved_sessions

    def request_approval(
        self, session_id: str, route: str, message: str
    ) -> PendingApproval:
        reason = (
            f"Sensitive action '{route}' requires human approval before execution."
        )
        pending = PendingApproval(
            session_id=session_id,
            route=route,
            message=message,
            reason=reason,
        )
        self._pending[session_id] = pending
        return pending

    def approve(self, session_id: str) -> bool:
        if session_id not in self._pending:
            return False
        self._approved_sessions.add(session_id)
        self._pending.pop(session_id, None)
        return True

    def reject(self, session_id: str) -> bool:
        self._approved_sessions.discard(session_id)
        return self._pending.pop(session_id, None) is not None

    def get_pending(self, session_id: str) -> PendingApproval | None:
        return self._pending.get(session_id)

    def list_pending(self) -> list[PendingApproval]:
        return list(self._pending.values())
