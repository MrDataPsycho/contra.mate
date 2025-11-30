"""Conversations controller for conversation management endpoints."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from loguru import logger
from pydantic import BaseModel, Field

from contramate.services.postgres_conversation_service import PostgresConversationService


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# Schemas
class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation"""
    user_id: str = Field(..., description="User identifier")
    title: str = Field(default="New Conversation", description="Conversation title")
    filter_values: Optional[Dict[str, Any]] = Field(None, description="Optional filter values")


class UpdateConversationFiltersRequest(BaseModel):
    """Request model for updating conversation filters"""
    filter_values: Dict[str, Any] = Field(..., description="Filter values to update")


class ConversationResponse(BaseModel):
    """Response model for a conversation"""
    conversation_id: str
    user_id: str
    title: str
    filter_values: Dict[str, Any]
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    """Response model for list of conversations"""
    conversations: List[ConversationResponse]
    count: int


class MessageResponse(BaseModel):
    """Response model for a message"""
    message_id: str
    conversation_id: str
    role: str
    content: str
    filter_value: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str
    feedback: str = ""
    response_time: Optional[float] = Field(None, description="Response time in seconds (for assistant messages)")


class MessageListResponse(BaseModel):
    """Response model for list of messages"""
    messages: List[MessageResponse]
    count: int


# Dependency injection
def get_conversation_service() -> PostgresConversationService:
    """Get PostgresConversationService instance"""
    return PostgresConversationService.create_default()


# Endpoints
@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Create a new conversation.

    Args:
        request: Conversation creation request
        service: ConversationService instance

    Returns:
        Created conversation

    Example:
        ```json
        {
            "user_id": "user123",
            "title": "Contract Review Session",
            "filter_values": {
                "documents": [
                    {
                        "project_id": "proj1",
                        "reference_doc_id": "doc1",
                        "document_title": "Contract A"
                    }
                ]
            }
        }
        ```
    """
    try:
        logger.info(f"Creating conversation for user: {request.user_id}")

        result = await service.create_conversation(
            user_id=request.user_id,
            title=request.title,
            filter_values=request.filter_values
        )

        if result.is_ok():
            return result.unwrap()
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error creating conversation")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error creating conversation: {str(e)}"
        )


@router.get("/{user_id}", response_model=ConversationListResponse)
async def get_conversations(
    user_id: str,
    limit: int = 10,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Get conversations for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of conversations to return
        service: ConversationService instance

    Returns:
        List of conversations

    Example:
        GET /api/conversations/user123?limit=20
    """
    try:
        logger.info(f"Fetching conversations for user: {user_id}")

        result = await service.get_conversations(
            user_id=user_id,
            limit=limit
        )

        if result.is_ok():
            conversations = result.unwrap()
            return ConversationListResponse(
                conversations=conversations,
                count=len(conversations)
            )
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error fetching conversations")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversations: {str(e)}"
        )


@router.get("/{user_id}/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    user_id: str,
    conversation_id: str,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Get a specific conversation.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier
        service: ConversationService instance

    Returns:
        Conversation details

    Example:
        GET /api/conversations/user123/conv456
    """
    try:
        logger.info(f"Fetching conversation: {conversation_id} for user: {user_id}")

        result = await service.get_conversation_by_id(
            user_id=user_id,
            conversation_id=conversation_id
        )

        if result.is_ok():
            return result.unwrap()
        else:
            error_details = result.unwrap_err()
            if "not found" in error_details.get("error", "").lower():
                raise HTTPException(status_code=404, detail=error_details.get("message"))
            else:
                raise HTTPException(status_code=500, detail=error_details.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching conversation: {str(e)}"
        )


@router.put("/{user_id}/{conversation_id}/filters")
async def update_conversation_filters(
    user_id: str,
    conversation_id: str,
    request: UpdateConversationFiltersRequest,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Update conversation filter values.

    This endpoint allows updating the global filter for a conversation.
    When users add/remove documents, this updates the conversation's filter state.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier
        request: Filter update request
        service: ConversationService instance

    Returns:
        Success status

    Example:
        ```json
        {
            "filter_values": {
                "documents": [
                    {
                        "project_id": "proj1",
                        "reference_doc_id": "doc1",
                        "document_title": "Updated Contract"
                    }
                ]
            }
        }
        ```
    """
    try:
        logger.info(f"Updating filters for conversation: {conversation_id}")

        result = await service.update_conversation_filters(
            user_id=user_id,
            conversation_id=conversation_id,
            filter_values=request.filter_values
        )

        if result.is_ok():
            return {"success": True, "message": "Filters updated successfully"}
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error updating filters")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating filters: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error updating filters: {str(e)}"
        )


@router.get("/{user_id}/{conversation_id}/messages", response_model=MessageListResponse)
async def get_messages(
    user_id: str,
    conversation_id: str,
    limit: int = 50,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Get messages for a conversation.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier
        limit: Maximum number of messages to return
        service: ConversationService instance

    Returns:
        List of messages

    Example:
        GET /api/conversations/user123/conv456/messages?limit=100
    """
    try:
        logger.info(f"Fetching messages for conversation: {conversation_id}")

        result = await service.get_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=limit
        )

        if result.is_ok():
            messages = result.unwrap()
            return MessageListResponse(
                messages=messages,
                count=len(messages)
            )
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error fetching messages")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching messages: {str(e)}"
        )


@router.delete("/{user_id}/{conversation_id}")
async def delete_conversation(
    user_id: str,
    conversation_id: str,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Delete a conversation and all its messages.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier
        service: ConversationService instance

    Returns:
        Success status

    Example:
        DELETE /api/conversations/user123/conv456
    """
    try:
        logger.info(f"Deleting conversation: {conversation_id}")

        result = await service.delete_conversation(
            user_id=user_id,
            conversation_id=conversation_id
        )

        if result.is_ok():
            return {"success": True, "message": "Conversation deleted successfully"}
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error deleting conversation")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting conversation: {str(e)}"
        )


class AddMessageRequest(BaseModel):
    """Request model for adding a message to conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    filter_values: Optional[Dict[str, Any]] = Field(None, description="Optional filter context")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (e.g., response_time)")


@router.post("/{user_id}/{conversation_id}/messages")
async def add_message(
    user_id: str,
    conversation_id: str,
    request: AddMessageRequest,
    service: PostgresConversationService = Depends(get_conversation_service)
):
    """
    Add a message to a conversation.

    Args:
        user_id: User identifier
        conversation_id: Conversation identifier
        request: Message request with role and content
        service: ConversationService instance

    Returns:
        Created message

    Example:
        ```json
        {
            "role": "user",
            "content": "What are the payment terms?",
            "filter_values": {"documents": [...]}
        }
        ```
    """
    try:
        logger.info(f"Adding {request.role} message to conversation {conversation_id}")

        if request.role == "user":
            result = await service.add_user_message(
                user_id=user_id,
                conversation_id=conversation_id,
                content=request.content,
                context_filters=request.filter_values,
                metadata=request.metadata
            )
        elif request.role == "assistant":
            result = await service.add_assistant_response(
                user_id=user_id,
                conversation_id=conversation_id,
                content=request.content,
                context_used=request.filter_values,
                metadata=request.metadata
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role: {request.role}. Must be 'user' or 'assistant'"
            )

        if result.is_ok():
            return result.unwrap()
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error adding message")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error adding message: {str(e)}"
        )
