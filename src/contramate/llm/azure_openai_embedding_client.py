from typing import List, Any, Optional, Union, Callable
from loguru import logger
from openai import AzureOpenAI, AsyncAzureOpenAI
from openai import OpenAIError

from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.utils.settings.core import AOAICertSettings
from contramate.llm.base import BaseEmbeddingClient


class AzureOpenAIEmbeddingClient(BaseEmbeddingClient):
    """
    Azure OpenAI embedding client with multiple authentication methods.

    Supports authentication in priority order:
    1. AOAICertSettings object (certificate-based)
    2. Azure AD token provider
    3. API key
    """

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2023-05-15",
        embedding_model: Optional[str] = None,
        api_key: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        azure_ad_cert_settings: Optional[AOAICertSettings] = None
    ):
        """
        Initialize Azure OpenAI embedding client with flexible authentication.

        Args:
            azure_endpoint: Azure OpenAI endpoint URL (required unless azure_ad_cert_settings provided)
            api_version: Azure OpenAI API version (default: "2023-05-15")
            embedding_model: Default embedding model (uses azure_ad_cert_settings.embedding_model if provided)
            api_key: API key for authentication (3rd priority)
            azure_ad_token_provider: Azure AD token provider callable (2nd priority)
            azure_ad_cert_settings: AOAICertSettings object (highest priority)

        Raises:
            ValueError: If required configuration is missing or no valid authentication method provided
        """
        # Initialize base client
        super().__init__()

        # Priority 1: Use AOAICertSettings if provided
        if azure_ad_cert_settings:
            logger.info("Initializing embedding client with AOAICertSettings (certificate-based auth)")
            self.azure_endpoint = azure_ad_cert_settings.azure_endpoint
            self.api_version = azure_ad_cert_settings.api_version
            self.default_embedding_model = embedding_model or azure_ad_cert_settings.embedding_model

            # Get certificate-based token provider
            try:
                token_provider = get_cert_token_provider(azure_ad_cert_settings)
                client_config = {
                    "azure_endpoint": self.azure_endpoint,
                    "api_version": self.api_version,
                    "azure_ad_token_provider": token_provider
                }
            except Exception as e:
                logger.error(f"Failed to initialize certificate token provider: {e}")
                raise

        # Priority 2: Use provided azure_ad_token_provider
        elif azure_ad_token_provider:
            logger.info("Initializing embedding client with provided Azure AD token provider")
            if not azure_endpoint:
                raise ValueError("azure_endpoint is required when using azure_ad_token_provider")
            if not embedding_model:
                raise ValueError("embedding_model is required when using azure_ad_token_provider")

            self.azure_endpoint = azure_endpoint
            self.api_version = api_version
            self.default_embedding_model = embedding_model

            client_config = {
                "azure_endpoint": azure_endpoint,
                "api_version": api_version,
                "azure_ad_token_provider": azure_ad_token_provider
            }

        # Priority 3: Use API key
        elif api_key:
            logger.info("Initializing embedding client with API key authentication")
            if not azure_endpoint:
                raise ValueError("azure_endpoint is required when using api_key")
            if not embedding_model:
                raise ValueError("embedding_model is required when using api_key")

            self.azure_endpoint = azure_endpoint
            self.api_version = api_version
            self.default_embedding_model = embedding_model

            client_config = {
                "azure_endpoint": azure_endpoint,
                "api_version": api_version,
                "api_key": api_key
            }

        else:
            raise ValueError(
                "No valid authentication method provided. "
                "Please provide one of: azure_ad_cert_settings, azure_ad_token_provider, or api_key"
            )

        # Initialize Azure OpenAI clients
        try:
            self._sync_client = AzureOpenAI(**client_config)
            self._async_client = AsyncAzureOpenAI(**client_config)
            logger.info("Azure OpenAI embedding clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI embedding clients: {e}")
            raise

    def _get_embedding_model(self, model: Optional[str] = None) -> str:
        """Get embedding model name, using default if not specified"""
        return model or self.default_embedding_model

    def create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Create embeddings for text input(s)

        Args:
            texts: Text string or list of text strings to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            Native OpenAI CreateEmbeddingResponse object
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts

            response = self._sync_client.embeddings.create(
                model=self._get_embedding_model(model),
                input=input_texts,
                **kwargs
            )

            return response

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error in embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI embedding creation: {e}")
            raise

    async def async_create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Create embeddings for text input(s) asynchronously

        Args:
            texts: Text string or list of text strings to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            Native OpenAI CreateEmbeddingResponse object
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts

            response = await self._async_client.embeddings.create(
                model=self._get_embedding_model(model),
                input=input_texts,
                **kwargs
            )

            return response

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error in async embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI async embedding creation: {e}")
            raise

    def create_batch_embeddings(
        self,
        texts_batches: List[List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """
        Create embeddings for multiple batches of texts

        Args:
            texts_batches: List of text batches to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            List of native OpenAI CreateEmbeddingResponse objects
        """
        responses = []
        for batch in texts_batches:
            response = self.create_embeddings(batch, model, **kwargs)
            responses.append(response)
        return responses

    async def async_create_batch_embeddings(
        self,
        texts_batches: List[List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """
        Create embeddings for multiple batches of texts asynchronously

        Args:
            texts_batches: List of text batches to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            List of native OpenAI CreateEmbeddingResponse objects
        """
        import asyncio

        tasks = [
            self.async_create_embeddings(batch, model, **kwargs)
            for batch in texts_batches
        ]

        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    import asyncio
    import os

    async def test_azure_embedding_client():
        """
        Test Azure OpenAI embedding client with different authentication methods.
        Set environment variables to test each method.
        """
        test_texts = [
            "This is a test sentence for Azure OpenAI embedding.",
            "Another test sentence to embed with Azure."
        ]

        print("=" * 60)
        print("Testing Azure OpenAI Embedding Client")
        print("=" * 60)

        # Method 1: Using AOAICertSettings (highest priority)
        try:
            print("\n1. Testing with AOAICertSettings (certificate-based)...")
            from contramate.utils.settings.factory import SettingsFactory

            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIEmbeddingClient(azure_ad_cert_settings=settings)

            response = client.create_embeddings(test_texts)
            print(f"✓ Certificate auth: {len(response.data)} embeddings created")
            print(f"  Model: {response.model}")
            print(f"  Dimensions: {len(response.data[0].embedding)}")
            print(f"  Usage: {response.usage.total_tokens} tokens")
        except Exception as e:
            print(f"✗ Certificate auth failed: {e}")

        # Method 2: Using API key
        try:
            print("\n2. Testing with API key authentication...")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")

            if api_key and endpoint:
                client = AzureOpenAIEmbeddingClient(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    embedding_model=embedding_model
                )

                response = client.create_embeddings(test_texts)
                print(f"✓ API key auth: {len(response.data)} embeddings created")
                print(f"  Model: {response.model}")
                print(f"  Dimensions: {len(response.data[0].embedding)}")
            else:
                print("✗ API key auth skipped: Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
        except Exception as e:
            print(f"✗ API key auth failed: {e}")

        # Test async completion
        try:
            print("\n3. Testing async embedding creation...")
            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIEmbeddingClient(azure_ad_cert_settings=settings)

            async_response = await client.async_create_embeddings(test_texts)
            print(f"✓ Async embeddings: {len(async_response.data)} embeddings created")
        except Exception as e:
            print(f"✗ Async embeddings failed: {e}")

        # Test single string
        try:
            print("\n4. Testing single string embedding...")
            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIEmbeddingClient(azure_ad_cert_settings=settings)

            single_response = client.create_embeddings("Single test sentence for Azure.")
            print(f"✓ Single string: {len(single_response.data)} embedding created")
        except Exception as e:
            print(f"✗ Single string failed: {e}")

        # Test batch embeddings
        try:
            print("\n5. Testing batch embeddings...")
            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIEmbeddingClient(azure_ad_cert_settings=settings)

            batches = [
                ["First batch sentence 1", "First batch sentence 2"],
                ["Second batch sentence 1", "Second batch sentence 2"]
            ]
            batch_responses = client.create_batch_embeddings(batches)
            print(f"✓ Batch embeddings: {len(batch_responses)} batches processed")
            for i, batch_resp in enumerate(batch_responses):
                print(f"  Batch {i + 1}: {len(batch_resp.data)} embeddings")
        except Exception as e:
            print(f"✗ Batch embeddings failed: {e}")

        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

    asyncio.run(test_azure_embedding_client())