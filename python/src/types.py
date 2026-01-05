from dataclasses import dataclass
from typing import Literal, Any, Optional

Provider = Literal["cerebras"]


@dataclass
class CallOptions:
    system_prompt: str
    user_message: str
    model: Optional[str] = None
    max_tokens: int = 1024


@dataclass
class AIResponse:
    provider: Provider
    content: str
    raw: Any
