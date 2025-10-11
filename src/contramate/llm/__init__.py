"""AI Clients for chat completions and embeddings with sync and async support"""

from contramate.llm.base import BaseClient, BaseChatClient, BaseEmbeddingClient, ChatMessage, ChatResponse, EmbeddingResponse
from contramate.llm.openai_client import OpenAIChatClient
from contramate.llm.litellm_client import LiteLLMChatClient
from contramate.llm.openai_embedding_client import OpenAIEmbeddingClient
from contramate.llm.litellm_embedding_client import LiteLLMEmbeddingClient
from contramate.llm.azure_openai_client import AzureOpenAIChatClient
from contramate.llm.azure_openai_embedding_client import AzureOpenAIEmbeddingClient
from contramate.llm.factory import LLMClientFactory, create_default_chat_client, create_default_embedding_client

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
    "LLMClientFactory",
    "create_default_chat_client",
    "create_default_embedding_client",
]