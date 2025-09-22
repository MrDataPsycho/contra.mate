from typing import List, Any, Optional, Union
import logging
from openai import AzureOpenAI, AsyncAzureOpenAI
from openai import OpenAIError

from contramate.utils.settings.core import settings
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.utils.clients.ai.base import BaseEmbeddingClient, EmbeddingResponse

logger = logging.getLogger(__name__)


class AzureOpenAIEmbeddingClient(BaseEmbeddingClient):
    """Azure OpenAI embedding client with certificate-based authentication"""

    def __init__(self, azure_settings: Optional[object] = None):
        """
        Initialize Azure OpenAI embedding client with certificate authentication

        Args:
            azure_settings: Azure OpenAI settings (uses global settings if not provided)
        """
        self.azure_settings = azure_settings or settings.azure_openai
        
        # Initialize base client
        super().__init__()
        
        self.default_embedding_model = self.azure_settings.embedding_model

        # Validate required configuration
        if not self.azure_settings.tenant_id:
            raise ValueError("Azure tenant ID is required. Set AZURE_OPENAI_TENANT_ID in environment.")
        
        if not self.azure_settings.client_id:
            raise ValueError("Azure client ID is required. Set AZURE_OPENAI_CLIENT_ID in environment.")
        
        if not self.azure_settings.azure_endpoint:
            raise ValueError("Azure endpoint is required. Set AZURE_OPENAI_AZURE_ENDPOINT in environment.")

        if not self.default_embedding_model:
            raise ValueError("Azure embedding model is required. Set AZURE_OPENAI_EMBEDDING_MODEL in environment.")

        # Get certificate-based token provider
        try:
            self.token_provider = get_cert_token_provider(self.azure_settings)
        except Exception as e:
            logger.error(f"Failed to initialize certificate token provider: {e}")
            raise

        # Initialize Azure OpenAI clients
        client_config = {
            "azure_endpoint": self.azure_settings.azure_endpoint,
            "api_version": self.azure_settings.api_version,
            "azure_ad_token_provider": self.token_provider
        }

        try:
            self._sync_client = AzureOpenAI(**client_config)
            self._async_client = AsyncAzureOpenAI(**client_config)
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI embedding clients: {e}")
            raise

    def _get_embedding_model(self, model: Optional[str] = None) -> str:
        """Get embedding model name, using default if not specified"""
        return model or self.default_embedding_model

    def _create_embedding_response(self, response: Any) -> EmbeddingResponse:
        """Convert Azure OpenAI embedding response to standardized format"""
        usage = response.usage
        embeddings = [data.embedding for data in response.data]
        
        return EmbeddingResponse(
            embeddings=embeddings,
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            dimensions=len(embeddings[0]) if embeddings else 0,
            metadata={
                "object": response.object,
                "provider": "azure_openai"
            }
        )

    def create_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """
        Create embeddings for text input(s)

        Args:
            texts: Text string or list of text strings to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            EmbeddingResponse: Standardized embedding response
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts
            
            response = self._sync_client.embeddings.create(
                model=self._get_embedding_model(model),
                input=input_texts,
                **kwargs
            )
            
            return self._create_embedding_response(response)

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
    ) -> EmbeddingResponse:
        """
        Create embeddings for text input(s) asynchronously

        Args:
            texts: Text string or list of text strings to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            EmbeddingResponse: Standardized embedding response
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts
            
            response = await self._async_client.embeddings.create(
                model=self._get_embedding_model(model),
                input=input_texts,
                **kwargs
            )
            
            return self._create_embedding_response(response)

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
    ) -> List[EmbeddingResponse]:
        """
        Create embeddings for multiple batches of texts

        Args:
            texts_batches: List of text batches to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            List[EmbeddingResponse]: List of embedding responses for each batch
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
    ) -> List[EmbeddingResponse]:
        """
        Create embeddings for multiple batches of texts asynchronously

        Args:
            texts_batches: List of text batches to embed
            model: Embedding model to use (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            List[EmbeddingResponse]: List of embedding responses for each batch
        """
        import asyncio
        
        tasks = [
            self.async_create_embeddings(batch, model, **kwargs)
            for batch in texts_batches
        ]
        
        return await asyncio.gather(*tasks)


if __name__ == "__main__":
    import asyncio

    async def test_azure_embedding_client():
        try:
            client = AzureOpenAIEmbeddingClient()

            test_texts = [
                "This is a test sentence for Azure OpenAI embedding.",
                "Another test sentence to embed with Azure."
            ]

            # Test sync
            print("Testing sync embedding creation...")
            response = client.create_embeddings(test_texts)
            print(f"Sync response: {len(response.embeddings)} embeddings, {response.dimensions} dimensions")

            # Test async
            print("Testing async embedding creation...")
            async_response = await client.async_create_embeddings(test_texts)
            print(f"Async response: {len(async_response.embeddings)} embeddings, {async_response.dimensions} dimensions")

            # Test single string
            print("Testing single string embedding...")
            single_response = client.create_embeddings("Single test sentence for Azure.")
            print(f"Single response: {len(single_response.embeddings)} embeddings, {single_response.dimensions} dimensions")

        except Exception as e:
            print(f"Test failed: {e}")

    asyncio.run(test_azure_embedding_client())