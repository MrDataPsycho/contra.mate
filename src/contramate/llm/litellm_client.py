from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import litellm
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.core import OpenAISettings, AOAICertSettings
from contramate.utils.settings.factory import settings_factory
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.llm.base import BaseChatClient, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class LiteLLMChatClient(BaseChatClient):
    """LiteLLM chat completion client with sync and async support for OpenAI and Azure OpenAI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        use_azure: bool = False,
        azure_settings: Optional[AOAICertSettings] = None,
        openai_settings: Optional[OpenAISettings] = None,
        # Direct Azure parameters (certificate-based authentication required)
        token_provider: Optional[callable] = None,
        azure_endpoint: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize LiteLLM client

        Args:
            api_key: API key (uses settings if not provided)
            model: Default model to use (uses settings if not provided)
            use_azure: Whether to use Azure OpenAI (default: False)
            azure_settings: Azure OpenAI settings object (creates from factory if not provided)
            openai_settings: OpenAI settings object (creates from factory if not provided)
            token_provider: Certificate-based token provider callable for Azure (required for Azure)
            azure_endpoint: Azure endpoint URL (required for Azure)
            api_version: API version (optional for Azure)
        """
        # Initialize base client
        super().__init__(api_key=api_key)

        self.use_azure = use_azure

        if use_azure:
            # Azure requires certificate-based authentication only
            self.azure_settings = azure_settings or settings_factory.create_azure_openai_settings()

            # Use direct parameters if provided, otherwise fall back to settings
            self.token_provider = token_provider or get_cert_token_provider(self.azure_settings)
            self.azure_endpoint = azure_endpoint or self.azure_settings.azure_endpoint
            self.api_version = api_version or self.azure_settings.api_version

            # For model, temperature, and max_tokens, use settings as fallback
            self.default_model = model or self.azure_settings.model
            self.default_temperature = self.azure_settings.temperature
            self.default_max_tokens = self.azure_settings.max_tokens

            # Validate required Azure parameters
            if not self.token_provider:
                raise ValueError("Certificate-based token provider is required for Azure OpenAI.")

            if not self.azure_endpoint:
                raise ValueError("Azure endpoint is required for Azure OpenAI.")
        else:
            # Standard OpenAI configuration
            _openai_settings = openai_settings or settings_factory.create_openai_settings()
            self.api_key = api_key or _openai_settings.api_key
            self.default_model = model or _openai_settings.model
            self.default_temperature = _openai_settings.temperature
            self.default_max_tokens = _openai_settings.max_tokens

            # Validate OpenAI configuration
            if not self.api_key:
                raise ValueError("API key is required for LiteLLM. Set OPENAI_API_KEY in environment or pass api_key parameter.")

        if not self.default_model:
            raise ValueError("Model is required for LiteLLM. Set appropriate model in environment or pass model parameter.")

        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging

    def _configure_azure_litellm(self):
        """Configure LiteLLM for Azure OpenAI - deprecated, using direct params instead"""
        # This method is kept for backward compatibility but no longer sets env vars
        pass

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

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        selected_model = model or self.default_model
        
        # For Azure, ensure model name is prefixed correctly for LiteLLM
        if self.use_azure:
            if not selected_model.startswith("azure/"):
                selected_model = f"azure/{selected_model}"
        
        return selected_model

    def _create_response(self, response: Any) -> ChatResponse:
        """Convert LiteLLM response to standardized format"""
        choice = response.choices[0]
        usage = response.usage

        return ChatResponse(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0,
            },
            response_id=response.id,
            finish_reason=choice.finish_reason,
            metadata={
                "created": getattr(response, 'created', None),
                "object": getattr(response, 'object', None),
                "provider": self._get_provider_from_model(response.model),
                "use_azure": self.use_azure
            }
        )

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name"""
        if self.use_azure or model.startswith("azure/"):
            return "azure_openai"
        elif model.startswith("gpt-"):
            return "openai"
        else:
            return "openai"  # Default to OpenAI

    def chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Synchronous chat completion

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            ChatResponse: Standardized response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            # Prepare LiteLLM parameters with Azure support
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                **kwargs
            }
            
            # Add Azure or OpenAI specific parameters
            completion_params.update(self._prepare_azure_params())

            response = litellm.completion(**completion_params)

            return self._create_response(response)

        except (AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"LiteLLM API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLM chat completion: {e}")
            raise

    async def async_chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Asynchronous chat completion

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            ChatResponse: Standardized response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            # Prepare LiteLLM parameters with Azure support
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                **kwargs
            }
            
            # Add Azure or OpenAI specific parameters
            completion_params.update(self._prepare_azure_params())

            response = await litellm.acompletion(**completion_params)

            return self._create_response(response)

        except (AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"LiteLLM API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLM async chat completion: {e}")
            raise

    def get_supported_models(self) -> List[str]:
        """Get list of supported OpenAI models via LiteLLM"""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-4.1-mini",
        ]

    def chat(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Simplified chat method for backward compatibility with agents

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            config: Additional configuration (e.g., response_format)
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            str: Response content
        """
        # Merge config into kwargs if provided
        if config:
            kwargs.update(config)

        response = self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.content

    def select_tool(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """
        Tool selection method for function calling

        Args:
            messages: List of chat messages
            tools: List of tool descriptions
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for LiteLLM API

        Returns:
            List[Any]: Tool calls from the response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            # Prepare LiteLLM parameters with Azure support
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                "tools": tools,
                "tool_choice": "auto",
                **kwargs
            }
            
            # Add Azure or OpenAI specific parameters
            completion_params.update(self._prepare_azure_params())

            response = litellm.completion(**completion_params)

            return response.choices[0].message.tool_calls or []

        except (AuthenticationError, RateLimitError, APIConnectionError, APIError) as e:
            logger.error(f"LiteLLM API error in tool selection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LiteLLM tool selection: {e}")
            raise



if __name__ == "__main__":
    import asyncio
    import time

    async def test_azure_certificate_chat():
        """Comprehensive test for Azure OpenAI chat with certificate-based authentication"""
        
        print("="*80)
        print("TESTING LiteLLM Chat Client with Azure Certificate Authentication")
        print("="*80)
        
        # Test messages
        test_messages = [
            {"role": "user", "content": "Hello! Please introduce yourself and explain what you can help with in 2-3 sentences."}
        ]
        
        complex_messages = [
            {"role": "system", "content": "You are a helpful AI assistant specialized in explaining technical concepts clearly."},
            {"role": "user", "content": "Explain what Azure OpenAI is and how certificate-based authentication works in about 100 words."}
        ]
        
        # Test 1: Azure Client with Settings (Certificate-based)
        print("\n" + "="*60)
        print("TEST 1: Azure Client Initialization (Settings-based)")
        print("="*60)
        
        try:
            print("Initializing Azure OpenAI chat client with certificate authentication...")
            azure_client = LiteLLMChatClient(use_azure=True)
            
            print(f"✅ Client initialized successfully")
            print(f"   - Model: {azure_client.default_model}")
            print(f"   - Endpoint: {azure_client.azure_endpoint}")
            print(f"   - API Version: {azure_client.api_version}")
            print(f"   - Token Provider: {'Available' if azure_client.token_provider else 'Missing'}")
            print(f"   - Temperature: {azure_client.default_temperature}")
            print(f"   - Max Tokens: {azure_client.default_max_tokens}")
            
        except Exception as e:
            print(f"❌ Client initialization failed: {e}")
            return
        
        # Test 2: Synchronous Chat Completion
        print("\n" + "="*60)
        print("TEST 2: Synchronous Chat Completion")
        print("="*60)
        
        try:
            print("Creating chat completion synchronously...")
            start_time = time.time()
            
            response = azure_client.chat_completion(test_messages)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Sync chat completion successful")
            print(f"   - Response: {response.content[:100]}..." if len(response.content) > 100 else f"   - Response: {response.content}")
            print(f"   - Model used: {response.model}")
            print(f"   - Duration: {duration:.2f} seconds")
            print(f"   - Prompt tokens: {response.usage.get('prompt_tokens', 'N/A')}")
            print(f"   - Completion tokens: {response.usage.get('completion_tokens', 'N/A')}")
            print(f"   - Total tokens: {response.usage.get('total_tokens', 'N/A')}")
            print(f"   - Provider: {response.metadata.get('provider', 'N/A')}")
            print(f"   - Finish reason: {response.finish_reason}")
            
        except Exception as e:
            print(f"❌ Sync chat completion failed: {e}")
            return
        
        # Test 3: Asynchronous Chat Completion
        print("\n" + "="*60)
        print("TEST 3: Asynchronous Chat Completion")
        print("="*60)
        
        try:
            print("Creating chat completion asynchronously...")
            start_time = time.time()
            
            async_response = await azure_client.async_chat_completion(complex_messages)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"✅ Async chat completion successful")
            print(f"   - Response: {async_response.content[:150]}..." if len(async_response.content) > 150 else f"   - Response: {async_response.content}")
            print(f"   - Model used: {async_response.model}")
            print(f"   - Duration: {duration:.2f} seconds")
            print(f"   - Total tokens: {async_response.usage.get('total_tokens', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Async chat completion failed: {e}")
        
        # Test 4: Different Temperature and Max Tokens
        print("\n" + "="*60)
        print("TEST 4: Custom Parameters (Temperature & Max Tokens)")
        print("="*60)
        
        try:
            print("Testing with custom temperature and max tokens...")
            
            creative_messages = [
                {"role": "user", "content": "Write a creative haiku about Azure cloud computing."}
            ]
            
            creative_response = azure_client.chat_completion(
                creative_messages,
                temperature=0.9,
                max_tokens=100
            )
            
            print(f"✅ Custom parameters test successful")
            print(f"   - Creative response: {creative_response.content}")
            print(f"   - Tokens used: {creative_response.usage.get('total_tokens', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Custom parameters test failed: {e}")
        
        # Test 5: Direct Certificate Parameters
        print("\n" + "="*60)
        print("TEST 5: Direct Certificate Parameters")
        print("="*60)
        
        try:
            print("Testing with direct certificate parameters...")
            
            direct_client = LiteLLMChatClient(
                use_azure=True,
                token_provider=get_cert_token_provider(settings.azure_openai),
                azure_endpoint=settings.azure_openai.azure_endpoint,
                api_version=settings.azure_openai.api_version,
                model=settings.azure_openai.model
            )
            
            print(f"✅ Direct parameters client initialized successfully")
            
            # Test with direct client
            direct_messages = [
                {"role": "user", "content": "Confirm you're running on Azure OpenAI with certificate authentication."}
            ]
            
            direct_response = direct_client.chat_completion(direct_messages)
            
            print(f"✅ Direct parameters chat completion successful")
            print(f"   - Response: {direct_response.content[:100]}..." if len(direct_response.content) > 100 else f"   - Response: {direct_response.content}")
            print(f"   - Model: {direct_response.model}")
            
        except Exception as e:
            print(f"❌ Direct parameters test failed: {e}")
        
        # Test 6: Error Handling
        print("\n" + "="*60)
        print("TEST 6: Error Handling")
        print("="*60)
        
        try:
            print("Testing error handling with invalid input...")
            
            # Test empty messages
            try:
                azure_client.chat_completion([])
                print("❌ Empty messages should have failed")
            except Exception as e:
                print(f"✅ Empty messages correctly rejected: {type(e).__name__}")
            
            # Test invalid temperature
            try:
                azure_client.chat_completion(test_messages, temperature=2.5)
                print("⚠️ High temperature accepted (might be valid)")
            except Exception as e:
                print(f"✅ Invalid temperature rejected: {type(e).__name__}")
                
        except Exception as e:
            print(f"Error handling test issue: {e}")
        
        print("\n" + "="*80)
        print("AZURE CERTIFICATE CHAT TESTS COMPLETED")
        print("="*80)

    # Also test OpenAI for comparison
    async def test_openai_chat():
        """Quick test of OpenAI chat for comparison"""
        
        print("\n" + "="*60)
        print("COMPARISON: OpenAI Chat Test")
        print("="*60)
        
        try:
            openai_client = LiteLLMChatClient()
            
            test_messages = [
                {"role": "user", "content": "Quick OpenAI chat test. Respond with 'OpenAI working!'"}
            ]
            
            response = openai_client.chat_completion(test_messages)
            
            print(f"✅ OpenAI chat successful")
            print(f"   - Response: {response.content}")
            print(f"   - Model: {response.model}")
            print(f"   - Provider: {response.metadata.get('provider', 'N/A')}")
            
        except Exception as e:
            print(f"❌ OpenAI test failed (likely API key not configured): {e}")

    # Run all tests
    async def run_all_tests():
        await test_azure_certificate_chat()
        await test_openai_chat()

    # Execute tests
    asyncio.run(run_all_tests())