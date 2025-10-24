"""
Script to create DynamoDB ConversationTable for local development.

This script creates the ConversationTable with the required schema:
- Partition key (pk): Stores USER#{user_id}
- Sort key (sk): Stores CONV#{conversation_id} or MSG#{conversation_id}#{message_id}
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aioboto3
from loguru import logger

from contramate.utils.settings.core import DynamoDBSettings


async def create_conversation_table():
    """Create the ConversationTable in DynamoDB Local"""

    settings = DynamoDBSettings()
    table_name = settings.table_name

    logger.info(f"Creating DynamoDB table: {table_name}")
    logger.info(f"Endpoint: {settings.endpoint_url}")

    session = aioboto3.Session(
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region
    )

    async with session.resource(
        "dynamodb",
        region_name=settings.region,
        endpoint_url=settings.endpoint_url
    ) as dynamodb:

        # Check if table already exists
        try:
            existing_tables = await dynamodb.meta.client.list_tables()
            if table_name in existing_tables.get("TableNames", []):
                logger.warning(f"Table '{table_name}' already exists")

                # Ask user if they want to delete and recreate
                response = input(f"Delete and recreate table '{table_name}'? (y/N): ")
                if response.lower() == 'y':
                    logger.info(f"Deleting existing table '{table_name}'...")
                    table = await dynamodb.Table(table_name)
                    await table.delete()

                    # Wait for table to be deleted
                    logger.info("Waiting for table deletion...")
                    await asyncio.sleep(5)
                else:
                    logger.info("Keeping existing table")
                    return
        except Exception as e:
            logger.error(f"Error checking existing tables: {e}")

        # Create table
        try:
            table = await dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        'AttributeName': 'pk',
                        'KeyType': 'HASH'  # Partition key
                    },
                    {
                        'AttributeName': 'sk',
                        'KeyType': 'RANGE'  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        'AttributeName': 'pk',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'sk',
                        'AttributeType': 'S'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'  # On-demand pricing (no need to specify throughput)
            )

            logger.success(f"Table '{table_name}' created successfully!")
            logger.info("Table schema:")
            logger.info("  Partition key (pk): USER#{user_id}")
            logger.info("  Sort key (sk): CONV#{conversation_id} or MSG#{conversation_id}#{message_id}")

        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(create_conversation_table())
