from typing import List, Dict, Any, Optional, Union
import logging
from openai import OpenAI, AsyncOpenAI
from openai import OpenAIError

from contramate.utils.settings.core import OpenAISettings
from contramate.utils.settings.factory import settings_factory
from contramate.llm.base import BaseChatClient, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class OpenAIChatClient(BaseChatClient):
    """OpenAI chat completion client with sync and async support"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        openai_settings: Optional[OpenAISettings] = None
    ):
        """
        Initialize OpenAI client

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Default model to use (uses settings if not provided)
            openai_settings: OpenAI settings object (creates from factory if not provided)
        """
        # Get settings from factory if not provided
        settings = openai_settings or settings_factory.create_openai_settings()

        super().__init__(api_key=api_key or settings.api_key)
        self.default_model = model or settings.model
        self.default_temperature = settings.temperature
        self.default_max_tokens = settings.max_tokens

        # Validate required configuration
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in environment or pass api_key parameter.")

        if not self.default_model:
            raise ValueError("OpenAI model is required. Set OPENAI_MODEL in environment or pass model parameter.")

        # Initialize sync and async clients
        client_config = {"api_key": self.api_key}

        try:
            self._sync_client = OpenAI(**client_config)
            self._async_client = AsyncOpenAI(**client_config)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI clients: {e}")
            raise

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        return model or self.default_model

    def _create_response(self, response: Any) -> ChatResponse:
        """Convert OpenAI response to standardized format"""
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
                "created": response.created,
                "object": response.object,
                "system_fingerprint": getattr(response, 'system_fingerprint', None)
            }
        )

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
            **kwargs: Additional parameters for OpenAI API

        Returns:
            ChatResponse: Standardized response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = self._sync_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_completion_tokens=self._get_max_tokens(max_tokens),
                **kwargs
            )

            return self._create_response(response)

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI chat completion: {e}")
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
            **kwargs: Additional parameters for OpenAI API

        Returns:
            ChatResponse: Standardized response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = await self._async_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_completion_tokens=self._get_max_tokens(max_tokens),
                **kwargs
            )

            return self._create_response(response)

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI async chat completion: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            models = self._sync_client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []

    async def async_get_available_models(self) -> List[str]:
        """Get list of available models (async)"""
        try:
            models = await self._async_client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []

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
            **kwargs: Additional parameters for OpenAI API

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
            **kwargs: Additional parameters for OpenAI API

        Returns:
            List[Any]: Tool calls from the response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = self._sync_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_completion_tokens=self._get_max_tokens(max_tokens),
                tools=tools,
                tool_choice="auto",
                **kwargs
            )

            return response.choices[0].message.tool_calls or []

        except OpenAIError as e:
            logger.error(f"OpenAI API error in tool selection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI tool selection: {e}")
            raise


if __name__ == "__main__":
    import asyncio

    async def test_client():
        client = OpenAIChatClient()

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