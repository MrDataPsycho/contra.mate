from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import litellm
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.factory import settings_factory
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.llm.base import BaseEmbeddingClient, EmbeddingResponse

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
            azure_openai_settings = settings_factory.create_azure_openai_settings()
            self.azure_settings = azure_settings or azure_openai_settings
            
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
            openai_settings = settings_factory.create_openai_settings()
            self.api_key = api_key or openai_settings.api_key
            self.default_embedding_model = embedding_model or openai_settings.embedding_model
            
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
                **kwargs,  # Include kwargs first
                "api_key": token,  # Override with our token (never allow override)
                "api_base": self.azure_endpoint,
                "api_version": self.api_version,
                # Note: api_type is not needed for newer LiteLLM versions
            }
            return azure_params
        return {**kwargs, "api_key": self.api_key}  # Override with our API key

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
        try:
            # Debug: Log response structure
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response data type: {type(response.data) if hasattr(response, 'data') else 'No data attr'}")
            if hasattr(response, 'data') and response.data:
                logger.debug(f"First data item type: {type(response.data[0])}")
                logger.debug(f"First data item: {response.data[0] if len(str(response.data[0])) < 200 else 'Too long to log'}")
            
            usage = response.usage if hasattr(response, 'usage') else None
            
            # Handle different response formats
            if hasattr(response, 'data') and response.data:
                embeddings = []
                for data_item in response.data:
                    if hasattr(data_item, 'embedding'):
                        # Standard format: data_item.embedding
                        embeddings.append(data_item.embedding)
                    elif isinstance(data_item, dict) and 'embedding' in data_item:
                        # Dict format: data_item['embedding']
                        embeddings.append(data_item['embedding'])
                    elif isinstance(data_item, (list, tuple)):
                        # Direct embedding format
                        embeddings.append(list(data_item))
                    else:
                        logger.warning(f"Unexpected data item format: {type(data_item)}")
                        # Try to extract embedding from the item
                        if hasattr(data_item, '__dict__'):
                            item_dict = data_item.__dict__
                            if 'embedding' in item_dict:
                                embeddings.append(item_dict['embedding'])
                            else:
                                logger.error(f"No embedding found in data item: {item_dict.keys()}")
                                raise ValueError(f"Cannot extract embedding from data item: {type(data_item)}")
                        else:
                            raise ValueError(f"Cannot extract embedding from data item: {type(data_item)}")
            else:
                raise ValueError("No data found in response")
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=response.model if hasattr(response, 'model') else 'unknown',
                usage={
                    "prompt_tokens": usage.prompt_tokens if usage and hasattr(usage, 'prompt_tokens') else 0,
                    "total_tokens": usage.total_tokens if usage and hasattr(usage, 'total_tokens') else 0,
                },
                dimensions=len(embeddings[0]) if embeddings and len(embeddings[0]) > 0 else 0,
                metadata={
                    "object": getattr(response, 'object', None),
                    "provider": self._get_provider_from_model(response.model if hasattr(response, 'model') else 'unknown'),
                    "use_azure": self.use_azure
                }
            )
        except Exception as e:
            logger.error(f"Error creating embedding response: {e}")
            logger.error(f"Response type: {type(response)}")
            if hasattr(response, '__dict__'):
                logger.error(f"Response attributes: {list(response.__dict__.keys())}")
            raise

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
    import time

    async def test_azure_certificate_embedding():
        """Comprehensive test for Azure OpenAI embedding with certificate-based authentication"""
        
        print("="*80)
        print("TESTING LiteLLM Embedding Client with Azure Certificate Authentication")
        print("="*80)
        
        # Test data
        test_texts = [
            "This is a comprehensive test for Azure OpenAI embedding using certificate authentication.",
            "LiteLLM provides a unified interface for multiple AI providers including Azure OpenAI.",
            "Certificate-based authentication ensures secure access to Azure resources.",
            "Embeddings convert text into high-dimensional vectors for semantic analysis."
        ]
        
        single_text = "Single sentence test for Azure OpenAI embedding via LiteLLM."
        
        # Test 1: Azure Client with Settings (Certificate-based)
        print("\n" + "="*60)
        print("TEST 1: Azure Client Initialization (Settings-based)")
        print("="*60)
        
        try:
            print("Initializing Azure OpenAI embedding client with certificate authentication...")
            azure_client = LiteLLMEmbeddingClient(use_azure=True)
            
            print(f"✅ Client initialized successfully")
            print(f"   - Model: {azure_client.default_embedding_model}")
            print(f"   - Endpoint: {azure_client.azure_endpoint}")
            print(f"   - API Version: {azure_client.api_version}")
            print(f"   - Token Provider: {'Available' if azure_client.token_provider else 'Missing'}")
            
        except Exception as e:
            print(f"❌ Client initialization failed: {e}")
            return
        
        # Test 2: Synchronous Embedding Creation
        print("\n" + "="*60)
        print("TEST 2: Synchronous Embedding Creation")
        print("="*60)
        
        try:
            print("Creating embeddings synchronously...")
            start_time = time.time()
            
            response = azure_client.create_embeddings(test_texts)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Sync embeddings created successfully")
            print(f"   - Number of embeddings: {len(response.embeddings)}")
            print(f"   - Embedding dimensions: {response.dimensions}")
            print(f"   - Model used: {response.model}")
            print(f"   - Duration: {duration:.2f} seconds")
            print(f"   - Tokens used: {response.usage.get('total_tokens', 'N/A')}")
            print(f"   - Provider: {response.metadata.get('provider', 'N/A')}")
            
            # Verify embedding quality
            if response.embeddings and len(response.embeddings[0]) > 0:
                first_embedding = response.embeddings[0]
                print(f"   - First embedding preview: [{first_embedding[0]:.6f}, {first_embedding[1]:.6f}, ...]")
            
        except Exception as e:
            print(f"❌ Sync embedding creation failed: {e}")
            return
        
        # Test 3: Asynchronous Embedding Creation
        print("\n" + "="*60)
        print("TEST 3: Asynchronous Embedding Creation")
        print("="*60)
        
        try:
            print("Creating embeddings asynchronously...")
            start_time = time.time()
            
            async_response = await azure_client.async_create_embeddings(test_texts)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Async embeddings created successfully")
            print(f"   - Number of embeddings: {len(async_response.embeddings)}")
            print(f"   - Embedding dimensions: {async_response.dimensions}")
            print(f"   - Model used: {async_response.model}")
            print(f"   - Duration: {duration:.2f} seconds")
            print(f"   - Tokens used: {async_response.usage.get('total_tokens', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Async embedding creation failed: {e}")
        
        # Test 4: Single Text Embedding
        print("\n" + "="*60)
        print("TEST 4: Single Text Embedding")
        print("="*60)
        
        try:
            print("Creating embedding for single text...")
            single_response = azure_client.create_embeddings(single_text)
            
            print(f"✅ Single text embedding created successfully")
            print(f"   - Number of embeddings: {len(single_response.embeddings)}")
            print(f"   - Embedding dimensions: {single_response.dimensions}")
            print(f"   - Model used: {single_response.model}")
            
        except Exception as e:
            print(f"❌ Single text embedding failed: {e}")
        
        # Test 5: Direct Certificate Parameters
        print("\n" + "="*60)
        print("TEST 5: Direct Certificate Parameters")
        print("="*60)
        
        try:
            print("Testing with direct certificate parameters...")
            
            azure_openai_settings = settings_factory.create_azure_openai_settings()
            direct_client = LiteLLMEmbeddingClient(
                use_azure=True,
                token_provider=get_cert_token_provider(azure_openai_settings),
                azure_endpoint=azure_openai_settings.azure_endpoint,
                api_version=azure_openai_settings.api_version,
                embedding_model=azure_openai_settings.embedding_model
            )
            
            print(f"✅ Direct parameters client initialized successfully")
            
            # Test with direct client
            direct_response = direct_client.create_embeddings([
                "Testing direct certificate parameter approach for Azure OpenAI."
            ])
            
            print(f"✅ Direct parameters embedding created successfully")
            print(f"   - Dimensions: {direct_response.dimensions}")
            print(f"   - Model: {direct_response.model}")
            
        except Exception as e:
            print(f"❌ Direct parameters test failed: {e}")
        
        # Test 6: Error Handling
        print("\n" + "="*60)
        print("TEST 6: Error Handling")
        print("="*60)
        
        try:
            print("Testing error handling with invalid input...")
            
            # Test empty input
            try:
                azure_client.create_embeddings([])
                print("❌ Empty input should have failed")
            except Exception as e:
                print(f"✅ Empty input correctly rejected: {type(e).__name__}")
            
            # Test None input
            try:
                azure_client.create_embeddings(None)
                print("❌ None input should have failed")
            except Exception as e:
                print(f"✅ None input correctly rejected: {type(e).__name__}")
                
        except Exception as e:
            print(f"Error handling test issue: {e}")
        
        print("\n" + "="*80)
        print("AZURE CERTIFICATE EMBEDDING TESTS COMPLETED")
        print("="*80)

    # Also test OpenAI for comparison
    async def test_openai_embedding():
        """Quick test of OpenAI embedding for comparison"""
        
        print("\n" + "="*60)
        print("COMPARISON: OpenAI Embedding Test")
        print("="*60)
        
        try:
            openai_client = LiteLLMEmbeddingClient()
            
            test_text = "Quick OpenAI embedding test for comparison."
            response = openai_client.create_embeddings(test_text)
            
            print(f"✅ OpenAI embedding successful")
            print(f"   - Dimensions: {response.dimensions}")
            print(f"   - Model: {response.model}")
            print(f"   - Provider: {response.metadata.get('provider', 'N/A')}")
            
        except Exception as e:
            print(f"❌ OpenAI test failed (likely API key not configured): {e}")

    # Run all tests
    async def run_all_tests():
        await test_azure_certificate_embedding()
        await test_openai_embedding()

    # Execute tests
    asyncio.run(run_all_tests())