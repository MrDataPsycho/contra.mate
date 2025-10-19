"""Message role value object"""

from enum import StrEnum


class MessageRole(StrEnum):
    """Enumeration for message roles in conversation"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

    def is_ai_generated(self) -> bool:
        """Check if message is AI generated"""
        return self in (MessageRole.ASSISTANT, MessageRole.TOOL)

    def is_user_generated(self) -> bool:
        """Check if message is user generated"""
        return self == MessageRole.USER
