"""List conversations use case"""

from typing import Any, Dict, List, Optional
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.conversation import Conversation


class ListConversationsUseCase:
    """
    Use case for listing user's conversations.

    Handles fetching and pagination of conversation lists.
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
        limit: int = 20,
        last_key: Optional[Dict[str, Any]] = None,
    ) -> List[Conversation]:
        """
        List conversations for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to retrieve
            last_key: Pagination key from previous request

        Returns:
            List of Conversation entities (without messages)

        Raises:
            ValueError: If user_id is empty
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if limit <= 0:
            raise ValueError("limit must be positive")

        logger.info(f"Listing conversations for user {user_id}, limit={limit}")

        # Get conversations from repository
        conversations_data = await self.conversation_repository.get_conversations(
            user_id=user_id, limit=limit, last_evaluated_key=last_key
        )

        # Convert to domain entities (without messages)
        conversations = [
            Conversation.from_dynamodb_item(conv_data, messages=[])
            for conv_data in conversations_data
        ]

        logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")

        return conversations

    async def execute_last_90_days(
        self,
        user_id: str,
        limit: int = 100,
        last_key: Optional[Dict[str, Any]] = None,
    ) -> List[Conversation]:
        """
        List conversations from last 90 days for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to retrieve
            last_key: Pagination key from previous request

        Returns:
            List of Conversation entities from last 90 days

        Raises:
            ValueError: If user_id is empty
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        logger.info(
            f"Listing recent conversations (90 days) for user {user_id}, limit={limit}"
        )

        # Get recent conversations
        conversations_data = (
            await self.conversation_repository.get_conversations_last_90_days(
                user_id=user_id, limit=limit, last_evaluated_key=last_key
            )
        )

        # Convert to domain entities
        conversations = [
            Conversation.from_dynamodb_item(conv_data, messages=[])
            for conv_data in conversations_data
        ]

        logger.info(
            f"Retrieved {len(conversations)} recent conversations for user {user_id}"
        )

        return conversations
