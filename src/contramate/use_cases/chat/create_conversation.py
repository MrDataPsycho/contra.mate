"""Create conversation use case"""

from typing import Any, Dict, Optional
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.conversation import Conversation


class CreateConversationUseCase:
    """
    Use case for creating a new conversation.

    Handles the business logic for starting a new chat session.
    """

    def __init__(self, conversation_repository: AbstractConversationRepository):
        """
        Initialize use case.

        Args:
            conversation_repository: Repository for conversation persistence
        """
        self.conversation_repository = conversation_repository

    async def execute(
        self,
        user_id: str,
        title: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None,
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            user_id: ID of the user creating the conversation
            title: Optional title for the conversation
            filter_values: Optional filter values for contract searching

        Returns:
            Created Conversation entity

        Raises:
            ValueError: If user_id is empty
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        logger.info(f"Creating new conversation for user {user_id}")

        # Create conversation via repository
        conversation_data = await self.conversation_repository.create_conversation(
            user_id=user_id.strip(),
            title=title or "New Conversation",
            filter_values=filter_values,
        )

        # Convert to domain entity
        conversation = Conversation.from_dynamodb_item(conversation_data)

        logger.info(
            f"Created conversation {conversation.conversation_id} for user {user_id}"
        )

        return conversation
