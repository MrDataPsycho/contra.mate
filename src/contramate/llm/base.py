from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Standardized chat message format for convenience"""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None


class BaseClient(ABC):
    """Base client class with common functionality"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize base client with API key"""
        self.api_key = api_key
    
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

    def _get_temperature(self, temperature: Optional[float] = None) -> float:
        """Get temperature, using default if not specified"""
        return temperature if temperature is not None else 0.0

    def _get_max_tokens(self, max_tokens: Optional[int] = None) -> int:
        """Get max tokens, using default if not specified"""
        return max_tokens if max_tokens is not None else 1024


class BaseChatClient(BaseClient):
    """Abstract base class for chat completion clients"""

    @abstractmethod
    def chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Synchronous chat completion - Returns native OpenAI SDK response"""
        pass

    @abstractmethod
    async def async_chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Asynchronous chat completion - Returns native OpenAI SDK response"""
        pass

    @abstractmethod
    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        pass


class BaseEmbeddingClient(BaseClient):
    """Abstract base class for embedding clients"""

    @abstractmethod
    def create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Synchronous embedding creation - Returns native OpenAI SDK response"""
        pass

    @abstractmethod
    async def async_create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Asynchronous embedding creation - Returns native OpenAI SDK response"""
        pass

    @abstractmethod
    def _get_embedding_model(self, model: Optional[str] = None) -> str:
        """Get embedding model name, using default if not specified"""
        pass