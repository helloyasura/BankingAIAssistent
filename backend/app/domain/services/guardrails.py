import re
from dataclasses import dataclass
from enum import Enum


class GuardrailVerdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"


@dataclass(frozen=True)
class GuardrailResult:
    verdict: GuardrailVerdict
    reason: str


_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"dump\s+(all\s+)?(documents|data)", re.I),
    re.compile(r"bypass\s+(rbac|security)", re.I),
]


class GuardrailService:
    def validate_user_input(self, content: str) -> GuardrailResult:
        if not content.strip():
            return GuardrailResult(GuardrailVerdict.BLOCK, "Empty input.")
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(content):
                return GuardrailResult(GuardrailVerdict.BLOCK, "Prompt injection detected.")
        return GuardrailResult(GuardrailVerdict.ALLOW, "OK")