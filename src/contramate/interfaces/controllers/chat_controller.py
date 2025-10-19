"""Chat controller for handling chat-related HTTP requests"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from loguru import logger

from contramate.interfaces.controllers.schemas import (
    CreateConversationRequest,
    SendMessageRequest,
    UpdateMessageFeedbackRequest,
    UpdateConversationTitleRequest,
    ConversationResponse,
    ConversationWithMessagesResponse,
    ChatResponse,
    ConversationListResponse,
    SuccessResponse,
)
from contramate.interfaces.presenters.chat_presenter import ChatPresenter
from contramate.use_cases.chat import (
    CreateConversationUseCase,
    SendMessageUseCase,
    GetAIResponseUseCase,
    GetConversationUseCase,
    ListConversationsUseCase,
)
from contramate.dbs.adapters import DynamoDBConversationAdapter
from contramate.dbs.models import FeedbackType
from contramate.utils.settings.core import DynamoDBSettings
from contramate.llm import OpenAIChatClient
from contramate.core.agents.orchrastrator import OrchrastratorAgent


router = APIRouter(prefix="/api/chat", tags=["chat"])


# Dependency injection
def get_conversation_repository() -> DynamoDBConversationAdapter:
    """Get conversation repository instance"""
    dynamodb_settings = DynamoDBSettings()
    return DynamoDBConversationAdapter(
        table_name=dynamodb_settings.table_name,
        dynamodb_settings=dynamodb_settings,
    )


def get_orchestrator_agent() -> OrchrastratorAgent:
    """Get orchestrator agent instance"""
    client = OpenAIChatClient()
    return OrchrastratorAgent(client)


def get_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """
    Get user ID from request header.

    For now, this is a simple header-based auth.
    TODO: Replace with proper JWT authentication
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# Endpoints
@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    Create a new conversation.

    Args:
        request: Conversation creation request
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        Created conversation
    """
    try:
        logger.info(f"Creating conversation for user {user_id}")

        use_case = CreateConversationUseCase(repository)
        conversation = await use_case.execute(
            user_id=user_id,
            title=request.title,
            filter_values=request.filter_values,
        )

        return ChatPresenter.format_conversation(conversation)

    except ValueError as e:
        logger.error(f"Validation error creating conversation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = 20,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    List user's conversations.

    Args:
        limit: Maximum number of conversations to return
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        List of conversations
    """
    try:
        logger.info(f"Listing conversations for user {user_id}")

        use_case = ListConversationsUseCase(repository)
        conversations = await use_case.execute(user_id=user_id, limit=limit)

        formatted_conversations = ChatPresenter.format_conversations(conversations)

        return {
            "conversations": formatted_conversations,
            "count": len(formatted_conversations),
        }

    except ValueError as e:
        logger.error(f"Validation error listing conversations: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationWithMessagesResponse,
)
async def get_conversation(
    conversation_id: str,
    message_limit: int = 50,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    Get a conversation with its messages.

    Args:
        conversation_id: ID of the conversation
        message_limit: Maximum number of messages to return
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        Conversation with messages
    """
    try:
        logger.info(f"Getting conversation {conversation_id} for user {user_id}")

        use_case = GetConversationUseCase(repository)
        conversation = await use_case.execute(
            user_id=user_id,
            conversation_id=conversation_id,
            message_limit=message_limit,
        )

        return ChatPresenter.format_conversation_with_messages(conversation)

    except ValueError as e:
        logger.error(f"Validation error getting conversation: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
    agent: OrchrastratorAgent = Depends(get_orchestrator_agent),
):
    """
    Send a message to a conversation and optionally get AI response.

    Args:
        conversation_id: ID of the conversation
        request: Message request
        user_id: User ID from header
        repository: Conversation repository
        agent: Orchestrator agent

    Returns:
        User message and AI response
    """
    try:
        logger.info(
            f"Sending message to conversation {conversation_id} for user {user_id}"
        )

        # Send user message
        send_message_use_case = SendMessageUseCase(repository)
        user_message = await send_message_use_case.execute(
            user_id=user_id,
            conversation_id=conversation_id,
            content=request.content,
            context_filters=request.context_filters,
        )

        # Get AI response if requested
        if request.get_ai_response:
            get_ai_response_use_case = GetAIResponseUseCase(repository, agent)
            assistant_message = await get_ai_response_use_case.execute(
                user_id=user_id,
                conversation_id=conversation_id,
                user_message_content=request.content,
            )
        else:
            # Return just the user message with empty assistant message
            return ChatPresenter.format_chat_response(user_message, user_message)

        return ChatPresenter.format_chat_response(user_message, assistant_message)

    except ValueError as e:
        logger.error(f"Validation error sending message: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: ID of the conversation
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        Success response
    """
    try:
        logger.info(f"Deleting conversation {conversation_id} for user {user_id}")

        success = await repository.delete_conversation_and_messages(
            user_id=user_id, conversation_id=conversation_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ChatPresenter.format_success(
            f"Conversation {conversation_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch(
    "/conversations/{conversation_id}/title", response_model=SuccessResponse
)
async def update_conversation_title(
    conversation_id: str,
    request: UpdateConversationTitleRequest,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    Update conversation title.

    Args:
        conversation_id: ID of the conversation
        request: Title update request
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        Success response
    """
    try:
        logger.info(f"Updating title for conversation {conversation_id}")

        success = await repository.update_conversation_title(
            user_id=user_id, conversation_id=conversation_id, title=request.title
        )

        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return ChatPresenter.format_success("Conversation title updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation title: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=SuccessResponse,
)
async def update_message_feedback(
    conversation_id: str,
    message_id: str,
    request: UpdateMessageFeedbackRequest,
    user_id: str = Depends(get_user_id),
    repository: DynamoDBConversationAdapter = Depends(get_conversation_repository),
):
    """
    Update message feedback.

    Args:
        conversation_id: ID of the conversation
        message_id: ID of the message
        request: Feedback update request
        user_id: User ID from header
        repository: Conversation repository

    Returns:
        Success response
    """
    try:
        logger.info(f"Updating feedback for message {message_id}")

        # Validate feedback type
        try:
            feedback_type = FeedbackType(request.feedback)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid feedback type. Use LIKE or DISLIKE"
            )

        updated_message = await repository.update_message_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            feedback=feedback_type,
        )

        if not updated_message:
            raise HTTPException(status_code=404, detail="Message not found")

        return ChatPresenter.format_success("Message feedback updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating message feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
