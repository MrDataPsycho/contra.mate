#!/usr/bin/env python3
"""
Test script for DynamoDB Conversation Adapter

Usage:
    python src/tools/test_conversation_adapter.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Use package-level imports following CLAUDE.md guidelines
from contramate.dbs import DynamoDBConversationAdapter, FeedbackType
from contramate.utils.settings.core import settings

async def test_conversation_adapter():
    """Test the DynamoDB conversation adapter"""
    print("🧪 Testing DynamoDB Conversation Adapter")
    
    # Initialize adapter
    adapter = DynamoDBConversationAdapter(
        table_name="conversations",  # We'll use this test table name
        region_name=settings.dynamodb.region
    )
    
    test_user_id = "test_user_123"
    
    try:
        print(f"📝 Testing conversation creation...")
        # Create a conversation
        conversation = await adapter.create_conversation(
            user_id=test_user_id,
            title="Test Conversation",
            filter_values={"contract_type": "employment"}
        )
        
        conversation_id = conversation["sk"].split("#")[1]  # Extract conversation ID
        print(f"✅ Created conversation: {conversation_id}")
        
        print(f"💬 Testing message creation...")
        # Create a message
        message = await adapter.create_message(
            user_id=test_user_id,
            conversation_id=conversation_id,
            role="user",
            content="What are the key terms in this contract?",
            filter_value={"urgent": True}
        )
        
        message_id = message["sk"].split("#")[2]  # Extract message ID  
        print(f"✅ Created message: {message_id}")
        
        print(f"📋 Testing conversation retrieval...")
        # Get conversations
        conversations = await adapter.get_conversations(user_id=test_user_id, limit=5)
        print(f"✅ Retrieved {len(conversations)} conversations")
        
        print(f"💭 Testing message retrieval...")
        # Get messages
        messages = await adapter.get_messages(
            user_id=test_user_id, 
            conversation_id=conversation_id
        )
        print(f"✅ Retrieved {len(messages)} messages")
        
        print(f"👍 Testing feedback update...")
        # Update message feedback
        updated_message = await adapter.update_message_feedback(
            message_id=message_id,
            conversation_id=conversation_id,
            user_id=test_user_id,
            feedback=FeedbackType.LIKE
        )
        print(f"✅ Updated message feedback")
        
        print(f"🏷️ Testing conversation title update...")
        # Update conversation title
        title_updated = await adapter.update_conversation_title(
            user_id=test_user_id,
            conversation_id=conversation_id,
            title="Updated Test Conversation"
        )
        print(f"✅ Updated conversation title: {title_updated}")
        
        print(f"🧹 Testing cleanup...")
        # Clean up - delete conversation and messages
        deleted = await adapter.delete_conversation_and_messages(
            user_id=test_user_id,
            conversation_id=conversation_id
        )
        print(f"✅ Cleaned up conversation and messages: {deleted}")
        
        print("\n🎉 All tests passed! DynamoDB Conversation Adapter is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_conversation_adapter())