from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import litellm
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.core import settings
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.utils.clients.ai.base import BaseChatClient, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class LiteLLMChatClient(BaseChatClient):
    """LiteLLM chat completion client with sync and async support for OpenAI and Azure OpenAI"""

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        use_azure: bool = False,
        azure_settings: Optional[object] = None,
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
            self.api_key = api_key or settings.openai.api_key
            self.default_model = model or settings.openai.model
            self.default_temperature = settings.openai.temperature
            self.default_max_tokens = settings.openai.max_tokens
            
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
                "api_key": token,
                "api_base": self.azure_endpoint,
                "api_version": self.api_version,
                "api_type": "azure",  # Explicitly set for LiteLLM
                **kwargs
            }
            return azure_params
        return {"api_key": self.api_key, **kwargs}

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

    async def test_client():
        # Test OpenAI
        print("Testing OpenAI LiteLLM client...")
        client = LiteLLMChatClient()

        test_messages = [
            {"role": "user", "content": "Hello, this is a test message."}
        ]

        # Test sync
        print("Testing sync completion...")
        response = client.chat_completion(test_messages)
        print(f"Sync response: {response.content}")

        # Test async
        print("Testing async completion...")
        async_response = await client.async_chat_completion(test_messages)
        print(f"Async response: {async_response.content}")

        # # Test Azure OpenAI with certificate-based authentication
        # try:
        #     print("\nTesting Azure OpenAI LiteLLM client (certificate-based authentication)...")
        #     azure_client = LiteLLMChatClient(use_azure=True)
            
        #     azure_messages = [
        #         {"role": "user", "content": "Hello from Azure OpenAI via LiteLLM!"}
        #     ]
            
        #     azure_response = azure_client.chat_completion(azure_messages)
        #     print(f"Azure response: {azure_response.content}")
            
        # except Exception as e:
        #     print(f"Azure certificate test skipped (likely not configured): {e}")

        # # Test Azure OpenAI with direct certificate parameters
        # try:
        #     print("\nTesting Azure OpenAI LiteLLM client (with direct certificate params)...")
            
        #     # Example of how to use direct certificate parameters
        #     azure_direct_client = LiteLLMChatClient(
        #         use_azure=True,
        #         token_provider=get_cert_token_provider(settings.azure_openai),
        #         azure_endpoint=settings.azure_openai.azure_endpoint,
        #         api_version=settings.azure_openai.api_version,
        #         model=settings.azure_openai.model
        #     )
            
        #     print("Azure direct certificate client initialized successfully")
        #     azure_response = azure_direct_client.chat_completion(azure_messages)
        #     print(f"Azure direct response: {azure_response.content}")
            
        # except Exception as e:
        #     print(f"Azure direct certificate params test: {e}")

    asyncio.run(test_client())