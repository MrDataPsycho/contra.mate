"""Get AI response use case"""

from typing import Any, Dict, List, Optional, Union
from loguru import logger

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.domain.entities.message import Message
from contramate.domain.value_objects.message_role import MessageRole
from contramate.core.agents.orchrastrator import OrchrastratorAgent
from contramate.llm import OpenAIChatClient


class GetAIResponseUseCase:
    """
    Use case for getting AI response to a user message.

    Orchestrates the AI agent workflow and persists the response.
    """

    def __init__(
        self,
        conversation_repository: AbstractConversationRepository,
        orchestrator_agent: OrchrastratorAgent,
    ):
        """
        Initialize use case.

        Args:
            conversation_repository: Repository for conversation/message persistence
            orchestrator_agent: AI orchestrator agent
        """
        self.conversation_repository = conversation_repository
        self.orchestrator_agent = orchestrator_agent

    async def execute(
        self,
        user_id: str,
        conversation_id: str,
        user_message_content: str,
        context_limit: int = 10,
    ) -> Message:
        """
        Get AI response for a user message.

        Args:
            user_id: ID of the user
            conversation_id: ID of the conversation
            user_message_content: The user's message content
            context_limit: Number of previous messages to include as context

        Returns:
            AI assistant message entity

        Raises:
            ValueError: If conversation doesn't exist
        """
        logger.info(
            f"Getting AI response for conversation {conversation_id}, user {user_id}"
        )

        # Get conversation history
        messages_data = await self.conversation_repository.get_messages(
            user_id=user_id, conversation_id=conversation_id, limit=context_limit
        )

        # Convert to domain entities (excluding the latest user message we just sent)
        conversation_history = []
        for msg_data in messages_data[:-1]:  # Exclude last message (current user msg)
            msg = Message.from_dynamodb_item(msg_data)
            conversation_history.append(msg.to_openai_format())

        logger.info(
            f"Retrieved {len(conversation_history)} previous messages for context"
        )

        # Call orchestrator agent
        try:
            ai_response = self.orchestrator_agent(
                input=user_message_content, conversation_history=conversation_history
            )
            logger.info(f"Received AI response: {ai_response[:100]}...")
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            raise ValueError(f"Failed to get AI response: {str(e)}")

        # Save assistant response
        assistant_message_data = await self.conversation_repository.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=ai_response,
        )

        # Convert to domain entity
        assistant_message = Message.from_dynamodb_item(assistant_message_data)

        logger.info(
            f"Created assistant message {assistant_message.message_id} in conversation {conversation_id}"
        )

        return assistant_message

    async def execute_with_tool_tracking(
        self,
        user_id: str,
        conversation_id: str,
        user_message_content: str,
        context_limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get AI response with detailed tool tracking.

        Returns both the response and intermediate tool calls.

        Args:
            user_id: ID of the user
            conversation_id: ID of the conversation
            user_message_content: The user's message content
            context_limit: Number of previous messages to include

        Returns:
            Dict with assistant_message, tool_calls, and metadata
        """
        logger.info(
            f"Getting AI response with tool tracking for conversation {conversation_id}"
        )

        # Get conversation history
        messages_data = await self.conversation_repository.get_messages(
            user_id=user_id, conversation_id=conversation_id, limit=context_limit
        )

        # Convert to OpenAI format
        conversation_history = []
        for msg_data in messages_data[:-1]:
            msg = Message.from_dynamodb_item(msg_data)
            conversation_history.append(msg.to_openai_format())

        # Call orchestrator agent with detailed tracking
        # Note: This would require extending the orchestrator to return tool calls
        # For now, we'll use the simple execute method
        ai_response = self.orchestrator_agent(
            input=user_message_content, conversation_history=conversation_history
        )

        # Save assistant response
        assistant_message_data = await self.conversation_repository.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT.value,
            content=ai_response,
            # TODO: Add tool_calls tracking when orchestrator supports it
        )

        assistant_message = Message.from_dynamodb_item(assistant_message_data)

        return {
            "assistant_message": assistant_message,
            "tool_calls": [],  # TODO: Extract from orchestrator
            "metadata": {
                "context_messages_used": len(conversation_history),
                "conversation_id": conversation_id,
            },
        }
