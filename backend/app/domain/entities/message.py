from dataclasses import dataclass , field
from datetime import datetime , timezone 
from enum import Enum
from uuid import uuid4

class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
@dataclass(slots=True)
class Message:
    content: str
    role: MessageRole
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))