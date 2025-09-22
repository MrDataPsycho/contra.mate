from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import litellm
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.core import settings
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from .base import BaseEmbeddingClient, EmbeddingResponse

logger = logging.getLogger(__name__)


class LiteLLMEmbeddingClient(BaseEmbeddingClient):
    """LiteLLM embedding client with sync and async support for OpenAI and Azure OpenAI"""

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        embedding_model: Optional[str] = None,
        use_azure: bool = False,
        azure_settings: Optional[object] = None,
        # Direct Azure parameters (certificate-based authentication required)
        token_provider: Optional[callable] = None,
        azure_endpoint: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize LiteLLM embedding client

        Args:
            api_key: API key (uses settings if not provided)
            embedding_model: Default embedding model to use (uses settings if not provided)
            use_azure: Whether to use Azure OpenAI (default: False)
            azure_settings: Azure OpenAI settings (uses global settings if not provided)
            token_provider: Certificate-based token provider callable for Azure (required for Azure)
            azure_endpoint: Azure endpoint URL (required for Azure)
            api_version: API version (optional for Azure)
        """
        # Initialize base client
        super().__init__(api_key=api_key)
        
        self.use_azure = use_azure
        
        if use_azure:
            # Azure requires certificate-based authentication only
            self.azure_settings = azure_settings or settings.azure_openai
            
            # Use direct parameters if provided, otherwise fall back to settings
            self.token_provider = token_provider or get_cert_token_provider(self.azure_settings)
            self.azure_endpoint = azure_endpoint or self.azure_settings.azure_endpoint
            self.api_version = api_version or self.azure_settings.api_version
            
            # For model, use settings as fallback
            self.default_embedding_model = embedding_model or self.azure_settings.embedding_model
            
            # Validate required Azure parameters
            if not self.token_provider:
                raise ValueError("Certificate-based token provider is required for Azure OpenAI.")
            
            if not self.azure_endpoint:
                raise ValueError("Azure endpoint is required for Azure OpenAI.")
        else:
            # Standard OpenAI configuration
            self.api_key = api_key or settings.openai.api_key
            self.default_embedding_model = embedding_model or settings.openai.embedding_model
            
            # Validate OpenAI configuration
            if not self.api_key:
                raise ValueError("API key is required for LiteLLM embedding. Set OPENAI_API_KEY in environment or pass api_key parameter.")

        if not self.default_embedding_model:
            raise ValueError("Embedding model is required for LiteLLM. Set appropriate embedding model in environment or pass embedding_model parameter.")

        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging

    def _get_azure_token(self) -> str:
        """Get fresh Azure token"""
        if self.use_azure:
            return self.token_provider()
        return None

    def _prepare_azure_params(self, **kwargs) -> Dict[str, Any]:
        """Prepare Azure-specific parameters for LiteLLM"""
        if self.use_azure:
            # Get fresh token for each request and pass directly to LiteLLM
            token = self._get_azure_token()
            
            azure_params = {
                "api_key": token,
                "api_base": self.azure_endpoint,
                "api_version": self.api_version,
                "api_type": "azure",  # Explicitly set for LiteLLM
                **kwargs
            }
            return azure_params
        return {"api_key": self.api_key, **kwargs}

    def _get_embedding_model(self, model: Optional[str] = None) -> str:
        """Get embedding model name, using default if not specified"""
        selected_model = model or self.default_embedding_model
        
        # For Azure, ensure model name is prefixed correctly for LiteLLM
        if self.use_azure:
            if not selected_model.startswith("azure/"):
                selected_model = f"azure/{selected_model}"
        
        return selected_model

    def _create_embedding_response(self, response: Any) -> EmbeddingResponse:
        """Convert LiteLLM embedding response to standardized format"""
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
                "object": getattr(response, 'object', None),
                "provider": self._get_provider_from_model(response.model),
                "use_azure": self.use_azure
            }
        )

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name"""
        if self.use_azure or model.startswith("azure/"):
            return "azure_openai"
        elif model.startswith("text-embedding"):
            return "openai"
        else:
            return "openai"  # Default to OpenAI

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
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            EmbeddingResponse: Standardized embedding response
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts
            
            # Set up parameters for LiteLLM embedding with Azure support
            embedding_params = {
                "model": self._get_embedding_model(model),
                "input": input_texts,
                **kwargs
            }
            
            # Add Azure or OpenAI specific parameters
            embedding_params.update(self._prepare_azure_params())

            response = litellm.embedding(**embedding_params)
            
            return self._create_embedding_response(response)

        except (AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"LiteLLM API error in embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLM embedding creation: {e}")
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
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            EmbeddingResponse: Standardized embedding response
        """
        try:
            # Ensure texts is a list
            input_texts = [texts] if isinstance(texts, str) else texts
            
            # Set up parameters for LiteLLM embedding with Azure support
            embedding_params = {
                "model": self._get_embedding_model(model),
                "input": input_texts,
                **kwargs
            }
            
            # Add Azure or OpenAI specific parameters
            embedding_params.update(self._prepare_azure_params())

            response = await litellm.aembedding(**embedding_params)
            
            return self._create_embedding_response(response)

        except (AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"LiteLLM API error in async embedding creation: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLM async embedding creation: {e}")
            raise


if __name__ == "__main__":
    import asyncio

    async def test_embedding_client():
        # Test OpenAI
        print("Testing OpenAI LiteLLM embedding client...")
        try:
            client = LiteLLMEmbeddingClient()

            test_texts = [
                "This is a test sentence for embedding.",
                "Another test sentence to embed."
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
            single_response = client.create_embeddings("Single test sentence.")
            print(f"Single response: {len(single_response.embeddings)} embeddings, {single_response.dimensions} dimensions")

        except Exception as e:
            print(f"OpenAI test failed: {e}")

        # Test Azure OpenAI with certificate-based authentication
        try:
            print("\nTesting Azure OpenAI LiteLLM embedding client (certificate-based authentication)...")
            azure_client = LiteLLMEmbeddingClient(use_azure=True)
            
            azure_texts = [
                "This is a test sentence for Azure OpenAI embedding.",
                "Another test sentence to embed with Azure."
            ]
            
            azure_response = azure_client.create_embeddings(azure_texts)
            print(f"Azure response: {len(azure_response.embeddings)} embeddings, {azure_response.dimensions} dimensions")
            
        except Exception as e:
            print(f"Azure certificate test skipped (likely not configured): {e}")

        # Test Azure OpenAI with direct certificate parameters
        try:
            print("\nTesting Azure OpenAI LiteLLM embedding client (with direct certificate params)...")
            
            # Example of how to use direct certificate parameters
            azure_direct_client = LiteLLMEmbeddingClient(
                use_azure=True,
                token_provider=get_cert_token_provider(settings.azure_openai),
                azure_endpoint=settings.azure_openai.azure_endpoint,
                api_version=settings.azure_openai.api_version,
                embedding_model=settings.azure_openai.embedding_model
            )
            
            print("Azure direct certificate embedding client initialized successfully")
            azure_response = azure_direct_client.create_embeddings(azure_texts)
            print(f"Azure direct response: {len(azure_response.embeddings)} embeddings, {azure_response.dimensions} dimensions")
            
        except Exception as e:
            print(f"Azure direct certificate params test: {e}")

    asyncio.run(test_embedding_client())