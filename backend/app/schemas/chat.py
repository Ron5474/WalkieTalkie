from typing import List, Optional

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None


class ChatRequest(BaseModel):
    """llm_tier: 'small' | 'large' for dual-model experiments. Legacy `model` is still accepted."""

    model: Optional[str] = None
    llm_tier: Optional[str] = "large"
    messages: List[Message]
    stream: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = "San Francisco"
    session_token: Optional[str] = None
    prompting_mode: Optional[str] = "self_reflection"
