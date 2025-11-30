"""
PostgreSQL Conversation Store Adapter using SQLModel.

Provides synchronous CRUD operations for conversations and messages using PostgreSQL.
Implements the same interface as DynamoDB adapter for drop-in replacement.
Uses SQLModel for type-safe operations and synchronous SQLAlchemy for database access.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlmodel import select, Session, or_

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.dbs.models import FeedbackType, Conversation, Message


class PostgreSQLConversationAdapter(AbstractConversationRepository):
    """
    Service for managing conversations and messages in PostgreSQL.

    Uses SQLModel for type-safe database operations with synchronous support.
    Overcomes DynamoDB's 400KB text field limitation by using PostgreSQL TEXT type.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialize adapter with session factory.

        Args:
            session_factory: Callable that returns Session context manager
        """
        self.session_factory = session_factory

    def create_conversation(
        self,
        user_id: str,
        title: str = "",
        conversation_id: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            user_id: User identifier
            title: Conversation title
            conversation_id: Optional UUID string (generated if not provided)
            filter_values: Optional filter settings

        Returns:
            Dict representation of created conversation
        """
        with self.session_factory() as session:
            conversation = Conversation(
                id=UUID(conversation_id) if conversation_id else None,
                user_id=user_id,
                title=title,
                filter_values=filter_values or {},
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)

            logger.info(f"Created conversation {conversation.id} for user {user_id}")

            return {
                "conversation_id": str(conversation.id),
                "userId": conversation.user_id,
                "title": conversation.title,
                "filter_value": conversation.filter_values,
                "createdAt": conversation.created_at.isoformat(),
                "updatedAt": conversation.updated_at.isoformat(),
                "is_active": conversation.is_active,
            }

    def get_conversations(
        self,
        user_id: str,
        limit: int = 10,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversations for a user, ordered by updated_at descending.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            last_evaluated_key: Not used in PostgreSQL (pagination handled differently)

        Returns:
            List of conversation dictionaries
        """
        with self.session_factory() as session:
            statement = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            result = session.execute(statement)
            conversations = result.scalars().all()

            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")

            return [
                {
                    "conversation_id": str(conv.id),
                    "userId": conv.user_id,
                    "title": conv.title,
                    "filter_value": conv.filter_values,
                    "createdAt": conv.created_at.isoformat(),
                    "updatedAt": conv.updated_at.isoformat(),
                    "is_active": conv.is_active,
                }
                for conv in conversations
            ]

    def get_conversation_by_id(
        self, user_id: str, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single conversation by ID.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string

        Returns:
            Conversation dictionary or None if not found
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return None

            logger.info(f"Retrieved conversation {conversation_id}")

            return {
                "conversation_id": str(conversation.id),
                "userId": conversation.user_id,
                "title": conversation.title,
                "filter_value": conversation.filter_values,
                "createdAt": conversation.created_at.isoformat(),
                "updatedAt": conversation.updated_at.isoformat(),
                "is_active": conversation.is_active,
            }

    def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        """
        Delete a conversation (messages are cascade deleted).

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if conversation:
                session.delete(conversation)
                session.commit()
                logger.info(f"Deleted conversation {conversation_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for deletion")

    def create_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        feedback: str = "",
        message_id: Optional[str] = None,
        filter_value: Optional[Dict[str, Any]] = None,
        is_user_filter_text: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new message in a conversation.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
            role: Message role ("user" or "assistant")
            content: Message content (no size limit with TEXT field)
            feedback: Optional feedback
            message_id: Optional UUID string (generated if not provided)
            filter_value: Optional filter settings
            is_user_filter_text: Whether this is a filter update message
            metadata: Optional metadata dict (e.g., response_time)

        Returns:
            Dict representation of created message
        """
        with self.session_factory() as session:
            message = Message(
                id=UUID(message_id) if message_id else None,
                conversation_id=UUID(conversation_id),
                user_id=user_id,
                role=role,
                content=content,
                feedback=feedback,
                filter_values=filter_value,
                is_user_filter_text=is_user_filter_text,
                msg_metadata=metadata or {},
            )
            session.add(message)

            # Touch the conversation to update its updated_at timestamp
            self.touch_conversation(user_id, conversation_id)

            session.commit()
            session.refresh(message)

            logger.info(f"Created message {message.id} in conversation {conversation_id}")

            return {
                "messageId": str(message.id),
                "conversationId": str(message.conversation_id),
                "userId": message.user_id,
                "role": message.role,
                "content": message.content,
                "feedback": message.feedback,
                "filter_value": message.filter_values,
                "is_user_filter_text": message.is_user_filter_text,
                "metadata": message.msg_metadata,
                "createdAt": message.created_at.isoformat(),
                "updatedAt": message.updated_at.isoformat(),
            }

    def get_messages(
        self, user_id: str, conversation_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation, ordered by created_at ascending.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        with self.session_factory() as session:
            statement = (
                select(Message)
                .where(
                    Message.conversation_id == UUID(conversation_id),
                    Message.user_id == user_id
                )
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            result = session.execute(statement)
            messages = result.scalars().all()

            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")

            return [
                {
                    "messageId": str(msg.id),
                    "conversationId": str(msg.conversation_id),
                    "userId": msg.user_id,
                    "role": msg.role,
                    "content": msg.content,
                    "feedback": msg.feedback,
                    "filter_value": msg.filter_values,
                    "is_user_filter_text": msg.is_user_filter_text,
                    "metadata": msg.msg_metadata,
                    "createdAt": msg.created_at.isoformat(),
                    "updatedAt": msg.updated_at.isoformat(),
                }
                for msg in messages
            ]

    def delete_conversation_and_messages(
        self, user_id: str, conversation_id: str
    ) -> bool:
        """
        Delete a conversation and all its messages.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string

        Returns:
            True if deletion was successful
        """
        self.delete_conversation(user_id, conversation_id)
        logger.info(f"Deleted conversation and messages for {conversation_id}")
        return True

    def get_conversations_last_90_days(
        self,
        user_id: str,
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get conversations from the last 90 days, ordered by updated_at descending.

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            last_evaluated_key: Not used in PostgreSQL

        Returns:
            List of conversation dictionaries
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)

        with self.session_factory() as session:
            statement = (
                select(Conversation)
                .where(
                    Conversation.user_id == user_id,
                    Conversation.updated_at >= cutoff_date
                )
                .order_by(Conversation.updated_at.desc())
                .limit(limit)
            )
            result = session.execute(statement)
            conversations = result.scalars().all()

            logger.info(f"Retrieved {len(conversations)} conversations from last 90 days for user {user_id}")

            return [
                {
                    "conversation_id": str(conv.id),
                    "userId": conv.user_id,
                    "title": conv.title,
                    "filter_value": conv.filter_values,
                    "createdAt": conv.created_at.isoformat(),
                    "updatedAt": conv.updated_at.isoformat(),
                    "is_active": conv.is_active,
                }
                for conv in conversations
            ]

    def update_message_feedback(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        feedback: FeedbackType,
    ) -> Optional[Dict[str, Any]]:
        """
        Update message feedback.

        Args:
            message_id: Message UUID string
            conversation_id: Conversation UUID string
            user_id: User identifier
            feedback: Feedback type enum

        Returns:
            Updated message dictionary or None if not found
        """
        with self.session_factory() as session:
            statement = select(Message).where(
                Message.id == UUID(message_id),
                Message.conversation_id == UUID(conversation_id),
                Message.user_id == user_id
            )
            result = session.execute(statement)
            message = result.scalar_one_or_none()

            if not message:
                logger.warning(f"Message {message_id} not found for feedback update")
                return None

            message.feedback = feedback.value
            message.updated_at = datetime.now(timezone.utc)

            self.touch_conversation(user_id, conversation_id)
            session.commit()
            session.refresh(message)

            logger.info(f"Updated feedback for message {message_id}")

            return {
                "messageId": str(message.id),
                "conversationId": str(message.conversation_id),
                "userId": message.user_id,
                "role": message.role,
                "content": message.content,
                "feedback": message.feedback,
                "updatedAt": message.updated_at.isoformat(),
            }

    def update_conversation_title(
        self, user_id: str, conversation_id: str, title: str
    ) -> bool:
        """
        Update conversation title.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
            title: New title

        Returns:
            True if update was successful
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for title update")
                return False

            conversation.title = title
            conversation.updated_at = datetime.now(timezone.utc)

            session.commit()
            logger.info(f"Updated title for conversation {conversation_id}")
            return True

    def update_conversation_filters(
        self,
        user_id: str,
        conversation_id: str,
        filter_values: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update conversation filter values.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
            filter_values: New filter settings

        Returns:
            True if update was successful
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for filter update")
                return False

            conversation.filter_values = filter_values or {}
            conversation.updated_at = datetime.now(timezone.utc)

            session.commit()
            logger.info(f"Updated filters for conversation {conversation_id}")
            return True

    def touch_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Update conversation's updated_at timestamp without changing other fields.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string

        Returns:
            True if update was successful
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for touch")
                return False

            conversation.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.debug(f"Touched conversation {conversation_id}")
            return True

    def update_conversation_status(
        self,
        user_id: str,
        conversation_id: str,
        is_active: bool,
    ) -> None:
        """
        Update conversation active status.

        Args:
            user_id: User identifier
            conversation_id: Conversation UUID string
            is_active: New active status
        """
        with self.session_factory() as session:
            statement = select(Conversation).where(
                Conversation.id == UUID(conversation_id),
                Conversation.user_id == user_id
            )
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for status update")
                return

            conversation.is_active = is_active
            conversation.updated_at = datetime.now(timezone.utc)

            session.commit()
            logger.info(f"Updated status for conversation {conversation_id} to {is_active}")

    # Helper methods matching the DynamoDB adapter interface

    def list_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Alias for get_conversations"""
        return self.get_conversations(user_id, limit)

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID without user_id check (for internal use)"""
        with self.session_factory() as session:
            statement = select(Conversation).where(Conversation.id == UUID(conversation_id))
            result = session.execute(statement)
            conversation = result.scalar_one_or_none()

            if not conversation:
                return None

            return {
                "conversation_id": str(conversation.id),
                "userId": conversation.user_id,
                "title": conversation.title,
                "filter_value": conversation.filter_values,
                "createdAt": conversation.created_at.isoformat(),
                "updatedAt": conversation.updated_at.isoformat(),
                "is_active": conversation.is_active,
            }

    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get message history for a conversation"""
        with self.session_factory() as session:
            statement = (
                select(Message)
                .where(Message.conversation_id == UUID(conversation_id))
                .order_by(Message.created_at.asc())
                .limit(limit)
            )
            result = session.execute(statement)
            messages = result.scalars().all()

            return [
                {
                    "messageId": str(msg.id),
                    "conversationId": str(msg.conversation_id),
                    "userId": msg.user_id,
                    "role": msg.role,
                    "content": msg.content,
                    "feedback": msg.feedback,
                    "createdAt": msg.created_at.isoformat(),
                    "updatedAt": msg.updated_at.isoformat(),
                }
                for msg in messages
            ]

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Simplified message creation"""
        return self.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata=metadata
        )
