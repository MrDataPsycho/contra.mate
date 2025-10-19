"""Manage session use case"""

from typing import Optional
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.user_session import UserSession
from contramate.domain.entities.conversation import Conversation


class ManageSessionUseCase:
    """
    Use case for managing user sessions.

    Handles user session state and active conversation tracking.
    """

    def __init__(self, conversation_repository: AbstractConversationRepository):
        """
        Initialize use case.

        Args:
            conversation_repository: Repository for conversation persistence
        """
        self.conversation_repository = conversation_repository

    async def get_user_session(
        self, user_id: str, conversation_limit: int = 20
    ) -> UserSession:
        """
        Get or create a user session with recent conversations.

        Args:
            user_id: ID of the user
            conversation_limit: Number of recent conversations to load

        Returns:
            UserSession entity with loaded conversations

        Raises:
            ValueError: If user_id is empty
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        logger.info(f"Getting session for user {user_id}")

        # Get user's conversations
        conversations_data = await self.conversation_repository.get_conversations(
            user_id=user_id, limit=conversation_limit
        )

        # Convert to domain entities
        conversations = [
            Conversation.from_dynamodb_item(conv_data, messages=[])
            for conv_data in conversations_data
        ]

        # Create session
        session = UserSession(user_id=user_id, conversations=conversations)

        # Set most recent active conversation as active (if any)
        if conversations:
            # Find first active conversation
            for conv in conversations:
                if conv.can_modify():
                    session.active_conversation_id = conv.conversation_id
                    break

        logger.info(
            f"Loaded session for user {user_id} with {len(conversations)} conversations"
        )

        return session

    async def set_active_conversation(
        self, user_id: str, conversation_id: str
    ) -> None:
        """
        Set the active conversation for a user.

        Args:
            user_id: ID of the user
            conversation_id: ID of conversation to activate

        Raises:
            ValueError: If conversation doesn't exist
        """
        logger.info(
            f"Setting active conversation {conversation_id} for user {user_id}"
        )

        # Verify conversation exists and belongs to user
        conversation_data = await self.conversation_repository.get_conversation_by_id(
            user_id=user_id, conversation_id=conversation_id
        )

        if not conversation_data:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {user_id}"
            )

        # Touch the conversation to update its timestamp
        await self.conversation_repository.touch_conversation(
            user_id=user_id, conversation_id=conversation_id
        )

        logger.info(f"Set active conversation {conversation_id} for user {user_id}")
