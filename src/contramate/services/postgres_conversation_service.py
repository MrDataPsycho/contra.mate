"""PostgreSQL-based conversation service with Result types for error handling."""

from typing import Dict, Any, List, Optional
from loguru import logger

from neopipe import Ok, Err, Result

from contramate.dbs.adapters.postgres_conversation_adapter import PostgreSQLConversationAdapter
from contramate.dbs.postgres_db import init_db
from contramate.utils.settings.core import PostgresSettings


class PostgresConversationService:
    """High-level service for conversation management using PostgreSQL with Result-based error handling"""

    def __init__(self, adapter: PostgreSQLConversationAdapter):
        self.adapter = adapter

    @staticmethod
    def create_default() -> "PostgresConversationService":
        """Factory method to create service with default settings"""
        settings = PostgresSettings()
        db = init_db(settings)
        adapter = PostgreSQLConversationAdapter(db.session_factory)
        return PostgresConversationService(adapter)

    def _normalize_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize PostgreSQL conversation to API response format"""
        return {
            "conversation_id": str(conversation.get("conversation_id", "")),
            "user_id": conversation.get("userId", ""),
            "title": conversation.get("title", ""),
            "filter_values": conversation.get("filter_value", {}),
            "created_at": conversation.get("createdAt", ""),
            "updated_at": conversation.get("updatedAt", "")
        }

    def _normalize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize PostgreSQL message to API response format"""
        # Handle response_time from metadata if present
        response_time = None
        metadata = message.get("metadata", {})
        if metadata and "response_time" in metadata:
            response_time_str = metadata["response_time"]
            try:
                response_time = float(response_time_str) if isinstance(response_time_str, str) else response_time_str
            except (ValueError, TypeError):
                response_time = None

        return {
            "message_id": str(message.get("messageId", "")),
            "conversation_id": str(message.get("conversationId", "")),
            "role": message.get("role", ""),
            "content": message.get("content", ""),
            "filter_value": message.get("filter_value"),
            "created_at": message.get("createdAt", ""),
            "updated_at": message.get("updatedAt", ""),
            "feedback": message.get("feedback", ""),
            "response_time": response_time
        }

    async def create_conversation(
        self,
        user_id: str,
        title: str = "New Conversation",
        filter_values: Optional[Dict[str, Any]] = None
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Create a new conversation"""
        try:
            logger.info(f"Creating conversation for user: {user_id}")
            
            conversation = self.adapter.create_conversation(
                user_id=user_id,
                title=title,
                filter_values=filter_values
            )
            
            normalized = self._normalize_conversation(conversation)
            logger.debug(f"Successfully created conversation: {normalized['conversation_id']}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to create conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "conversation_creation_failed",
                "message": error_msg
            })

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> Result[List[Dict[str, Any]], Dict[str, Any]]:
        """Get all conversations for a user"""
        try:
            logger.info(f"Fetching conversations for user: {user_id}")
            
            conversations = self.adapter.get_conversations(user_id, limit=limit)
            normalized = [self._normalize_conversation(conv) for conv in conversations]
            
            logger.debug(f"Retrieved {len(normalized)} conversations for user {user_id}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to fetch conversations: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "fetch_conversations_failed",
                "message": error_msg
            })

    async def get_conversation_by_id(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Get a specific conversation by ID"""
        try:
            logger.info(f"Fetching conversation: {conversation_id}")
            
            conversation = self.adapter.get_conversation_by_id(user_id, conversation_id)
            
            if not conversation:
                error_msg = f"Conversation {conversation_id} not found"
                logger.warning(error_msg)
                return Err({
                    "error": "conversation_not_found",
                    "message": error_msg
                })
            
            normalized = self._normalize_conversation(conversation)
            logger.debug(f"Retrieved conversation: {conversation_id}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to fetch conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "fetch_conversation_failed",
                "message": error_msg
            })

    async def update_conversation_filters(
        self,
        user_id: str,
        conversation_id: str,
        filter_values: Dict[str, Any]
    ) -> Result[bool, Dict[str, Any]]:
        """Update conversation filter values"""
        try:
            logger.info(f"Updating filters for conversation: {conversation_id}")
            
            success = self.adapter.update_conversation_filters(
                user_id=user_id,
                conversation_id=conversation_id,
                filter_values=filter_values
            )
            
            if not success:
                error_msg = f"Failed to update filters for conversation {conversation_id}"
                logger.warning(error_msg)
                return Err({
                    "error": "update_failed",
                    "message": error_msg
                })
            
            logger.debug(f"Successfully updated filters for conversation {conversation_id}")
            return Ok(True)
            
        except Exception as e:
            error_msg = f"Failed to update conversation filters: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "update_filters_failed",
                "message": error_msg
            })

    async def get_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> Result[List[Dict[str, Any]], Dict[str, Any]]:
        """Get messages for a conversation"""
        try:
            logger.info(f"Fetching messages for conversation: {conversation_id}")
            
            messages = self.adapter.get_messages(user_id, conversation_id, limit=limit)
            normalized = [self._normalize_message(msg) for msg in messages]
            
            logger.debug(f"Retrieved {len(normalized)} messages for conversation {conversation_id}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to fetch messages: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "fetch_messages_failed",
                "message": error_msg
            })

    async def add_user_message(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        context_filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Add a user message to the conversation"""
        try:
            logger.info(f"Adding user message to conversation: {conversation_id}")
            
            message = self.adapter.create_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="user",
                content=content,
                filter_value=context_filters,
                metadata=metadata
            )
            
            normalized = self._normalize_message(message)
            logger.debug(f"Successfully added user message: {normalized['message_id']}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to add user message: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "add_message_failed",
                "message": error_msg
            })

    async def add_assistant_response(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        context_used: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Add an assistant response to the conversation"""
        try:
            logger.info(f"Adding assistant response to conversation: {conversation_id}")
            
            message = self.adapter.create_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                filter_value=context_used,
                metadata=metadata
            )
            
            normalized = self._normalize_message(message)
            logger.debug(f"Successfully added assistant message: {normalized['message_id']}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to add assistant response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "add_response_failed",
                "message": error_msg
            })

    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[bool, Dict[str, Any]]:
        """Delete a conversation and all its messages"""
        try:
            logger.info(f"Deleting conversation: {conversation_id}")
            
            self.adapter.delete_conversation(user_id, conversation_id)
            
            logger.debug(f"Successfully deleted conversation {conversation_id}")
            return Ok(True)
            
        except Exception as e:
            error_msg = f"Failed to delete conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "delete_failed",
                "message": error_msg
            })

    async def update_message_feedback(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        feedback: str
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Update message feedback"""
        try:
            logger.info(f"Updating feedback for message: {message_id}")
            
            from contramate.dbs.models import FeedbackType
            
            feedback_enum = FeedbackType(feedback) if feedback else FeedbackType.NEUTRAL
            
            message = self.adapter.update_message_feedback(
                message_id=message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                feedback=feedback_enum
            )
            
            if not message:
                error_msg = f"Message {message_id} not found"
                logger.warning(error_msg)
                return Err({
                    "error": "message_not_found",
                    "message": error_msg
                })
            
            normalized = self._normalize_message(message)
            logger.debug(f"Successfully updated feedback for message {message_id}")
            return Ok(normalized)
            
        except Exception as e:
            error_msg = f"Failed to update message feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "update_feedback_failed",
                "message": error_msg
            })

    async def rename_conversation(
        self,
        user_id: str,
        conversation_id: str,
        title: str
    ) -> Result[bool, Dict[str, Any]]:
        """Rename a conversation"""
        try:
            logger.info(f"Renaming conversation: {conversation_id}")
            
            success = self.adapter.update_conversation_title(
                user_id=user_id,
                conversation_id=conversation_id,
                title=title
            )
            
            if not success:
                error_msg = f"Failed to rename conversation {conversation_id}"
                logger.warning(error_msg)
                return Err({
                    "error": "rename_failed",
                    "message": error_msg
                })
            
            logger.debug(f"Successfully renamed conversation {conversation_id}")
            return Ok(True)
            
        except Exception as e:
            error_msg = f"Failed to rename conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "rename_failed",
                "message": error_msg
            })

    async def archive_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[None, Dict[str, Any]]:
        """Archive (deactivate) a conversation"""
        try:
            logger.info(f"Archiving conversation: {conversation_id}")
            
            self.adapter.update_conversation_status(
                user_id=user_id,
                conversation_id=conversation_id,
                is_active=False
            )
            
            logger.debug(f"Successfully archived conversation {conversation_id}")
            return Ok(None)
            
        except Exception as e:
            error_msg = f"Failed to archive conversation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err({
                "error": "archive_failed",
                "message": error_msg
            })
