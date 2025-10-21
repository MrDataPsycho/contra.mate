from typing import List, Dict, Any, Optional, Union, Callable
from loguru import logger
from openai import AzureOpenAI, AsyncAzureOpenAI
from openai import OpenAIError

from contramate.utils.auth.certificate_provider import get_cert_token_provider
from contramate.utils.settings.core import AOAICertSettings
from contramate.llm.base import BaseChatClient, ChatMessage


class AzureOpenAIChatClient(BaseChatClient):
    """
    Azure OpenAI chat completion client with multiple authentication methods.

    Supports authentication in priority order:
    1. AOAICertSettings object (certificate-based)
    2. Azure AD token provider
    3. API key
    """

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2023-05-15",
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        azure_ad_token_provider: Optional[Callable] = None,
        azure_ad_cert_settings: Optional[AOAICertSettings] = None
    ):
        """
        Initialize Azure OpenAI chat client with flexible authentication.

        Args:
            azure_endpoint: Azure OpenAI endpoint URL (required unless azure_ad_cert_settings provided)
            api_version: Azure OpenAI API version (default: "2023-05-15")
            model: Default model for completions (uses azure_ad_cert_settings.model if provided)
            temperature: Default temperature (uses azure_ad_cert_settings.temperature if provided)
            max_tokens: Default max tokens (uses azure_ad_cert_settings.max_tokens if provided)
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
            logger.info("Initializing with AOAICertSettings (certificate-based auth)")
            self.azure_endpoint = azure_ad_cert_settings.azure_endpoint
            self.api_version = azure_ad_cert_settings.api_version
            self.default_model = model or azure_ad_cert_settings.model
            self.default_temperature = temperature if temperature is not None else azure_ad_cert_settings.temperature
            self.default_max_tokens = max_tokens if max_tokens is not None else azure_ad_cert_settings.max_tokens

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
            logger.info("Initializing with provided Azure AD token provider")
            if not azure_endpoint:
                raise ValueError("azure_endpoint is required when using azure_ad_token_provider")

            self.azure_endpoint = azure_endpoint
            self.api_version = api_version
            self.default_model = model or "gpt-4"
            self.default_temperature = temperature if temperature is not None else 0.7
            self.default_max_tokens = max_tokens if max_tokens is not None else 1000

            client_config = {
                "azure_endpoint": azure_endpoint,
                "api_version": api_version,
                "azure_ad_token_provider": azure_ad_token_provider
            }

        # Priority 3: Use API key
        elif api_key:
            logger.info("Initializing with API key authentication")
            if not azure_endpoint:
                raise ValueError("azure_endpoint is required when using api_key")

            self.azure_endpoint = azure_endpoint
            self.api_version = api_version
            self.default_model = model or "gpt-4"
            self.default_temperature = temperature if temperature is not None else 0.7
            self.default_max_tokens = max_tokens if max_tokens is not None else 1000

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
            logger.info("Azure OpenAI clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI clients: {e}")
            raise

    def _get_model(self, model: Optional[str] = None) -> str:
        """Get model name, using default if not specified"""
        return model or self.default_model

    def _get_temperature(self, temperature: Optional[float] = None) -> float:
        """Get temperature, using default if not specified"""
        return temperature if temperature is not None else self.default_temperature

    def _get_max_tokens(self, max_tokens: Optional[int] = None) -> int:
        """Get max tokens, using default if not specified"""
        return max_tokens if max_tokens is not None else self.default_max_tokens

    def chat_completion(
        self,
        messages: List[Union[ChatMessage, Dict[str, str]]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Synchronous chat completion

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            Native OpenAI ChatCompletion object
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

            return response

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
    ):
        """
        Asynchronous chat completion

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            Native OpenAI ChatCompletion object
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

            return response

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
    ):
        """
        Streaming chat completion

        Args:
            messages: List of chat messages
            model: Model to use (optional)
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional parameters for Azure OpenAI API

        Returns:
            Generator yielding stream chunks
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

            return response

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
    import os

    async def test_azure_client():
        """
        Test Azure OpenAI client with different authentication methods.
        Set environment variables to test each method.
        """
        test_messages = [
            {"role": "user", "content": "Hello, this is a test message for Azure OpenAI."}
        ]

        print("=" * 60)
        print("Testing Azure OpenAI Client with Multiple Auth Methods")
        print("=" * 60)

        # Method 1: Using AOAICertSettings (highest priority)
        try:
            print("\n1. Testing with AOAICertSettings (certificate-based)...")
            from contramate.utils.settings.factory import SettingsFactory

            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIChatClient(azure_ad_cert_settings=settings)

            response = client.chat_completion(test_messages)
            print(f"✓ Certificate auth response: {response.choices[0].message.content[:100]}...")
        except Exception as e:
            print(f"✗ Certificate auth failed: {e}")

        # Method 2: Using API key
        try:
            print("\n2. Testing with API key authentication...")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

            if api_key and endpoint:
                client = AzureOpenAIChatClient(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    model="gpt-4"
                )

                response = client.chat_completion(test_messages)
                print(f"✓ API key auth response: {response.choices[0].message.content[:100]}...")
            else:
                print("✗ API key auth skipped: Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
        except Exception as e:
            print(f"✗ API key auth failed: {e}")

        # Method 3: Using custom Azure AD token provider
        try:
            print("\n3. Testing with custom Azure AD token provider...")
            print("✗ Token provider auth skipped: Requires custom implementation")
        except Exception as e:
            print(f"✗ Token provider auth failed: {e}")

        # Test async completion
        try:
            print("\n4. Testing async completion...")
            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIChatClient(azure_ad_cert_settings=settings)

            async_response = await client.async_chat_completion(test_messages)
            print(f"✓ Async response: {async_response.choices[0].message.content[:100]}...")
        except Exception as e:
            print(f"✗ Async completion failed: {e}")

        # Test streaming
        try:
            print("\n5. Testing streaming completion...")
            settings = SettingsFactory.create_azure_openai_settings()
            client = AzureOpenAIChatClient(azure_ad_cert_settings=settings)

            stream = client.stream_completion(test_messages)
            print("✓ Stream response: ", end="")
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="", flush=True)
            print()
        except Exception as e:
            print(f"✗ Streaming failed: {e}")

        print("\n" + "=" * 60)
        print("Testing complete!")
        print("=" * 60)

    asyncio.run(test_azure_client())