from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=-1, le=1, description="1=thumbs up, -1=thumbs down")
    message_id: str | None = None
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: str
    session_id: str
    rating: int
    message_id: str | None = None
    comment: str | None = None
