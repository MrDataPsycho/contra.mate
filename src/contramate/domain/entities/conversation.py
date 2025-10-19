"""Conversation domain entity"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from contramate.domain.value_objects.conversation_status import ConversationStatus
from contramate.domain.entities.message import Message


class Conversation(BaseModel):
    """
    Conversation entity representing a chat session.

    Encapsulates conversation metadata and business rules.
    """

    conversation_id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    status: ConversationStatus = ConversationStatus.ACTIVE
    filter_values: Optional[Dict[str, Any]] = None
    messages: List[Message] = []

    class Config:
        use_enum_values = True

    def add_message(self, message: Message) -> None:
        """
        Add a message to the conversation.

        Args:
            message: Message entity to add
        """
        if not self.can_modify():
            raise ValueError(f"Cannot modify conversation in {self.status} status")

        if message.conversation_id != self.conversation_id:
            raise ValueError("Message conversation_id does not match")

        self.messages.append(message)

    def get_message_count(self) -> int:
        """Get total number of messages"""
        return len(self.messages)

    def get_messages_for_llm(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get messages in OpenAI-compatible format for LLM.

        Args:
            limit: Optional limit on number of messages to return

        Returns:
            List of messages in OpenAI format
        """
        messages = self.messages[-limit:] if limit else self.messages
        return [msg.to_openai_format() for msg in messages]

    def can_modify(self) -> bool:
        """Check if conversation can be modified"""
        return self.status.is_modifiable()

    def can_access(self) -> bool:
        """Check if conversation can be accessed"""
        return self.status.is_accessible()

    def archive(self) -> None:
        """Archive the conversation"""
        self.status = ConversationStatus.ARCHIVED

    def activate(self) -> None:
        """Activate the conversation"""
        self.status = ConversationStatus.ACTIVE

    def update_title(self, new_title: str) -> None:
        """
        Update conversation title.

        Args:
            new_title: New title for conversation
        """
        if not new_title.strip():
            raise ValueError("Title cannot be empty")
        self.title = new_title.strip()

    def update_filters(self, filter_values: Dict[str, Any]) -> None:
        """
        Update conversation filter values.

        Args:
            filter_values: New filter values
        """
        if not self.can_modify():
            raise ValueError(f"Cannot modify conversation in {self.status} status")
        self.filter_values = filter_values

    @classmethod
    def from_dynamodb_item(
        cls, item: Dict[str, Any], messages: Optional[List[Message]] = None
    ) -> "Conversation":
        """
        Create Conversation entity from DynamoDB item.

        Args:
            item: DynamoDB conversation item
            messages: Optional list of Message entities

        Returns:
            Conversation entity instance
        """
        # Extract conversation_id from sort key (CONV#conversation_id)
        conversation_id = item["sk"].split("#")[1]

        # Determine status from is_active field if present
        is_active = item.get("is_active", True)
        status = ConversationStatus.ACTIVE if is_active else ConversationStatus.ARCHIVED

        return cls(
            conversation_id=conversation_id,
            user_id=item["userId"],
            title=item.get("title", ""),
            created_at=datetime.fromisoformat(item["createdAt"]),
            updated_at=datetime.fromisoformat(item["updatedAt"]),
            status=status,
            filter_values=item.get("filter_value"),
            messages=messages or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.

        Returns:
            Dict representation of conversation
        """
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "filter_values": self.filter_values,
            "message_count": self.get_message_count(),
        }
