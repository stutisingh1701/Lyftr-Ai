from typing import Optional, Literal, Dict, Any, List, Union
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier, 1-128 characters")
    message: str = Field(..., description="User message content, 1-4000 characters after trimming")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt overriding default")

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("session_id must be a string")
        s = v.strip()
        if len(s) < 1 or len(s) > 128:
            raise ValueError("session_id must be between 1 and 128 characters")
        return s

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("message must be a string")
        stripped = v.strip()
        if len(stripped) == 0:
            raise ValueError("message cannot be empty")
        if len(stripped) > 4000:
            raise ValueError("message cannot exceed 4000 characters")
        return stripped

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None


class ChatMetadata(BaseModel):
    resolution_source: Literal["LIVE_INFERENCE", "LLM_CACHE"] = Field(
        ..., description="Resolution source: LIVE_INFERENCE or LLM_CACHE"
    )
    model: str = Field(..., description="LiteLLM model name that produced the reply")
    latency_ms: int = Field(..., description="Server-measured time for this request in milliseconds")
    input_tokens: int = Field(..., description="Prompt tokens of this request (system + history + new message)")
    output_tokens: int = Field(..., description="Completion tokens of this reply")
    key_id: Optional[str] = Field(None, description="Id of the key that answered (key_1, key_2, ...). null on LLM_CACHE")
    fallback_attempts: int = Field(..., description="Keys that failed before this one succeeded. 0 on LLM_CACHE")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class HealthResponse(BaseModel):
    status: str
    keys_configured: int
    cache_enabled: bool


class MessageHistoryItem(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageHistoryItem]
