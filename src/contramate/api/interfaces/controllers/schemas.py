"""Request and response schemas for chat API"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Request Models
class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation"""

    title: Optional[str] = Field(None, description="Optional conversation title")
    filter_values: Optional[Dict[str, Any]] = Field(
        None, description="Optional filter values for contract searching"
    )


class SendMessageRequest(BaseModel):
    """Request model for sending a message"""

    content: str = Field(..., min_length=1, description="Message content")
    context_filters: Optional[Dict[str, Any]] = Field(
        None, description="Optional context filters for this message"
    )
    get_ai_response: bool = Field(
        True, description="Whether to get AI response immediately"
    )


class UpdateMessageFeedbackRequest(BaseModel):
    """Request model for updating message feedback"""

    feedback: str = Field(..., description="Feedback type (LIKE or DISLIKE)")


class UpdateConversationTitleRequest(BaseModel):
    """Request model for updating conversation title"""

    title: str = Field(..., min_length=1, description="New conversation title")


class TalkToContractRequest(BaseModel):
    """Request model for talk to contract queries"""

    query: str = Field(..., min_length=1, description="User query about contracts")
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional filters for search (documents, contract_type, source, project)",
    )
    message_history: Optional[List[Dict[str, str]]] = Field(
        None, description="Optional conversation history for context"
    )


# Response Models
class MessageResponse(BaseModel):
    """Response model for a message"""

    message_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    updated_at: str
    feedback: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    filter_value: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    """Response model for a conversation"""

    conversation_id: str
    user_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    filter_values: Optional[Dict[str, Any]] = None
    message_count: int


class ConversationWithMessagesResponse(BaseModel):
    """Response model for conversation with messages"""

    conversation: ConversationResponse
    messages: List[MessageResponse]


class ChatResponse(BaseModel):
    """Response model for chat interaction"""

    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
    timestamp: str


class ConversationListResponse(BaseModel):
    """Response model for list of conversations"""

    conversations: List[ConversationResponse]
    count: int


class ErrorResponse(BaseModel):
    """Response model for errors"""

    error: str
    status_code: int
    timestamp: str


class SuccessResponse(BaseModel):
    """Response model for success messages"""

    message: str
    status_code: int
    timestamp: str
    data: Optional[Any] = None


class TalkToContractResponse(BaseModel):
    """Response model for talk to contract queries"""

    success: bool
    answer: str = Field(..., description="The formatted answer with citations")
    citations: Dict[str, str] = Field(
        ..., description="Mapping of citation keys to document names"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata like token usage"
    )
    error: Optional[str] = Field(None, description="Error message if query failed")
