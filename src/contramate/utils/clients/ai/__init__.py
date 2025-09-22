"""AI Clients for chat completions and embeddings with sync and async support"""

from .base import BaseClient, BaseChatClient, BaseEmbeddingClient, ChatMessage, ChatResponse, EmbeddingResponse
from .openai_client import OpenAIChatClient
from .litellm_client import LiteLLMChatClient
from .openai_embedding_client import OpenAIEmbeddingClient
from .litellm_embedding_client import LiteLLMEmbeddingClient
from .azure_openai_client import AzureOpenAIChatClient
from .azure_openai_embedding_client import AzureOpenAIEmbeddingClient

__all__ = [
    "BaseClient",
    "BaseChatClient",
    "BaseEmbeddingClient",
    "ChatMessage",
    "ChatResponse",
    "EmbeddingResponse",
    "OpenAIChatClient",
    "LiteLLMChatClient",
    "OpenAIEmbeddingClient",
    "LiteLLMEmbeddingClient",
    "AzureOpenAIChatClient",
    "AzureOpenAIEmbeddingClient",
]