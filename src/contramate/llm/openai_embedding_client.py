from typing import List, Dict, Any, Optional, Union
from loguru import logger
from openai import OpenAI, AsyncOpenAI
from openai import OpenAIError

from contramate.utils.settings.core import OpenAISettings
from contramate.utils.settings.factory import settings_factory
from contramate.llm.base import BaseEmbeddingClient


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """OpenAI embedding client with sync and async support"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = None,
        openai_settings: Optional[OpenAISettings] = None
    ):
        """
        Initialize OpenAI embedding client

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            embedding_model: Default embedding model to use (uses settings if not provided)
            openai_settings: OpenAI settings object (creates from factory if not provided)
        """
        settings = openai_settings or settings_factory.create_openai_settings()
        super().__init__(api_key=api_key or settings.api_key)
        self.default_embedding_model = embedding_model or settings.embedding_model

        # Validate required configuration
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in environment or pass api_key parameter.")

        if not self.default_embedding_model:
            raise ValueError("OpenAI embedding model is required. Set OPENAI_EMBEDDING_MODEL in environment or pass embedding_model parameter.")

        # Initialize sync and async clients
        client_config = {"api_key": self.api_key}

        try:
            self._sync_client = OpenAI(**client_config)
            self._async_client = AsyncOpenAI(**client_config)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embedding clients: {e}")
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
            **kwargs: Additional parameters for OpenAI API

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
            logger.error(f"OpenAI API error in embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI embedding creation: {e}")
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
            **kwargs: Additional parameters for OpenAI API

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
            logger.error(f"OpenAI API error in async embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI async embedding creation: {e}")
            raise


if __name__ == "__main__":
    import asyncio

    async def test_embedding_client():
        """Test OpenAI embedding client with native response objects"""
        client = OpenAIEmbeddingClient()

        test_texts = [
            "This is a test sentence for embedding.",
            "Another test sentence to embed."
        ]

        print("=" * 60)
        print("Testing OpenAI Embedding Client")
        print("=" * 60)

        # Test sync
        print("\n1. Testing sync embedding creation...")
        response = client.create_embeddings(test_texts)
        print(f"✓ Sync embeddings: {len(response.data)} embeddings created")
        print(f"  Model: {response.model}")
        print(f"  Dimensions: {len(response.data[0].embedding)}")
        print(f"  Usage: {response.usage.total_tokens} tokens")

        # Test async
        print("\n2. Testing async embedding creation...")
        async_response = await client.async_create_embeddings(test_texts)
        print(f"✓ Async embeddings: {len(async_response.data)} embeddings created")
        print(f"  Dimensions: {len(async_response.data[0].embedding)}")

        # Test single string
        print("\n3. Testing single string embedding...")
        single_response = client.create_embeddings("Single test sentence.")
        print(f"✓ Single embedding: {len(single_response.data)} embedding created")
        print(f"  Dimensions: {len(single_response.data[0].embedding)}")

        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

    asyncio.run(test_embedding_client())