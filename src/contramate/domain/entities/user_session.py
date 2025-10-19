"""User session domain entity"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from contramate.domain.entities.conversation import Conversation


class UserSession(BaseModel):
    """
    User session entity for managing user's chat sessions.

    Provides high-level view of user's conversations and activity.
    """

    user_id: str
    active_conversation_id: Optional[str] = None
    conversations: List[Conversation] = []
    last_activity: Optional[datetime] = None

    def get_active_conversation(self) -> Optional[Conversation]:
        """
        Get the currently active conversation.

        Returns:
            Active conversation or None
        """
        if not self.active_conversation_id:
            return None

        for conv in self.conversations:
            if conv.conversation_id == self.active_conversation_id:
                return conv

        return None

    def set_active_conversation(self, conversation_id: str) -> None:
        """
        Set the active conversation.

        Args:
            conversation_id: ID of conversation to activate
        """
        # Verify conversation exists
        conv_exists = any(
            c.conversation_id == conversation_id for c in self.conversations
        )

        if not conv_exists:
            raise ValueError(f"Conversation {conversation_id} not found in session")

        self.active_conversation_id = conversation_id
        self.last_activity = datetime.utcnow()

    def add_conversation(self, conversation: Conversation) -> None:
        """
        Add a conversation to the session.

        Args:
            conversation: Conversation entity to add
        """
        if conversation.user_id != self.user_id:
            raise ValueError("Conversation user_id does not match session user_id")

        self.conversations.append(conversation)
        self.last_activity = datetime.utcnow()

    def get_conversation_count(self) -> int:
        """Get total number of conversations"""
        return len(self.conversations)

    def get_active_conversations(self) -> List[Conversation]:
        """Get all active (non-archived) conversations"""
        return [c for c in self.conversations if c.can_modify()]

    def get_archived_conversations(self) -> List[Conversation]:
        """Get all archived conversations"""
        return [c for c in self.conversations if not c.can_modify() and c.can_access()]

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
