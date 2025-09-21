from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import litellm
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.core import settings
from .base import BaseChatClient, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class LiteLLMChatClient(BaseChatClient):
    """LiteLLM chat completion client with sync and async support"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LiteLLM client

        Args:
            api_key: API key (uses settings if not provided)
            model: Default model to use (uses settings if not provided)
        """
        self.api_key = api_key or settings.openai.api_key
        self.default_model = model or settings.openai.model
        self.default_temperature = settings.openai.temperature
        self.default_max_tokens = settings.openai.max_tokens

        # Validate required configuration
        if not self.api_key:
            raise ValueError("API key is required for LiteLLM. Set OPENAI_API_KEY in environment or pass api_key parameter.")

        if not self.default_model:
            raise ValueError("Model is required for LiteLLM. Set OPENAI_MODEL in environment or pass model parameter.")

        # Configure LiteLLM
        litellm.set_verbose = False  # Set to True for debugging

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        return model or self.default_model

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
                "provider": self._get_provider_from_model(response.model)
            }
        )

    def _get_provider_from_model(self, model: str) -> str:
        """Determine provider from model name - only supports OpenAI"""
        if model.startswith("gpt-"):
            return "openai"
        else:
            return "openai"  # Default to OpenAI since we only support OpenAI models

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

            # Prepare LiteLLM parameters
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                "api_key": self.api_key,
                **kwargs
            }

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

            # Prepare LiteLLM parameters
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                "api_key": self.api_key,
                **kwargs
            }

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

            # Prepare LiteLLM parameters
            completion_params = {
                "model": self._get_model(model),
                "messages": normalized_messages,
                "temperature": self._get_temperature(temperature),
                "max_tokens": self._get_max_tokens(max_tokens),
                "api_key": self.api_key,
                "tools": tools,
                "tool_choice": "auto",
                **kwargs
            }

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

    asyncio.run(test_client())