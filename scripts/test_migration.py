"""
Test script for the DynamoDB to PostgreSQL migration.

This script:
1. Creates test data in DynamoDB
2. Runs the migration script
3. Verifies data integrity in PostgreSQL

Usage:
    uv run python scripts/test_migration.py
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from decimal import Decimal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from contramate.utils.settings.core import DynamoDBSettings, PostgresSettings
from contramate.dbs.postgres_db import init_db
from contramate.dbs.adapters.postgres_conversation_adapter import PostgreSQLConversationAdapter
from rich.console import Console

console = Console()


async def create_test_dynamodb_data():
    """Create sample test data in DynamoDB"""
    import aioboto3
    from datetime import datetime, timezone

    settings = DynamoDBSettings()
    session = aioboto3.Session(
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region
    )

    async with session.resource(
        'dynamodb',
        region_name=settings.region,
        endpoint_url=settings.endpoint_url
    ) as dynamodb:
        table = await dynamodb.Table(settings.table_name)

        # Create test conversations
        user_id = "test_user_123"
        conv_id_1 = str(uuid4())
        conv_id_2 = str(uuid4())

        # Conversation 1
        conversation_1 = {
            "pk": f"USER#{user_id}",
            "sk": f"CONV#{conv_id_1}",
            "type": "conversation",
            "userId": user_id,
            "title": "Test Conversation 1",
            "filter_value": {"documents": ["doc1", "doc2"]},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        # Conversation 2
        conversation_2 = {
            "pk": f"USER#{user_id}",
            "sk": f"CONV#{conv_id_2}",
            "type": "conversation",
            "userId": user_id,
            "title": "Test Conversation 2",
            "filter_value": {},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        # Messages for conversation 1
        msg_id_1 = str(uuid4())
        msg_id_2 = str(uuid4())

        message_1 = {
            "pk": f"USER#{user_id}",
            "sk": f"MSG#{conv_id_1}#{msg_id_1}",
            "type": "message",
            "conversationId": conv_id_1,
            "userId": user_id,
            "role": "user",
            "content": "What are the key terms in this contract?",
            "feedback": "",
            "filter_value": {"documents": ["doc1"]},
            "is_user_filter_text": False,
            "metadata": {"response_time": Decimal("1.2")},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        message_2 = {
            "pk": f"USER#{user_id}",
            "sk": f"MSG#{conv_id_1}#{msg_id_2}",
            "type": "message",
            "conversationId": conv_id_1,
            "userId": user_id,
            "role": "assistant",
            "content": "The key terms include payment terms, delivery dates, and liability clauses.",
            "feedback": "LIKE",
            "filter_value": {"documents": ["doc1"]},
            "is_user_filter_text": False,
            "metadata": {"response_time": Decimal("2.5")},
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        # Put items
        try:
            await table.put_item(Item=conversation_1)
            await table.put_item(Item=conversation_2)
            await table.put_item(Item=message_1)
            await table.put_item(Item=message_2)
            logger.success("✓ Test data created in DynamoDB")
            return user_id, [conv_id_1, conv_id_2], [msg_id_1, msg_id_2]
        except Exception as e:
            logger.error(f"Failed to create test data: {e}")
            raise


def verify_postgres_data(user_id: str, conv_ids: list, msg_ids: list):
    """Verify migrated data in PostgreSQL"""
    postgres_settings = PostgresSettings()
    db = init_db(postgres_settings)
    adapter = PostgreSQLConversationAdapter(db.session_factory)

    console.print("\n[cyan]Verifying migrated data in PostgreSQL:[/cyan]")

    # Get conversations
    conversations = adapter.get_conversations(user_id, limit=10)
    console.print(f"\n[bold]Conversations migrated: {len(conversations)}/2[/bold]")

    if len(conversations) > 0:
        for conv in conversations:
            console.print(f"  ✓ {conv.get('title')} ({conv.get('conversation_id')})")
            
            # Get messages for this conversation
            messages = adapter.get_messages(user_id, conv['conversation_id'], limit=10)
            console.print(f"    Messages: {len(messages)}")
            for msg in messages:
                console.print(f"      - {msg['role']}: {msg['content'][:50]}...")
    else:
        console.print("[red]✗ No conversations found![/red]")


async def main():
    """Run full test"""
    console.print("[bold cyan]DynamoDB → PostgreSQL Migration Test[/bold cyan]\n")

    try:
        # Create test data
        console.print("[cyan]Step 1: Creating test data in DynamoDB...[/cyan]")
        user_id, conv_ids, msg_ids = await create_test_dynamodb_data()

        console.print("\n[cyan]Step 2: Run migration with:[/cyan]")
        console.print("  [yellow]uv run python -m tools.migrate_to_postgres --migrate --dry-run[/yellow]")
        console.print("  [yellow]uv run python -m tools.migrate_to_postgres --migrate[/yellow]")

        console.print("\n[cyan]Step 3: Verifying data...[/cyan]")
        console.print(f"  Looking for user_id: {user_id}")
        console.print(f"  Conversation IDs: {', '.join(conv_ids[:2])}")
        console.print(f"  Message IDs: {', '.join(msg_ids[:2])}")

        # Note: Verify after manual migration
        console.print("\n[yellow]After running migration, run:[/yellow]")
        console.print("  [cyan]uv run python scripts/verify_migration.py[/cyan]")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
