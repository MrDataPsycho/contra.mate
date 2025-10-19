"""Conversation status value object"""

from enum import StrEnum


class ConversationStatus(StrEnum):
    """Enumeration for conversation status"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

    def is_accessible(self) -> bool:
        """Check if conversation can be accessed"""
        return self in (ConversationStatus.ACTIVE, ConversationStatus.ARCHIVED)

    def is_modifiable(self) -> bool:
        """Check if conversation can be modified"""
        return self == ConversationStatus.ACTIVE
