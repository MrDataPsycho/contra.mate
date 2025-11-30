"""
PostgreSQL SQLModel models for conversations and messages.

These models replace the DynamoDB schema to overcome the 400KB text field limitation.
Uses SQLModel (SQLAlchemy + Pydantic) for type-safe database operations.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON, Text
from contramate.dbs.models.conversation import FeedbackType


class ConversationBase(SQLModel):
    """Base model for Conversation with shared fields"""
    user_id: str = Field(index=True, max_length=255)
    title: str = Field(default="", max_length=500)
    filter_values: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(ConversationBase, table=True):
    """
    Conversation table model.

    Stores conversation metadata including user, title, and filter settings.
    One conversation can have many messages.
    """
    __tablename__ = "conversations"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "title": "Contract Analysis Discussion",
                "filter_values": {"documents": ["doc1", "doc2"]},
                "is_active": True,
                "created_at": "2025-11-30T10:00:00Z",
                "updated_at": "2025-11-30T10:00:00Z"
            }
        }


class MessageBase(SQLModel):
    """Base model for Message with shared fields"""
    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    user_id: str = Field(index=True, max_length=255)
    role: str = Field(max_length=50)  # "user" or "assistant"
    content: str = Field(sa_column=Column(Text))  # TEXT type for unlimited length
    feedback: str = Field(default="", max_length=50)
    filter_values: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    is_user_filter_text: bool = Field(default=False)
    msg_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))  # Renamed to avoid shadowing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Message(MessageBase, table=True):
    """
    Message table model.

    Stores individual messages within conversations.
    Uses TEXT field for content to support large messages (>400KB).
    """
    __tablename__ = "messages"

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "role": "user",
                "content": "What are the key terms in this contract?",
                "feedback": "",
                "filter_values": {"documents": ["doc1"]},
                "is_user_filter_text": False,
                "msg_metadata": {"response_time": "2.5"},
                "created_at": "2025-11-30T10:01:00Z",
                "updated_at": "2025-11-30T10:01:00Z"
            }
        }


# Response models for API
class ConversationRead(ConversationBase):
    """Response model for reading conversations"""
    id: UUID
    created_at: datetime
    updated_at: datetime


class MessageRead(MessageBase):
    """Response model for reading messages"""
    id: UUID
    created_at: datetime
    updated_at: datetime


class ConversationCreate(SQLModel):
    """Model for creating a new conversation"""
    user_id: str
    title: str = ""
    filter_values: Optional[Dict[str, Any]] = None


class MessageCreate(SQLModel):
    """Model for creating a new message"""
    conversation_id: UUID
    user_id: str
    role: str
    content: str
    feedback: str = ""
    filter_values: Optional[Dict[str, Any]] = None
    is_user_filter_text: bool = False
    msg_metadata: Optional[Dict[str, Any]] = None
