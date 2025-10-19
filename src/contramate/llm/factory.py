"""Factory for creating LLM clients with OpenAI and Azure OpenAI support"""

from typing import Optional, Literal
import logging

from contramate.utils.settings.factory import settings_factory
from contramate.llm.base import BaseChatClient, BaseEmbeddingClient
from contramate.llm.openai_client import OpenAIChatClient
from contramate.llm.openai_embedding_client import OpenAIEmbeddingClient
from contramate.llm.azure_openai_client import AzureOpenAIChatClient
from contramate.llm.azure_openai_embedding_client import AzureOpenAIEmbeddingClient

logger = logging.getLogger(__name__)

ClientType = Literal["openai", "azure_openai"]


class LLMClientFactory:
    """Factory for creating LLM clients with sensible defaults

    Default client is OpenAI for reliable API access.
    Automatically initializes settings from AppSettings.
    """

    def __init__(
        self,
        default_client_type: ClientType = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize the LLM client factory

        Args:
            default_client_type: Default client type to use ("openai", "azure_openai")
            api_key: Optional API key (will use settings if not provided)
            model: Optional default model name (will use settings if not provided)
            embedding_model: Optional default embedding model (will use settings if not provided)
        """
        self.default_client_type = default_client_type
        self._api_key = api_key
        self._model = model
        self._embedding_model = embedding_model

        logger.info(f"LLMClientFactory initialized with default client type: {default_client_type}")

    @classmethod
    def create_from_default(cls, client_type: ClientType = "openai") -> "LLMClientFactory":
        """
        Create factory from default AppSettings configuration

        Args:
            client_type: Client type to use as default

        Returns:
            LLMClientFactory instance initialized with settings
        """
        logger.info(f"Creating LLMClientFactory from default settings for client type: {client_type}")

        # Initialize appropriate settings based on client type
        if client_type == "openai":
            openai_settings = settings_factory.create_openai_settings()
            api_key = openai_settings.api_key
            model = openai_settings.model
            embedding_model = openai_settings.embedding_model
        elif client_type == "azure_openai":
            azure_settings = settings_factory.create_azure_openai_settings()
            api_key = None  # Azure uses certificate-based auth
            model = azure_settings.model
            embedding_model = azure_settings.embedding_model
        else:
            raise ValueError(f"Unsupported client type: {client_type}")

        return cls(
            default_client_type=client_type,
            api_key=api_key,
            model=model,
            embedding_model=embedding_model
        )

    def create_client(
        self,
        client_type: Optional[ClientType] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseChatClient:
        """
        Create a chat client

        Args:
            client_type: Type of client to create (uses default if not specified)
            api_key: API key override
            model: Model name override
            **kwargs: Additional client-specific parameters

        Returns:
            BaseChatClient instance
        """
        client_type = client_type or self.default_client_type
        api_key = api_key or self._api_key
        model = model or self._model

        logger.info(f"Creating chat client of type: {client_type}")

        if client_type == "openai":
            return OpenAIChatClient(
                api_key=api_key,
                model=model
            )
        elif client_type == "azure_openai":
            return AzureOpenAIChatClient(
                azure_settings=kwargs.get("azure_settings", None)
            )
        else:
            raise ValueError(f"Unsupported client type: {client_type}")

    def create_embedding_client(
        self,
        client_type: Optional[ClientType] = None,
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        **kwargs
    ) -> BaseEmbeddingClient:
        """
        Create an embedding client

        Args:
            client_type: Type of client to create (uses default if not specified)
            api_key: API key override
            embedding_model: Embedding model name override
            **kwargs: Additional client-specific parameters

        Returns:
            BaseEmbeddingClient instance
        """
        client_type = client_type or self.default_client_type
        api_key = api_key or self._api_key
        embedding_model = embedding_model or self._embedding_model

        logger.info(f"Creating embedding client of type: {client_type}")

        if client_type == "openai":
            return OpenAIEmbeddingClient(
                api_key=api_key,
                embedding_model=embedding_model
            )
        elif client_type == "azure_openai":
            return AzureOpenAIEmbeddingClient(
                azure_settings=kwargs.get("azure_settings", None)
            )
        else:
            raise ValueError(f"Unsupported client type: {client_type}")


# Convenience functions for quick client creation
def create_default_chat_client(client_type: ClientType = "openai") -> BaseChatClient:
    """
    Convenience function to create a chat client with default settings

    Args:
        client_type: Type of client to create (default: "openai")

    Returns:
        BaseChatClient instance
    """
    factory = LLMClientFactory.create_from_default(client_type)
    return factory.create_client()


def create_default_embedding_client(client_type: ClientType = "openai") -> BaseEmbeddingClient:
    """
    Convenience function to create an embedding client with default settings

    Args:
        client_type: Type of client to create (default: "openai")

    Returns:
        BaseEmbeddingClient instance
    """
    factory = LLMClientFactory.create_from_default(client_type)
    return factory.create_embedding_client()


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def test_factory():
        # Create factory from default settings
        factory = LLMClientFactory.create_from_default("openai")

        # Create a chat client
        chat_client = factory.create_client()

        # Test chat
        test_messages = [
            {"role": "user", "content": "Hello, this is a test message."}
        ]

        response = chat_client.chat(test_messages)
        print(f"Chat response: {response}")

        # Create an embedding client
        embedding_client = factory.create_embedding_client()

        # Test embedding
        embedding_response = embedding_client.create_embeddings("Test text for embedding")
        print(f"Embedding dimensions: {embedding_response.dimensions}")

        # Using convenience functions
        print("\n--- Using convenience functions ---")
        quick_chat_client = create_default_chat_client()
        quick_response = quick_chat_client.chat(test_messages)
        print(f"Quick chat response: {quick_response}")

    asyncio.run(test_factory())
