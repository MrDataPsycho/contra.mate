"""Message domain entity"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from contramate.domain.value_objects.message_role import MessageRole


class Message(BaseModel):
    """
    Message entity representing a single message in a conversation.

    Supports OpenAI-compatible message format with tool calling support.
    """

    message_id: str
    conversation_id: str
    user_id: str
    role: MessageRole
    content: str
    created_at: datetime
    updated_at: datetime

    # Optional fields for advanced features
    feedback: Optional[str] = None
    tool_calls: Optional[list[Dict[str, Any]]] = None  # OpenAI tool calls format
    tool_call_id: Optional[str] = None  # For tool response messages
    filter_value: Optional[Dict[str, Any]] = None  # Context filters used
    is_user_filter_text: bool = False

    class Config:
        use_enum_values = True

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert to OpenAI chat completion message format.

        Returns:
            Dict compatible with OpenAI chat completion API
        """
        message = {
            "role": self.role.value,
            "content": self.content,
        }

        if self.tool_calls:
            message["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            message["tool_call_id"] = self.tool_call_id

        return message

    def is_ai_message(self) -> bool:
        """Check if message is from AI"""
        return self.role.is_ai_generated()

    def is_user_message(self) -> bool:
        """Check if message is from user"""
        return self.role.is_user_generated()

    def has_tool_calls(self) -> bool:
        """Check if message contains tool calls"""
        return bool(self.tool_calls)

    def validate_content(self) -> bool:
        """Validate message content is not empty"""
        return bool(self.content.strip())

    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> "Message":
        """
        Create Message entity from DynamoDB item.

        Args:
            item: DynamoDB item dict

        Returns:
            Message entity instance
        """
        # Extract message_id from sort key (MSG#conversation_id#message_id)
        message_id = item["sk"].split("#")[2]

        return cls(
            message_id=message_id,
            conversation_id=item["conversationId"],
            user_id=item["userId"],
            role=MessageRole(item["role"]),
            content=item["content"],
            created_at=datetime.fromisoformat(item["createdAt"]),
            updated_at=datetime.fromisoformat(item["updatedAt"]),
            feedback=item.get("feedback"),
            tool_calls=item.get("tool_calls"),
            tool_call_id=item.get("tool_call_id"),
            filter_value=item.get("filter_value"),
            is_user_filter_text=item.get("is_user_filter_text", False),
        )

    def to_dynamodb_format(self) -> Dict[str, Any]:
        """
        Convert to format suitable for DynamoDB storage.

        Returns:
            Dict for DynamoDB adapter
        """
        return {
            "role": self.role.value,
            "content": self.content,
            "feedback": self.feedback or "",
            "filter_value": self.filter_value,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "is_user_filter_text": self.is_user_filter_text,
        }
