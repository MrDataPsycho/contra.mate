from typing import Dict, Any
import logging
from openai import OpenAIError, AuthenticationError, RateLimitError, APIConnectionError
from neopipe import Result, Ok, Err

from contramate.llm import OpenAIChatClient, ChatMessage

logger = logging.getLogger(__name__)

class OpenAIStatusService:
    """Service for OpenAI API connection status checks"""

    def __init__(self, client: OpenAIChatClient = None):
        self.client = client or OpenAIChatClient()

    async def check_status(self) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Check OpenAI API connection status with a test message

        Returns:
            Result[Ok, Err]: Ok with status data if successful, Err with error details if failed
        """
        try:
            # Test with a simple completion using wrapper client
            test_message = "Hello, this is a test message to check OpenAI connectivity."

            messages = [
                ChatMessage(role="user", content=test_message)
            ]

            response = await self.client.async_chat_completion(
                messages=messages,
                max_tokens=50,
                temperature=0.1
            )

            return Ok({
                "connected": True,
                "status": "healthy",
                "model": response.model,
                "test_message": test_message,
                "response": response.content,
                "usage": response.usage,
                "response_id": response.response_id,
                "finish_reason": response.finish_reason,
                "metadata": response.metadata,
                "message": "OpenAI API connection successful"
            })

        except AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            return Err({
                "connected": False,
                "status": "authentication_error",
                "error": str(e),
                "message": "OpenAI API authentication failed - check API key"
            })
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return Err({
                "connected": False,
                "status": "rate_limit_error",
                "error": str(e),
                "message": "OpenAI API rate limit exceeded"
            })
        except APIConnectionError as e:
            logger.error(f"OpenAI API connection failed: {e}")
            return Err({
                "connected": False,
                "status": "connection_error",
                "error": str(e),
                "message": "OpenAI API connection failed"
            })
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return Err({
                "connected": False,
                "status": "api_error",
                "error": str(e),
                "message": "OpenAI API error occurred"
            })
        except Exception as e:
            logger.error(f"Unexpected error checking OpenAI status: {e}")
            return Err({
                "connected": False,
                "status": "error",
                "error": str(e),
                "message": "Unexpected error occurred"
            })

if __name__ == "__main__":
    import asyncio
    service = OpenAIStatusService()
    status = asyncio.run(service.check_status())
    print(status)