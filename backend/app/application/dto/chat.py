from pydantic import BaseModel , Field

class LoginRequest(BaseModel):
    email:str
    password:str

class LoginResponse(BaseModel):
    user_id:str 
    email:str
    display_name:str
    role:str
    access_token:str

class ChatRequest(BaseModel):
    message: str = Field(...,min_length=2, max_length=4000,
                          description="The message content to be sent to the chat system.")
    session_id: str| None = None
    approved:bool = False

class AgentActivityDTO(BaseModel):
    node:str
    status:str
    detail:str
    metadata: dict[str, str] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[dict] = Field(default_factory=list)
    activities: list[AgentActivityDTO] = Field(default_factory=list)
    validation_passed: bool | None = None
    awaiting_approval: bool = False
    memory_message_count: int = 0


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    dependencies: dict[str, str]