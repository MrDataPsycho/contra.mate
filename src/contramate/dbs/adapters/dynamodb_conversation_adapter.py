"""
DynamoDB Conversation Store Adapter

Provides async CRUD operations for conversations and messages using DynamoDB.
Uses a single-table design:
Partition key: PK (e.g., USER#user_id)
Sort key: SK (e.g., CONV#conversation_id or MSG#conversation_id#message_id)
Async with aioboto3 for FastAPI compatibility.
Methods for create, get, and delete for both conversations and messages.
Extend as needed for update, feedback, etc.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aioboto3

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository
from contramate.dbs.models import FeedbackType
from contramate.utils.settings.core import DynamoDBSettings

logger = logging.getLogger(__name__)


class DynamoDBConversationAdapter(AbstractConversationRepository):
    """
    Service for managing conversations and messages in DynamoDB.
    """

    def __init__(self, table_name: str, dynamodb_settings: DynamoDBSettings) -> None:
        self.table_name: str = table_name
        self.dynamodb_settings: DynamoDBSettings = dynamodb_settings

    @property
    def session(self) -> Any:
        return aioboto3.Session(
            aws_access_key_id=self.dynamodb_settings.access_key_id,
            aws_secret_access_key=self.dynamodb_settings.secret_access_key,
            region_name=self.dynamodb_settings.region
        )

    def _sort_items(
        self, items: List[Dict[str, Any]], key: str = "updatedAt", reverse: bool = True
    ) -> List[Dict[str, Any]]:
        return sorted(items, key=lambda x: x.get(key, ""), reverse=reverse)

    async def create_conversation(
        self, 
        user_id: str, 
        title: str = "", 
        conversation_id: Optional[str] = None, 
        filter_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation item.
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        conversation: Dict[str, Any] = {
            "pk": f"USER#{user_id}",
            "sk": f"CONV#{conversation_id}",
            "type": "conversation",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "userId": user_id,
            "title": title,
            "filter_value": filter_values or {},
        }
        logger.info(f"Creating New conversation for user {user_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            await table.put_item(Item=conversation)
        return conversation
        

    async def get_conversations(
        self,
        user_id: str,
        limit: int = 10,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        last_evaluated_key={"pk": "USER#user_id", "sk": "CONV#12345"}
        """
        query_params: Dict[str, Any] = {
            "KeyConditionExpression": "pk = :pk AND begins_with(sk, :sk)",
            "ExpressionAttributeValues": {
                ":pk": f"USER#{user_id}",
                ":sk": "CONV#",
            },
            "Limit": limit,
        }
        logger.info(f"Getting conversations for {user_id}")

        if last_evaluated_key:
            query_params["ExclusiveStartKey"] = last_evaluated_key
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.query(**query_params)
            filtered: List[Dict[str, Any]] = self._sort_items(response.get("Items", []))
        return filtered[:limit]

    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        """
        Delete a conversation item by user and conversation ID.
        """
        logger.info(f"Deleting conversation {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            await table.delete_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                }
            )

    async def get_message_items_for_conversation(self, user_id: str, conversation_id: str) -> List[Dict[str, Any]]:
        """
        Query all message items for a given conversation.
        """
        logger.info(f"get_message_items_for_conversation for {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :msg_prefix)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":msg_prefix": f"MSG#{conversation_id}",
                },
            )
        return response.get("Items", [])

    async def delete_message_items(self, items: List[Dict[str, Any]]) -> None:
        """
        Delete all message items provided in the list.
        """
        logger.info("delete_message_items")
        if not items:
            return
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            for item in items:
                await table.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})

    async def delete_conversation_and_messages(self, user_id: str, conversation_id: str) -> bool:
        """
        Delete a conversation and all associated messages for a user.
        """
        logger.info(f"delete_conversation_and_messages {conversation_id}")
        await self.delete_conversation(user_id, conversation_id)
        message_items: List[Dict[str, Any]] = await self.get_message_items_for_conversation(user_id, conversation_id)
        await self.delete_message_items(message_items)
        return True

    async def create_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        feedback: str = "",
        message_id: Optional[str] = None,
        filter_value: Optional[Dict[str, Any]] = None,
        is_user_filter_text: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new message in a conversation.

        Args:
            metadata: Optional metadata dict for storing additional info like response_time
        """
        if message_id is None:
            message_id = str(uuid.uuid4())
        message: Dict[str, Any] = {
            "pk": f"USER#{user_id}",
            "sk": f"MSG#{conversation_id}#{message_id}",
            "type": "message",
            "conversationId": conversation_id,
            "userId": user_id,
            "role": role,
            "content": content,
            "feedback": feedback,
            "filter_value": filter_value,
            "is_user_filter_text": is_user_filter_text,
            "metadata": metadata or {},  # Store metadata like response_time
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"create_message {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            await table.put_item(Item=message)
            await self.touch_conversation(user_id, conversation_id)
        return message

    async def get_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation.
        """
        logger.info(f"get_messages for {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={
                    ":pk": f"USER#{user_id}",
                    ":sk": f"MSG#{conversation_id}#",
                },
                Limit=limit,
            )
        return self._sort_items(response.get("Items", []), key="createdAt", reverse=False)

    async def get_conversation_by_id(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single conversation by user_id and conversation_id.
        """
        logger.info(f"get_conversation_by_id {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.get_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                }
            )
        return response.get("Item")

    async def get_conversations_last_90_days(
        self,
        user_id: str,
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user from the last 90 days, ordered by createdAt descending.
        """
        logger.info(f"get_conversations_last_90_days {user_id}")
        cutoff_date: str = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        query_params: Dict[str, Any] = {
            "KeyConditionExpression": "pk = :pk AND begins_with(sk, :sk)",
            "ExpressionAttributeValues": {
                ":pk": f"USER#{user_id}",
                ":sk": "CONV#",
            },
        }
        if last_evaluated_key:
            query_params["ExclusiveStartKey"] = last_evaluated_key
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.query(**query_params)
        items: List[Dict[str, Any]] = response.get("Items", [])
        filtered: List[Dict[str, Any]] = [
            item for item in items if "updatedAt" in item and item["updatedAt"] >= cutoff_date
        ]
        filtered = self._sort_items(filtered)
        return filtered[:limit]

    async def update_message_feedback(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        feedback: FeedbackType,
    ) -> Optional[Dict[str, Any]]:
        """
        Update the feedback field of a message and return the full updated item.
        """
        logger.info(f"update_message_feedback {user_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.update_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"MSG#{conversation_id}#{message_id}",
                },
                UpdateExpression=("SET feedback = :feedback, updatedAt = :updatedAt"),
                ExpressionAttributeValues={
                    ":feedback": feedback.value,
                    ":updatedAt": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="ALL_NEW",
            )
        if response:
            await self.touch_conversation(user_id, conversation_id)
        return response.get("Attributes")

    async def update_conversation_title(self, user_id: str, conversation_id: str, title: str) -> bool:
        """
        Update the title of a conversation.
        """
        logger.info(f"update_conversation_title {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.update_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                },
                UpdateExpression="SET title = :title, updatedAt = :updatedAt",
                ExpressionAttributeValues={
                    ":title": title,
                    ":updatedAt": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="UPDATED_NEW",
            )
        return "Attributes" in response

    async def update_conversation_filters(
        self, 
        user_id: str, 
        conversation_id: str, 
        filter_values: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update the filter values of a conversation.
        """
        logger.info(f"update_conversation_filter {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.update_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                },
                UpdateExpression="SET filter_value = :filter_values, updatedAt = :updatedAt",
                ExpressionAttributeValues={
                    ":filter_values": filter_values or {},
                    ":updatedAt": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="UPDATED_NEW",
            )
        return "Attributes" in response

    async def touch_conversation(self, user_id: str, conversation_id: str) -> bool:
        """
        Update only the updatedAt field of a conversation to the current timestamp.
        """
        logger.info(f"touch_conversation Update updatedAt for {conversation_id}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            response: Dict[str, Any] = await table.update_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                },
                UpdateExpression="SET updatedAt = :updatedAt",
                ExpressionAttributeValues={
                    ":updatedAt": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="UPDATED_NEW",
            )
        return "Attributes" in response

    async def update_conversation_status(
        self,
        user_id: str,
        conversation_id: str,
        is_active: bool,
    ) -> None:
        """
        Update the active status of a conversation.
        """
        logger.info(f"update_conversation_status for {conversation_id} to {is_active}")
        async with self.session.resource(
            "dynamodb", 
            region_name=self.dynamodb_settings.region,
            endpoint_url=self.dynamodb_settings.endpoint_url,
            
            
        ) as dynamodb:
            table = await dynamodb.Table(self.table_name)
            await table.update_item(
                Key={
                    "pk": f"USER#{user_id}",
                    "sk": f"CONV#{conversation_id}",
                },
                UpdateExpression="SET is_active = :active",
                ExpressionAttributeValues={":active": is_active},
            )