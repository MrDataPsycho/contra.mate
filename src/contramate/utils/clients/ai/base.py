from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Standardized chat message format"""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None


class ChatResponse(BaseModel):
    """Standardized chat response format"""
    content: str
    model: str
    usage: Dict[str, int]
    response_id: str
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseChatClient(ABC):
    """Abstract base class for chat completion clients"""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Synchronous chat completion"""
        pass

    @abstractmethod
    async def async_chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """Asynchronous chat completion"""
        pass

    def _normalize_messages(
        self, messages: List[Union[ChatMessage, Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Convert messages to standard dict format"""
        normalized = []
        for msg in messages:
            if isinstance(msg, ChatMessage):
                msg_dict = {"role": msg.role, "content": msg.content}
                if msg.name:
                    msg_dict["name"] = msg.name
                normalized.append(msg_dict)
            elif isinstance(msg, dict):
                normalized.append(msg)
            else:
                raise ValueError(f"Invalid message type: {type(msg)}")
        return normalized

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        if model:
            return model
        # This should be overridden by concrete implementations
        raise NotImplementedError("Subclasses must implement model selection")

    def _get_temperature(self, temperature: Optional[float] = None) -> float:
        """Get temperature, using default if not specified"""
        return temperature if temperature is not None else 0.7

    def _get_max_tokens(self, max_tokens: Optional[int] = None) -> int:
        """Get max tokens, using default if not specified"""
        return max_tokens if max_tokens is not None else 1000