"""Chat presenter for formatting chat responses"""

from typing import Any, Dict, List
from datetime import datetime

from contramate.domain.entities.conversation import Conversation
from contramate.domain.entities.message import Message


class ChatPresenter:
    """
    Presenter for formatting chat-related responses.

    Converts domain entities to API response formats.
    """

    @staticmethod
    def format_message(message: Message) -> Dict[str, Any]:
        """
        Format a message for API response.

        Args:
            message: Message entity

        Returns:
            Dict with formatted message data
        """
        return {
            "message_id": message.message_id,
            "conversation_id": message.conversation_id,
            "role": message.role.value,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "updated_at": message.updated_at.isoformat(),
            "feedback": message.feedback,
            "tool_calls": message.tool_calls,
            "tool_call_id": message.tool_call_id,
            "filter_value": message.filter_value,
        }

    @staticmethod
    def format_messages(messages: List[Message]) -> List[Dict[str, Any]]:
        """
        Format multiple messages for API response.

        Args:
            messages: List of Message entities

        Returns:
            List of formatted message dicts
        """
        return [ChatPresenter.format_message(msg) for msg in messages]

    @staticmethod
    def format_conversation(conversation: Conversation) -> Dict[str, Any]:
        """
        Format a conversation for API response.

        Args:
            conversation: Conversation entity

        Returns:
            Dict with formatted conversation data
        """
        return {
            "conversation_id": conversation.conversation_id,
            "user_id": conversation.user_id,
            "title": conversation.title,
            "status": conversation.status.value,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "filter_values": conversation.filter_values,
            "message_count": conversation.get_message_count(),
        }

    @staticmethod
    def format_conversation_with_messages(
        conversation: Conversation,
    ) -> Dict[str, Any]:
        """
        Format a conversation with its messages for API response.

        Args:
            conversation: Conversation entity with messages

        Returns:
            Dict with formatted conversation and messages
        """
        return {
            "conversation": ChatPresenter.format_conversation(conversation),
            "messages": ChatPresenter.format_messages(conversation.messages),
        }

    @staticmethod
    def format_conversations(conversations: List[Conversation]) -> List[Dict[str, Any]]:
        """
        Format multiple conversations for API response.

        Args:
            conversations: List of Conversation entities

        Returns:
            List of formatted conversation dicts
        """
        return [ChatPresenter.format_conversation(conv) for conv in conversations]

    @staticmethod
    def format_chat_response(
        user_message: Message, assistant_message: Message
    ) -> Dict[str, Any]:
        """
        Format a complete chat interaction (user message + AI response).

        Args:
            user_message: User's message entity
            assistant_message: Assistant's response entity

        Returns:
            Dict with both messages and metadata
        """
        return {
            "conversation_id": user_message.conversation_id,
            "user_message": ChatPresenter.format_message(user_message),
            "assistant_message": ChatPresenter.format_message(assistant_message),
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_error(error_message: str, status_code: int = 400) -> Dict[str, Any]:
        """
        Format an error response.

        Args:
            error_message: Error message to return
            status_code: HTTP status code

        Returns:
            Dict with error details
        """
        return {
            "error": error_message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def format_success(
        message: str, data: Any = None, status_code: int = 200
    ) -> Dict[str, Any]:
        """
        Format a success response.

        Args:
            message: Success message
            data: Optional data payload
            status_code: HTTP status code

        Returns:
            Dict with success details
        """
        response = {
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if data is not None:
            response["data"] = data

        return response
