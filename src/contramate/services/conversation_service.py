"""
Conversation Service

Business logic layer for conversation management using DynamoDB adapter.
Provides high-level operations and validation for conversation workflows.
All methods return Result types for consistent error handling.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from loguru import logger
from neopipe import Ok, Err, Result

from contramate.dbs.adapters import DynamoDBConversationAdapter
from contramate.dbs.models import FeedbackType
from contramate.utils.settings.core import DynamoDBSettings


class ConversationService:
    """High-level service for conversation management with Result-based error handling"""

    def __init__(self, table_name: str, dynamodb_settings: DynamoDBSettings):
        self.adapter = DynamoDBConversationAdapter(
            table_name=table_name,
            dynamodb_settings=dynamodb_settings
        )

    def _normalize_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize DynamoDB conversation to API response format"""
        conversation_id = conversation["sk"].split("#")[1]
        return {
            "conversation_id": conversation_id,
            "user_id": conversation.get("userId", conversation.get("user_id")),
            "title": conversation.get("title", ""),
            "filter_values": conversation.get("filter_value", conversation.get("filter_values", {})),
            "created_at": conversation.get("createdAt", conversation.get("created_at")),
            "updated_at": conversation.get("updatedAt", conversation.get("updated_at"))
        }

    def _normalize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize DynamoDB message to API response format"""
        message_id = message["sk"].split("#")[2]
        conversation_id = message["sk"].split("#")[1]
        metadata = message.get("metadata", {})

        normalized = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "role": message.get("role", ""),
            "content": message.get("content", ""),
            "filter_value": message.get("filter_value"),
            "created_at": message.get("createdAt", message.get("created_at")),
            "updated_at": message.get("updatedAt", message.get("updated_at")),
            "feedback": message.get("feedback", "")
        }

        # Add response_time if available in metadata
        if "response_time" in metadata:
            # Convert string response_time to float for consistency
            response_time = metadata["response_time"]
            try:
                normalized["response_time"] = float(response_time) if isinstance(response_time, str) else response_time
            except (ValueError, TypeError):
                # If conversion fails, keep as string
                normalized["response_time"] = response_time

        return normalized

    async def create_conversation(
        self,
        user_id: str,
        title: str = "",
        filter_values: Optional[Dict[str, Any]] = None
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Create a new conversation for a user

        Args:
            user_id: User identifier
            title: Optional conversation title
            filter_values: Optional filter values for document selection

        Returns:
            Result with created conversation or error details
        """
        try:
            if not title:
                title = f"Conversation - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

            logger.info(f"Creating conversation for user {user_id}")

            conversation = await self.adapter.create_conversation(
                user_id=user_id,
                title=title,
                filter_values=filter_values
            )

            # Normalize to API format
            normalized = self._normalize_conversation(conversation)

            return Ok(normalized)

        except Exception as e:
            logger.error(f"Error creating conversation: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to create conversation: {str(e)}"
            })

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 20,
        last_key: Optional[Dict[str, Any]] = None
    ) -> Result[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get list of conversations for a user

        Args:
            user_id: User identifier
            limit: Maximum number of conversations to return
            last_key: Pagination key for next page

        Returns:
            Result with list of conversations or error details
        """
        try:
            logger.info(f"Retrieving conversations for user {user_id}")

            conversations = await self.adapter.get_conversations(
                user_id=user_id,
                limit=limit,
                last_evaluated_key=last_key
            )

            # Normalize all conversations
            normalized = [self._normalize_conversation(conv) for conv in conversations]

            return Ok(normalized)

        except Exception as e:
            logger.error(f"Error fetching conversations: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to fetch conversations: {str(e)}"
            })

    async def get_conversation_by_id(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Get a specific conversation by ID

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier

        Returns:
            Result with conversation details or error
        """
        try:
            logger.info(f"Fetching conversation {conversation_id} for user {user_id}")

            conversation = await self.adapter.get_conversation_by_id(user_id, conversation_id)

            if not conversation:
                return Err({
                    "error": "not_found",
                    "message": f"Conversation {conversation_id} not found for user {user_id}"
                })

            # Normalize to API format
            normalized = self._normalize_conversation(conversation)

            return Ok(normalized)

        except Exception as e:
            logger.error(f"Error fetching conversation: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to fetch conversation: {str(e)}"
            })

    async def update_conversation_filters(
        self,
        user_id: str,
        conversation_id: str,
        filter_values: Dict[str, Any]
    ) -> Result[bool, Dict[str, Any]]:
        """
        Update filter values for a conversation

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            filter_values: New filter values

        Returns:
            Result with success status or error
        """
        try:
            logger.info(f"Updating filters for conversation {conversation_id}")

            success = await self.adapter.update_conversation_filters(
                user_id=user_id,
                conversation_id=conversation_id,
                filter_values=filter_values
            )

            return Ok(success)

        except Exception as e:
            logger.error(f"Error updating conversation filters: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to update conversation filters: {str(e)}"
            })

    async def get_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> Result[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get messages for a conversation

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            Result with list of messages or error
        """
        try:
            logger.info(f"Fetching messages for conversation {conversation_id}")

            messages = await self.adapter.get_messages(user_id, conversation_id, limit)

            # Normalize all messages
            normalized = [self._normalize_message(msg) for msg in messages]

            return Ok(normalized)

        except Exception as e:
            logger.error(f"Error fetching messages: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to fetch messages: {str(e)}"
            })

    async def delete_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[bool, Dict[str, Any]]:
        """
        Delete a conversation and all its messages

        Args:
            user_id: User identifier
            conversation_id: Conversation identifier

        Returns:
            Result with success status or error
        """
        try:
            logger.info(f"Deleting conversation {conversation_id} for user {user_id}")

            success = await self.adapter.delete_conversation_and_messages(
                user_id=user_id,
                conversation_id=conversation_id
            )

            return Ok(success)

        except Exception as e:
            logger.error(f"Error deleting conversation: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to delete conversation: {str(e)}"
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
            if not content.strip():
                return Err({
                    "error": "validation_error",
                    "message": "Message content cannot be empty"
                })

            logger.info(f"Adding user message to conversation {conversation_id}")

            message = await self.adapter.create_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="user",
                content=content.strip(),
                filter_value=context_filters,
                is_user_filter_text=bool(context_filters),
                metadata=metadata
            )

            # Extract message ID for easier access
            message_id = message["sk"].split("#")[2]
            message["message_id"] = message_id

            return Ok(message)

        except Exception as e:
            logger.error(f"Error adding user message: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to add user message: {str(e)}"
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
            if not content.strip():
                return Err({
                    "error": "validation_error",
                    "message": "Response content cannot be empty"
                })

            logger.info(f"Adding assistant response to conversation {conversation_id}")

            message = await self.adapter.create_message(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                content=content.strip(),
                filter_value=context_used,
                metadata=metadata
            )

            # Extract message ID for easier access
            message_id = message["sk"].split("#")[2]
            message["message_id"] = message_id

            return Ok(message)

        except Exception as e:
            logger.error(f"Error adding assistant response: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to add assistant response: {str(e)}"
            })

    async def update_message_feedback(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        feedback: FeedbackType
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """Update feedback for a message"""
        try:
            logger.info(f"Updating feedback for message {message_id}")

            updated_message = await self.adapter.update_message_feedback(
                message_id=message_id,
                conversation_id=conversation_id,
                user_id=user_id,
                feedback=feedback
            )

            if not updated_message:
                return Err({
                    "error": "not_found",
                    "message": f"Message {message_id} not found"
                })

            # Add extracted message ID
            updated_message["message_id"] = message_id

            return Ok(updated_message)

        except Exception as e:
            logger.error(f"Error updating message feedback: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to update message feedback: {str(e)}"
            })

    async def rename_conversation(
        self,
        user_id: str,
        conversation_id: str,
        new_title: str
    ) -> Result[bool, Dict[str, Any]]:
        """Rename a conversation"""
        try:
            if not new_title.strip():
                return Err({
                    "error": "validation_error",
                    "message": "Title cannot be empty"
                })

            logger.info(f"Renaming conversation {conversation_id} to '{new_title}'")

            success = await self.adapter.update_conversation_title(
                user_id=user_id,
                conversation_id=conversation_id,
                title=new_title.strip()
            )

            return Ok(success)

        except Exception as e:
            logger.error(f"Error renaming conversation: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to rename conversation: {str(e)}"
            })

    async def archive_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> Result[None, Dict[str, Any]]:
        """Mark a conversation as archived/inactive"""
        try:
            logger.info(f"Archiving conversation {conversation_id}")

            await self.adapter.update_conversation_status(
                user_id=user_id,
                conversation_id=conversation_id,
                is_active=False
            )

            return Ok(None)

        except Exception as e:
            logger.error(f"Error archiving conversation: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": f"Failed to archive conversation: {str(e)}"
            })
