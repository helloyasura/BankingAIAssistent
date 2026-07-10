from dataclasses import dataclass, field 
from enum import Enum
from app.domain.entities.document import DocumentChunk
from app.domain.entities.message import Message


class AgentNode(str, Enum):
    SUPERVISOR = "supervisor"
    RETRIEVAL = "retrieval"
    RESEARCH = "research"
    RESPONSE = "response"
    GUARDRAILS = "guardrails"
    HUMAN_APPROVAL = "human_approval"

@dataclass(slots=True)
class AgentActivity: 
    node: AgentNode
    status: str
    detail: str 
    metadata: dict[str, str] = field(default_factory=dict)
    
@dataclass(slots=True)
class AgentState:
    session_id: str
    messages: list[Message] = field(default_factory=list)
    current_node: AgentNode | None = None
    retrieved_documents: list[DocumentChunk] = field(default_factory=list)
    activities: list[AgentActivity] = field(default_factory=list)
    final_aswer: str | None = None
    validation_result: str | None = None
