from typing import List, Dict, Any, Optional, Union
import logging
from openai import AzureOpenAI, AsyncAzureOpenAI
from openai import OpenAIError

from contramate.utils.settings.core import settings
from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.utils.clients.ai.base import BaseChatClient, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


class AzureOpenAIChatClient(BaseChatClient):
    """Azure OpenAI chat completion client with certificate-based authentication"""

    def __init__(self, azure_settings: Optional[object] = None):
        """
        Initialize Azure OpenAI chat client with certificate authentication

        Args:
            azure_settings: Azure OpenAI settings (uses global settings if not provided)
        """
        self.azure_settings = azure_settings or settings.azure_openai
        
        # Initialize base client
        super().__init__()
        
        self.default_model = self.azure_settings.model
        self.default_temperature = self.azure_settings.temperature
        self.default_max_tokens = self.azure_settings.max_tokens

        # Validate required configuration
        if not self.azure_settings.tenant_id:
            raise ValueError("Azure tenant ID is required. Set AZURE_OPENAI_TENANT_ID in environment.")
        
        if not self.azure_settings.client_id:
            raise ValueError("Azure client ID is required. Set AZURE_OPENAI_CLIENT_ID in environment.")
        
        if not self.azure_settings.azure_endpoint:
            raise ValueError("Azure endpoint is required. Set AZURE_OPENAI_AZURE_ENDPOINT in environment.")

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
            logger.error(f"Failed to initialize Azure OpenAI clients: {e}")
            raise

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        return model or self.default_model

    def _create_response(self, response: Any) -> ChatResponse:
        """Convert Azure OpenAI response to standardized format"""
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
                "system_fingerprint": getattr(response, 'system_fingerprint', None),
                "provider": "azure_openai"
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
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            ChatResponse: Standardized chat response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = self._sync_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens),
                **kwargs
            )

            return self._create_response(response)

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI chat completion: {e}")
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
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            ChatResponse: Standardized chat response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = await self._async_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens),
                **kwargs
            )

            return self._create_response(response)

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error in async chat completion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI async chat completion: {e}")
            raise

    def stream_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Streaming chat completion (returns final content)

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            str: Complete response content
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = self._sync_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens),
                stream=True,
                **kwargs
            )

            content_chunks = []
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    content_chunks.append(chunk.choices[0].delta.content)

            return "".join(content_chunks)

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error in streaming completion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI streaming completion: {e}")
            raise

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
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            List[Any]: Tool calls from the response
        """
        try:
            normalized_messages = self._normalize_messages(messages)

            response = self._sync_client.chat.completions.create(
                model=self._get_model(model),
                messages=normalized_messages,
                temperature=self._get_temperature(temperature),
                max_tokens=self._get_max_tokens(max_tokens),
                tools=tools,
                tool_choice="auto",
                **kwargs
            )

            return response.choices[0].message.tool_calls or []

        except OpenAIError as e:
            logger.error(f"Azure OpenAI API error in tool selection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Azure OpenAI tool selection: {e}")
            raise


if __name__ == "__main__":
    import asyncio

    async def test_azure_client():
        try:
            client = AzureOpenAIChatClient()

            test_messages = [
                {"role": "user", "content": "Hello, this is a test message for Azure OpenAI."}
            ]

            # Test sync
            print("Testing sync completion...")
            response = client.chat_completion(test_messages)
            print(f"Sync response: {response.content}")

            # Test async
            print("Testing async completion...")
            async_response = await client.async_chat_completion(test_messages)
            print(f"Async response: {async_response.content}")

        except Exception as e:
            print(f"Test failed: {e}")

    asyncio.run(test_azure_client())