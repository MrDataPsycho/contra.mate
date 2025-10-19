"""Get conversation use case"""

from typing import Optional
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.conversation import Conversation
from contramate.domain.entities.message import Message


class GetConversationUseCase:
    """
    Use case for retrieving a conversation with its messages.

    Handles fetching conversation data and converting to domain entities.
    """

    def __init__(self, conversation_repository: AbstractConversationRepository):
        """
        Initialize use case.

        Args:
            conversation_repository: Repository for conversation persistence
        """
        self.conversation_repository = conversation_repository

    async def execute(
        self, user_id: str, conversation_id: str, message_limit: int = 50
    ) -> Conversation:
        """
        Get a conversation with its messages.

        Args:
            user_id: ID of the user
            conversation_id: ID of the conversation to retrieve
            message_limit: Maximum number of messages to retrieve

        Returns:
            Conversation entity with messages

        Raises:
            ValueError: If conversation doesn't exist
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not conversation_id or not conversation_id.strip():
            raise ValueError("conversation_id cannot be empty")

        logger.info(f"Retrieving conversation {conversation_id} for user {user_id}")

        # Get conversation metadata
        conversation_data = await self.conversation_repository.get_conversation_by_id(
            user_id=user_id, conversation_id=conversation_id
        )

        if not conversation_data:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {user_id}"
            )

        # Get messages
        messages_data = await self.conversation_repository.get_messages(
            user_id=user_id, conversation_id=conversation_id, limit=message_limit
        )

        # Convert messages to domain entities
        messages = [Message.from_dynamodb_item(msg_data) for msg_data in messages_data]

        # Convert conversation to domain entity
        conversation = Conversation.from_dynamodb_item(
            conversation_data, messages=messages
        )

        logger.info(
            f"Retrieved conversation {conversation_id} with {len(messages)} messages"
        )

        return conversation
