"""Send message use case"""

from typing import Any, Dict, Optional
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.message import Message
from contramate.domain.value_objects.message_role import MessageRole


class SendMessageUseCase:
    """
    Use case for sending a user message to a conversation.

    Handles validation and persistence of user messages.
    """

    def __init__(self, conversation_repository: AbstractConversationRepository):
        """
        Initialize use case.

        Args:
            conversation_repository: Repository for conversation/message persistence
        """
        self.conversation_repository = conversation_repository

    async def execute(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        context_filters: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Send a user message to a conversation.

        Args:
            user_id: ID of the user sending the message
            conversation_id: ID of the conversation
            content: Message content
            context_filters: Optional context filters for this message

        Returns:
            Created Message entity

        Raises:
            ValueError: If inputs are invalid or conversation doesn't exist
        """
        # Validate inputs
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not conversation_id or not conversation_id.strip():
            raise ValueError("conversation_id cannot be empty")

        if not content or not content.strip():
            raise ValueError("message content cannot be empty")

        # Verify conversation exists
        conversation_data = await self.conversation_repository.get_conversation_by_id(
            user_id=user_id, conversation_id=conversation_id
        )

        if not conversation_data:
            raise ValueError(
                f"Conversation {conversation_id} not found for user {user_id}"
            )

        logger.info(f"Sending user message to conversation {conversation_id}")

        # Create message via repository
        message_data = await self.conversation_repository.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=MessageRole.USER.value,
            content=content.strip(),
            filter_value=context_filters,
            is_user_filter_text=bool(context_filters),
        )

        # Convert to domain entity
        message = Message.from_dynamodb_item(message_data)

        logger.info(
            f"Created user message {message.message_id} in conversation {conversation_id}"
        )

        return message
