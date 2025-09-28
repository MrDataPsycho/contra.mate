"""
Conversation Service

Business logic layer for conversation management using DynamoDB adapter.
Provides high-level operations and validation for conversation workflows.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from contramate.dbs.adapters import DynamoDBConversationAdapter
from contramate.dbs.models import FeedbackType
from contramate.utils.settings.core import settings

logger = logging.getLogger(__name__)


class ConversationService:
    """High-level service for conversation management"""
    
    def __init__(self, table_name: str = "conversations"):
        self.adapter = DynamoDBConversationAdapter(
            table_name=table_name,
            region_name=settings.dynamodb.region
        )
    
    async def start_new_conversation(
        self, 
        user_id: str, 
        title: str = "", 
        contract_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new conversation for a user
        
        Args:
            user_id: User identifier
            title: Optional conversation title
            contract_filters: Optional filters for contract searching
            
        Returns:
            Created conversation object
        """
        if not title:
            title = f"Conversation - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
            
        logger.info(f"Starting new conversation for user {user_id}")
        
        conversation = await self.adapter.create_conversation(
            user_id=user_id,
            title=title,
            filter_values=contract_filters
        )
        
        # Extract conversation ID for easier access
        conversation_id = conversation["sk"].split("#")[1]
        conversation["conversation_id"] = conversation_id
        
        return conversation
    
    async def add_user_message(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        context_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a user message to the conversation"""
        
        if not content.strip():
            raise ValueError("Message content cannot be empty")
            
        logger.info(f"Adding user message to conversation {conversation_id}")
        
        message = await self.adapter.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=content.strip(),
            filter_value=context_filters,
            is_user_filter_text=bool(context_filters)
        )
        
        # Extract message ID for easier access
        message_id = message["sk"].split("#")[2]
        message["message_id"] = message_id
        
        return message
    
    async def add_assistant_response(
        self,
        user_id: str,
        conversation_id: str,
        content: str,
        context_used: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add an assistant response to the conversation"""
        
        if not content.strip():
            raise ValueError("Response content cannot be empty")
            
        logger.info(f"Adding assistant response to conversation {conversation_id}")
        
        message = await self.adapter.create_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=content.strip(),
            filter_value=context_used
        )
        
        # Extract message ID for easier access  
        message_id = message["sk"].split("#")[2]
        message["message_id"] = message_id
        
        return message
    
    async def get_conversation_history(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get full conversation with messages
        
        Returns:
            Dictionary with conversation metadata and messages list
        """
        logger.info(f"Retrieving conversation history for {conversation_id}")
        
        # Get conversation metadata
        conversation = await self.adapter.get_conversation_by_id(user_id, conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found for user {user_id}")
        
        # Get messages
        messages = await self.adapter.get_messages(user_id, conversation_id, limit)
        
        # Add extracted IDs to messages
        for message in messages:
            message_id = message["sk"].split("#")[2]
            message["message_id"] = message_id
        
        return {
            "conversation": conversation,
            "messages": messages,
            "message_count": len(messages)
        }
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        last_key: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get list of conversations for a user"""
        
        logger.info(f"Retrieving conversations for user {user_id}")
        
        conversations = await self.adapter.get_conversations(
            user_id=user_id,
            limit=limit,
            last_evaluated_key=last_key
        )
        
        # Add extracted conversation IDs
        for conversation in conversations:
            conversation_id = conversation["sk"].split("#")[1]
            conversation["conversation_id"] = conversation_id
            
        return conversations
    
    async def update_message_feedback(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        feedback: FeedbackType
    ) -> Dict[str, Any]:
        """Update feedback for a message"""
        
        logger.info(f"Updating feedback for message {message_id}")
        
        updated_message = await self.adapter.update_message_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=user_id,
            feedback=feedback
        )
        
        if not updated_message:
            raise ValueError(f"Message {message_id} not found")
            
        # Add extracted message ID
        updated_message["message_id"] = message_id
        
        return updated_message
    
    async def rename_conversation(
        self,
        user_id: str,
        conversation_id: str,
        new_title: str
    ) -> bool:
        """Rename a conversation"""
        
        if not new_title.strip():
            raise ValueError("Title cannot be empty")
            
        logger.info(f"Renaming conversation {conversation_id} to '{new_title}'")
        
        return await self.adapter.update_conversation_title(
            user_id=user_id,
            conversation_id=conversation_id,
            title=new_title.strip()
        )
    
    async def delete_conversation(
        self,
        user_id: str, 
        conversation_id: str
    ) -> bool:
        """Delete a conversation and all its messages"""
        
        logger.info(f"Deleting conversation {conversation_id} for user {user_id}")
        
        return await self.adapter.delete_conversation_and_messages(
            user_id=user_id,
            conversation_id=conversation_id
        )
    
    async def archive_conversation(
        self,
        user_id: str,
        conversation_id: str
    ) -> None:
        """Mark a conversation as archived/inactive"""
        
        logger.info(f"Archiving conversation {conversation_id}")
        
        await self.adapter.update_conversation_status(
            user_id=user_id,
            conversation_id=conversation_id,
            is_active=False
        )