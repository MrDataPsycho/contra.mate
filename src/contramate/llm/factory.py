from typing import Optional, Literal
from pathlib import Path
from loguru import logger

from contramate.utils.settings.factory import settings_factory
from contramate.utils.settings.core import AppSettings, OpenAISettings
from contramate.llm.base import BaseChatClient, BaseEmbeddingClient
from contramate.llm.openai_client import OpenAIChatClient
from contramate.llm.openai_embedding_client import OpenAIEmbeddingClient
from contramate.llm.azure_openai_client import AzureOpenAIChatClient
from contramate.llm.azure_openai_embedding_client import AzureOpenAIEmbeddingClient
from openai import OpenAI, AsyncOpenAI, AzureOpenAI, AsyncAzureOpenAI
from contramate.utils.auth.certificate_provider import get_cert_token_provider

ClientType = Literal["openai", "azure_openai"]


class LLMVanillaClientFactory:
    """
    Factory for creating vanilla OpenAI SDK clients (not wrapper classes).

    Returns raw OpenAI SDK clients that can handle both chat and embeddings
    with the same client instance by specifying different models.
    """

    def __init__(self, env_path: Optional[str | Path] = None):
        """
        Initialize vanilla client factory.

        Args:
            env_path: Optional path to environment file to load settings from

        Provider is automatically determined from APP_LLM_PROVIDER environment variable.
        """
        self.env_path = env_path

    @classmethod
    def from_env_file(cls, env_path: str | Path) -> "LLMVanillaClientFactory":
        """
        Create factory with settings loaded from a specific .env file.
        Useful for notebooks where you want to specify environment file path.

        Args:
            env_path: Path to the .env file to load settings from

        Returns:
            LLMVanillaClientFactory instance with settings loaded from env file

        Example:
            factory = LLMVanillaClientFactory.from_env_file(".envs/local.env")
            client = factory.get_default_client(async_mode=True)
        """
        return cls(env_path=env_path)

    def get_default_client(self, async_mode: bool = False) -> AsyncOpenAI | OpenAI | AsyncAzureOpenAI | AzureOpenAI:
        """
        Get vanilla OpenAI SDK client (sync or async).

        Returns the raw OpenAI SDK client that can handle both chat completions
        and embeddings by specifying different models.

        Args:
            async_mode: If True, returns AsyncOpenAI/AsyncAzureOpenAI,
                       otherwise returns OpenAI/AzureOpenAI (default: False)

        Returns:
            OpenAI | AzureOpenAI | AsyncOpenAI | AsyncAzureOpenAI
        """

        # Determine provider from environment
        try:
            if self.env_path:
                app_settings = AppSettings.from_env_file(self.env_path)
            else:
                app_settings = settings_factory.create_app_settings()
            provider = app_settings.llm_provider.lower()
        except Exception as e:
            logger.warning(f"Failed to get APP_LLM_PROVIDER, defaulting to 'openai': {e}")
            provider = "openai"

        logger.info(f"Creating vanilla {'async' if async_mode else 'sync'} client for provider: {provider}")

        # Create clients based on provider
        if provider == "openai":
            return self._create_openai_client(async_mode)
        elif provider == "azure_openai":
            return self._create_azure_client(async_mode)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'azure_openai'")

    def _create_openai_client(self, async_mode: bool) -> AsyncOpenAI | OpenAI:
        """Create OpenAI vanilla client"""

        try:
            if self.env_path:
                openai_settings = OpenAISettings.from_env_file(self.env_path)
            else:
                openai_settings = settings_factory.create_openai_settings()

            if not openai_settings.api_key:
                raise ValueError("OPENAI_API_KEY is required")

            client_config = {"api_key": openai_settings.api_key}
            if openai_settings.base_url:
                client_config["base_url"] = openai_settings.base_url

            if async_mode:
                return AsyncOpenAI(**client_config)
            else:
                return OpenAI(**client_config)

        except Exception as e:
            logger.error(f"Failed to create OpenAI vanilla client: {e}")
            raise ValueError(f"Failed to create OpenAI client: {e}")

    def _create_azure_client(self, async_mode: bool) -> AsyncAzureOpenAI | AzureOpenAI:
        """Create Azure OpenAI vanilla client"""
        from openai import AzureOpenAI, AsyncAzureOpenAI

        try:
            if self.env_path:
                from contramate.utils.settings.core import AOAICertSettings
                azure_settings = AOAICertSettings.from_env_file(self.env_path)
            else:
                azure_settings = settings_factory.create_azure_openai_settings()

            if not azure_settings.azure_endpoint:
                raise ValueError("AZURE_OPENAI_AZURE_ENDPOINT is required")

            # Get certificate-based token provider
            
            token_provider = get_cert_token_provider(azure_settings)
            client_config = {
                "azure_endpoint": azure_settings.azure_endpoint,
                "api_version": azure_settings.api_version,
                "azure_ad_token_provider": token_provider
            }

            if async_mode:
                return AsyncAzureOpenAI(**client_config)
            else:
                return AzureOpenAI(**client_config)

        except Exception as e:
            logger.error(f"Failed to create Azure OpenAI vanilla client: {e}")
            raise ValueError(f"Failed to create Azure OpenAI client: {e}")


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
            azure_ad_cert_settings = kwargs.get("azure_ad_cert_settings")
            if not azure_ad_cert_settings:
                # Create settings from factory if not provided
                azure_ad_cert_settings = settings_factory.create_azure_openai_settings()

            return AzureOpenAIChatClient(
                azure_ad_cert_settings=azure_ad_cert_settings,
                model=model
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
            azure_ad_cert_settings = kwargs.get("azure_ad_cert_settings")
            if not azure_ad_cert_settings:
                # Create settings from factory if not provided
                azure_ad_cert_settings = settings_factory.create_azure_openai_settings()

            return AzureOpenAIEmbeddingClient(
                azure_ad_cert_settings=azure_ad_cert_settings,
                embedding_model=embedding_model
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


def create_vanilla_chat_client() -> BaseChatClient:
    """
    Create a vanilla chat client based on app settings.

    Automatically selects between OpenAI and Azure OpenAI based on APP_LLM_PROVIDER
    environment variable. Falls back to trying available providers if not set.

    Returns:
        BaseChatClient instance (OpenAI or Azure OpenAI)

    Raises:
        ValueError: If no valid LLM provider can be initialized

    Example:
        >>> # Set APP_LLM_PROVIDER=openai or APP_LLM_PROVIDER=azure_openai
        >>> client = create_vanilla_chat_client()
        >>> response = client.chat_completion([{"role": "user", "content": "Hello"}])
    """
    try:
        app_settings = settings_factory.create_app_settings()
        provider = app_settings.llm_provider.lower()

        logger.info(f"Creating vanilla chat client with provider: {provider}")

        if provider == "openai":
            return create_default_chat_client(client_type="openai")
        elif provider == "azure_openai":
            return create_default_chat_client(client_type="azure_openai")
        else:
            logger.warning(f"Unknown LLM provider '{provider}', trying OpenAI first")

    except Exception as e:
        logger.warning(f"Failed to get app settings or create client with configured provider: {e}")

    # Fallback: Try OpenAI first, then Azure OpenAI
    try:
        logger.info("Attempting to create OpenAI chat client as fallback")
        return create_default_chat_client(client_type="openai")
    except Exception as e:
        logger.warning(f"Failed to create OpenAI client: {e}")

    try:
        logger.info("Attempting to create Azure OpenAI chat client as fallback")
        return create_default_chat_client(client_type="azure_openai")
    except Exception as e:
        logger.warning(f"Failed to create Azure OpenAI client: {e}")

    raise ValueError(
        "No valid LLM provider could be initialized. "
        "Please configure OPENAI_API_KEY or Azure OpenAI settings. "
        "You can also set APP_LLM_PROVIDER to 'openai' or 'azure_openai'."
    )


def get_vanilla_openai_client():
    """
    Get native OpenAI SDK clients (sync and async) based on app settings.

    Returns a tuple of (sync_client, async_client) that are native OpenAI SDK objects,
    not our wrapper classes. Use this when you want direct access to the OpenAI SDK.

    Returns:
        tuple: (OpenAI, AsyncOpenAI) - Native OpenAI SDK clients

    Raises:
        ValueError: If OpenAI settings are not configured

    Example:
        >>> from openai import OpenAI, AsyncOpenAI
        >>> sync_client, async_client = get_vanilla_openai_client()
        >>>
        >>> # Use sync client
        >>> response = sync_client.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
        >>>
        >>> # Use async client
        >>> async def example():
        ...     response = await async_client.chat.completions.create(
        ...         model="gpt-4",
        ...         messages=[{"role": "user", "content": "Hello"}]
        ...     )
    """
    from openai import OpenAI, AsyncOpenAI

    try:
        openai_settings = settings_factory.create_openai_settings()

        if not openai_settings.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        client_config = {"api_key": openai_settings.api_key}

        if openai_settings.base_url:
            client_config["base_url"] = openai_settings.base_url

        sync_client = OpenAI(**client_config)
        async_client = AsyncOpenAI(**client_config)

        logger.info("Created native OpenAI SDK clients (sync + async)")
        return sync_client, async_client

    except Exception as e:
        logger.error(f"Failed to create native OpenAI clients: {e}")
        raise ValueError(
            f"Failed to create native OpenAI clients: {e}. "
            "Please ensure OPENAI_API_KEY is set."
        )


def get_vanilla_azure_openai_client():
    """
    Get native Azure OpenAI SDK clients (sync and async) based on app settings.

    Returns a tuple of (sync_client, async_client) that are native Azure OpenAI SDK objects,
    not our wrapper classes. Use this when you want direct access to the Azure OpenAI SDK.

    Returns:
        tuple: (AzureOpenAI, AsyncAzureOpenAI) - Native Azure OpenAI SDK clients

    Raises:
        ValueError: If Azure OpenAI settings are not configured

    Example:
        >>> from openai import AzureOpenAI, AsyncAzureOpenAI
        >>> sync_client, async_client = get_vanilla_azure_openai_client()
        >>>
        >>> # Use sync client
        >>> response = sync_client.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
    """
    from openai import AzureOpenAI, AsyncAzureOpenAI

    try:
        azure_settings = settings_factory.create_azure_openai_settings()

        if not azure_settings.azure_endpoint:
            raise ValueError("AZURE_OPENAI_AZURE_ENDPOINT is required")

        # Get certificate-based token provider
        try:
            from contramate.utils.auth.certificate_provider import get_cert_token_provider
            token_provider = get_cert_token_provider(azure_settings)

            client_config = {
                "azure_endpoint": azure_settings.azure_endpoint,
                "api_version": azure_settings.api_version,
                "azure_ad_token_provider": token_provider
            }

            sync_client = AzureOpenAI(**client_config)
            async_client = AsyncAzureOpenAI(**client_config)

            logger.info("Created native Azure OpenAI SDK clients (sync + async) with certificate auth")
            return sync_client, async_client

        except Exception as cert_error:
            logger.warning(f"Certificate auth failed: {cert_error}, trying API key if available")

            # Fallback to API key if available (though not in settings, might be set manually)
            raise ValueError(
                f"Failed to create native Azure OpenAI clients: {cert_error}. "
                "Please ensure Azure OpenAI certificate settings are properly configured."
            )

    except Exception as e:
        logger.error(f"Failed to create native Azure OpenAI clients: {e}")
        raise ValueError(
            f"Failed to create native Azure OpenAI clients: {e}. "
            "Please ensure Azure OpenAI settings are properly configured."
        )


def get_vanilla_native_clients():
    """
    Get native OpenAI SDK clients based on APP_LLM_PROVIDER setting.

    Automatically selects between OpenAI and Azure OpenAI based on APP_LLM_PROVIDER,
    and returns the raw SDK clients (not wrapper classes).

    Returns:
        tuple: (sync_client, async_client) - Native OpenAI or Azure OpenAI SDK clients

    Raises:
        ValueError: If no valid LLM provider can be initialized

    Example:
        >>> # Set APP_LLM_PROVIDER=openai or APP_LLM_PROVIDER=azure_openai
        >>> sync_client, async_client = get_vanilla_native_clients()
        >>>
        >>> # Use directly with OpenAI SDK
        >>> response = sync_client.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
        >>>
        >>> # Async
        >>> async def example():
        ...     response = await async_client.chat.completions.create(
        ...         model="gpt-4",
        ...         messages=[{"role": "user", "content": "Hello"}]
        ...     )
    """
    try:
        app_settings = settings_factory.create_app_settings()
        provider = app_settings.llm_provider.lower()

        logger.info(f"Getting native SDK clients for provider: {provider}")

        if provider == "openai":
            return get_vanilla_openai_client()
        elif provider == "azure_openai":
            return get_vanilla_azure_openai_client()
        else:
            logger.warning(f"Unknown LLM provider '{provider}', trying OpenAI first")

    except Exception as e:
        logger.warning(f"Failed to get app settings or create clients with configured provider: {e}")

    # Fallback: Try OpenAI first, then Azure OpenAI
    try:
        logger.info("Attempting to create native OpenAI clients as fallback")
        return get_vanilla_openai_client()
    except Exception as e:
        logger.warning(f"Failed to create native OpenAI clients: {e}")

    try:
        logger.info("Attempting to create native Azure OpenAI clients as fallback")
        return get_vanilla_azure_openai_client()
    except Exception as e:
        logger.warning(f"Failed to create native Azure OpenAI clients: {e}")

    raise ValueError(
        "No valid LLM provider could be initialized. "
        "Please configure OPENAI_API_KEY or Azure OpenAI settings. "
        "You can also set APP_LLM_PROVIDER to 'openai' or 'azure_openai'."
    )


def create_vanilla_embedding_client() -> BaseEmbeddingClient:
    """
    Create a vanilla embedding client based on app settings.

    Automatically selects between OpenAI and Azure OpenAI based on APP_LLM_PROVIDER
    environment variable. Falls back to trying available providers if not set.

    Returns:
        BaseEmbeddingClient instance (OpenAI or Azure OpenAI)

    Raises:
        ValueError: If no valid LLM provider can be initialized

    Example:
        >>> # Set APP_LLM_PROVIDER=openai or APP_LLM_PROVIDER=azure_openai
        >>> client = create_vanilla_embedding_client()
        >>> response = client.create_embeddings("Hello world")
    """
    try:
        app_settings = settings_factory.create_app_settings()
        provider = app_settings.llm_provider.lower()

        logger.info(f"Creating vanilla embedding client with provider: {provider}")

        if provider == "openai":
            return create_default_embedding_client(client_type="openai")
        elif provider == "azure_openai":
            return create_default_embedding_client(client_type="azure_openai")
        else:
            logger.warning(f"Unknown LLM provider '{provider}', trying OpenAI first")

    except Exception as e:
        logger.warning(f"Failed to get app settings or create client with configured provider: {e}")

    # Fallback: Try OpenAI first, then Azure OpenAI
    try:
        logger.info("Attempting to create OpenAI embedding client as fallback")
        return create_default_embedding_client(client_type="openai")
    except Exception as e:
        logger.warning(f"Failed to create OpenAI embedding client: {e}")

    try:
        logger.info("Attempting to create Azure OpenAI embedding client as fallback")
        return create_default_embedding_client(client_type="azure_openai")
    except Exception as e:
        logger.warning(f"Failed to create Azure OpenAI embedding client: {e}")

    raise ValueError(
        "No valid LLM embedding provider could be initialized. "
        "Please configure OPENAI_API_KEY and OPENAI_EMBEDDING_MODEL or Azure OpenAI settings. "
        "You can also set APP_LLM_PROVIDER to 'openai' or 'azure_openai'."
    )


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def test_factory():
        """Test LLM client factory with various creation methods"""
        test_messages = [
            {"role": "user", "content": "Hello, this is a test message."}
        ]

        print("=" * 60)
        print("Testing LLM Client Factory")
        print("=" * 60)

        # Method 1: Using factory pattern
        print("\n1. Testing factory pattern...")
        try:
            factory = LLMClientFactory.create_from_default("openai")
            chat_client = factory.create_client()
            response = chat_client.chat(test_messages)
            print(f"✓ Factory chat response: {response[:100]}...")
        except Exception as e:
            print(f"✗ Factory pattern failed: {e}")

        # Method 2: Using convenience functions
        print("\n2. Testing convenience functions...")
        try:
            quick_chat_client = create_default_chat_client(client_type="openai")
            quick_response = quick_chat_client.chat(test_messages)
            print(f"✓ Quick chat response: {quick_response[:100]}...")
        except Exception as e:
            print(f"✗ Convenience function failed: {e}")

        # Method 3: Using vanilla client (automatic provider selection)
        print("\n3. Testing vanilla client (auto provider selection)...")
        print("   Set APP_LLM_PROVIDER=openai or APP_LLM_PROVIDER=azure_openai")
        try:
            vanilla_client = create_vanilla_chat_client()

            # Test sync
            vanilla_response = vanilla_client.chat(test_messages)
            print(f"✓ Vanilla client (sync): {vanilla_response[:100]}...")

            # Test async on same client
            async_vanilla_response = await vanilla_client.async_chat_completion(test_messages)
            print(f"✓ Vanilla client (async): {async_vanilla_response.choices[0].message.content[:100]}...")
        except Exception as e:
            print(f"✗ Vanilla client failed: {e}")

        # Test embedding clients
        print("\n4. Testing embedding clients...")
        try:
            embedding_client = create_default_embedding_client(client_type="openai")
            embedding_response = embedding_client.create_embeddings("Test text for embedding")
            print(f"✓ Embeddings created: {len(embedding_response.data)} embeddings")
        except Exception as e:
            print(f"✗ Embedding client failed: {e}")

        # Test vanilla embedding client (sync + async)
        print("\n5. Testing vanilla embedding client (sync + async)...")
        try:
            vanilla_embed_client = create_vanilla_embedding_client()

            # Sync
            vanilla_embed_response = vanilla_embed_client.create_embeddings("Test text")
            print(f"✓ Vanilla embeddings (sync): {len(vanilla_embed_response.data)} embeddings")

            # Async on same client
            async_embed_response = await vanilla_embed_client.async_create_embeddings("Test text async")
            print(f"✓ Vanilla embeddings (async): {len(async_embed_response.data)} embeddings")
        except Exception as e:
            print(f"✗ Vanilla embedding client failed: {e}")

        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

    asyncio.run(test_factory())
