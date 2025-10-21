"""AI Clients for chat completions and embeddings with sync and async support"""

from contramate.llm.base import BaseClient, BaseChatClient, BaseEmbeddingClient, ChatMessage
from contramate.llm.openai_client import OpenAIChatClient
from contramate.llm.openai_embedding_client import OpenAIEmbeddingClient
from contramate.llm.azure_openai_client import AzureOpenAIChatClient
from contramate.llm.azure_openai_embedding_client import AzureOpenAIEmbeddingClient
from contramate.llm.factory import (
    LLMClientFactory,
    LLMVanillaClientFactory,
    create_default_chat_client,
    create_default_embedding_client,
    create_vanilla_chat_client,
    create_vanilla_embedding_client,
    get_vanilla_openai_client,
    get_vanilla_azure_openai_client,
    get_vanilla_native_clients,
)

__all__ = [
    "BaseClient",
    "BaseChatClient",
    "BaseEmbeddingClient",
    "ChatMessage",
    "OpenAIChatClient",
    "OpenAIEmbeddingClient",
    "AzureOpenAIChatClient",
    "AzureOpenAIEmbeddingClient",
    "LLMClientFactory",
    "LLMVanillaClientFactory",
    "create_default_chat_client",
    "create_default_embedding_client",
    "create_vanilla_chat_client",
    "create_vanilla_embedding_client",
    "get_vanilla_openai_client",
    "get_vanilla_azure_openai_client",
    "get_vanilla_native_clients",
]
