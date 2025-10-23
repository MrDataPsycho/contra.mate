"""
Message models for agent conversation history.

This module contains Pydantic models for handling conversation messages
in OpenAI-compatible format and converting them to Pydantic AI format.
"""

from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, UserPromptPart, TextPart


class OpenAIMessage(BaseModel):
    """OpenAI-compatible message format with Pydantic validation."""
    role: Literal["user", "assistant"] = Field(..., description="Message role: user or assistant")
    content: str = Field(..., min_length=1, description="Message content")
    timestamp: datetime | None = Field(default=None, description="Optional timestamp for the message (UTC)")


class MessageHistory(BaseModel):
    """Message history wrapper for list of OpenAIMessage."""
    messages: list[OpenAIMessage] = Field(..., description="List of OpenAI-compatible messages")

    def to_pydantic_ai_messages(self) -> list[ModelMessage]:
        """
        Convert to list of Pydantic AI ModelMessage objects.

        Returns:
            List of ModelMessage objects (ModelRequest or ModelResponse)
        """
        pydantic_messages: list[ModelMessage] = []

        for msg in self.messages:
            if msg.role == "user":
                # User messages -> ModelRequest with UserPromptPart
                # Pass timestamp if provided, otherwise Pydantic AI will auto-generate
                if msg.timestamp:
                    pydantic_messages.append(
                        ModelRequest(parts=[UserPromptPart(content=msg.content, timestamp=msg.timestamp)])
                    )
                else:
                    pydantic_messages.append(
                        ModelRequest(parts=[UserPromptPart(content=msg.content)])
                    )
            elif msg.role == "assistant":
                # Assistant messages -> ModelResponse with TextPart
                # Note: ModelResponse doesn't take timestamp in constructor, it's set automatically
                pydantic_messages.append(
                    ModelResponse(parts=[TextPart(content=msg.content)])
                )

        return pydantic_messages
