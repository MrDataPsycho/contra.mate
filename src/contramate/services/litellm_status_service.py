from typing import Dict, Any
import logging
from litellm import AuthenticationError, RateLimitError, APIConnectionError, APIError

from contramate.utils.settings.core import settings
from contramate.utils.clients.ai import LiteLLMChatClient, ChatMessage

logger = logging.getLogger(__name__)

class LiteLLMStatusService:
    """Service for LiteLLM API connection status checks"""

    def __init__(self, client: LiteLLMChatClient = None):
        self.config = settings.openai
        self.client = client or LiteLLMChatClient()

    async def check_status(self) -> Dict[str, Any]:
        """Check LiteLLM API connection status with a test message"""
        try:
            # Test with a simple completion using wrapper client
            test_message = "Hello, this is a test message to check LiteLLM connectivity."

            messages = [
                ChatMessage(role="user", content=test_message)
            ]

            response = await self.client.async_chat_completion(
                messages=messages,
                max_tokens=50,
                temperature=0.1
            )

            return {
                "connected": True,
                "status": "healthy",
                "model": response.model,
                "provider": response.metadata.get("provider", "unknown") if response.metadata else "unknown",
                "test_message": test_message,
                "response": response.content,
                "usage": response.usage,
                "response_id": response.response_id,
                "finish_reason": response.finish_reason,
                "metadata": response.metadata,
                "message": "LiteLLM API connection successful"
            }

        except AuthenticationError as e:
            logger.error(f"LiteLLM authentication failed: {e}")
            return {
                "connected": False,
                "status": "authentication_error",
                "model": self.config.model,
                "provider": "openai",
                "error": str(e),
                "message": "LiteLLM authentication failed - check API key"
            }
        except RateLimitError as e:
            logger.error(f"LiteLLM rate limit exceeded: {e}")
            return {
                "connected": False,
                "status": "rate_limit_error",
                "model": self.config.model,
                "provider": "openai",
                "error": str(e),
                "message": "LiteLLM rate limit exceeded"
            }
        except APIConnectionError as e:
            logger.error(f"LiteLLM API connection failed: {e}")
            return {
                "connected": False,
                "status": "connection_error",
                "model": self.config.model,
                "provider": "openai",
                "error": str(e),
                "message": "LiteLLM API connection failed"
            }
        except APIError as e:
            logger.error(f"LiteLLM API error: {e}")
            return {
                "connected": False,
                "status": "api_error",
                "model": self.config.model,
                "provider": "openai",
                "error": str(e),
                "message": "LiteLLM API error occurred"
            }
        except Exception as e:
            logger.error(f"Unexpected error checking LiteLLM status: {e}")
            return {
                "connected": False,
                "status": "error",
                "model": self.config.model,
                "provider": "openai",
                "error": str(e),
                "message": "Unexpected error occurred"
            }


if __name__ == "__main__":
    import asyncio
    service = LiteLLMStatusService()
    status = asyncio.run(service.check_status())
    print(status)