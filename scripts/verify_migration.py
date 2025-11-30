"""
Verification script to check migration results.

This script compares DynamoDB and PostgreSQL data to verify migration integrity.

Usage:
    uv run python scripts/verify_migration.py [user_id]
"""

import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from contramate.utils.settings.core import DynamoDBSettings, PostgresSettings
from contramate.dbs.postgres_db import init_db
from contramate.dbs.adapters.postgres_conversation_adapter import PostgreSQLConversationAdapter

app = typer.Typer(help="Verify DynamoDB → PostgreSQL migration")
console = Console()


def get_dynamodb_data(user_id: str) -> tuple[list, list]:
    """Get data from DynamoDB"""
    import boto3

    settings = DynamoDBSettings()
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=settings.endpoint_url,
        region_name=settings.region,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key
    )

    table = dynamodb.Table(settings.table_name)

    # Query conversations
    response = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
        ExpressionAttributeValues={
            ":pk": f"USER#{user_id}",
            ":sk": "CONV#",
        }
    )
    conversations = response.get("Items", [])

    # Query messages
    response = table.query(
        KeyConditionExpression="pk = :pk AND begins_with(sk, :msg_prefix)",
        ExpressionAttributeValues={
            ":pk": f"USER#{user_id}",
            ":msg_prefix": "MSG#",
        },
        Limit=100
    )
    messages = response.get("Items", [])

    return conversations, messages


def get_postgres_data(user_id: str) -> tuple[list, list]:
    """Get data from PostgreSQL"""
    postgres_settings = PostgresSettings()
    db = init_db(postgres_settings)
    adapter = PostgreSQLConversationAdapter(db.session_factory)

    conversations = adapter.get_conversations(user_id, limit=100)
    
    # Get all messages
    all_messages = []
    for conv in conversations:
        messages = adapter.get_messages(user_id, conv['conversation_id'], limit=100)
        all_messages.extend(messages)

    return conversations, all_messages


@app.command()
def verify(user_id: str = typer.Argument("test_user_123", help="User ID to verify")):
    """Verify migration for a specific user"""
    console.print(f"\n[bold cyan]Verification Report for User: {user_id}[/bold cyan]\n")

    try:
        # Get DynamoDB data
        console.print("[cyan]Reading DynamoDB data...[/cyan]")
        ddb_conversations, ddb_messages = get_dynamodb_data(user_id)
        console.print(f"  Found {len(ddb_conversations)} conversations, {len(ddb_messages)} messages\n")

        # Get PostgreSQL data
        console.print("[cyan]Reading PostgreSQL data...[/cyan]")
        pg_conversations, pg_messages = get_postgres_data(user_id)
        console.print(f"  Found {len(pg_conversations)} conversations, {len(pg_messages)} messages\n")

        # Create comparison tables
        console.print("[bold cyan]Conversation Comparison:[/bold cyan]")
        conv_table = Table(title="Conversations")
        conv_table.add_column("Field", style="cyan")
        conv_table.add_column("DynamoDB", style="yellow")
        conv_table.add_column("PostgreSQL", style="green")

        conv_table.add_row("Count", str(len(ddb_conversations)), str(len(pg_conversations)))
        console.print(conv_table)

        console.print("\n[bold cyan]Message Comparison:[/bold cyan]")
        msg_table = Table(title="Messages")
        msg_table.add_column("Field", style="cyan")
        msg_table.add_column("DynamoDB", style="yellow")
        msg_table.add_column("PostgreSQL", style="green")

        msg_table.add_row("Count", str(len(ddb_messages)), str(len(pg_messages)))
        console.print(msg_table)

        # Detailed checks
        console.print("\n[bold cyan]Detailed Verification:[/bold cyan]")

        success = True

        # Check conversation count
        if len(ddb_conversations) == len(pg_conversations):
            console.print("[green]✓[/green] Conversation count matches")
        else:
            console.print(f"[red]✗[/red] Conversation count mismatch: DDB={len(ddb_conversations)}, PG={len(pg_conversations)}")
            success = False

        # Check message count
        if len(ddb_messages) == len(pg_messages):
            console.print("[green]✓[/green] Message count matches")
        else:
            console.print(f"[red]✗[/red] Message count mismatch: DDB={len(ddb_messages)}, PG={len(pg_messages)}")
            success = False

        # Sample data verification
        if ddb_conversations and pg_conversations:
            sample_ddb_conv = ddb_conversations[0]
            sample_pg_conv = pg_conversations[0]

            console.print("\n[cyan]Sample Conversation Data:[/cyan]")
            console.print(f"  DDB title: {sample_ddb_conv.get('title')}")
            console.print(f"  PG title: {sample_pg_conv.get('title')}")

            if sample_ddb_conv.get('title') == sample_pg_conv.get('title'):
                console.print("[green]✓[/green] Sample conversation title matches")
            else:
                console.print("[yellow]⚠[/yellow] Sample conversation title differs")
                success = False

        # Final result
        console.print("\n[bold]=" * 50 + "[/bold]")
        if success and len(ddb_conversations) > 0 and len(ddb_messages) > 0:
            console.print("[bold green]✅ Migration verification PASSED[/bold green]")
            console.print(f"   All {len(ddb_conversations)} conversations and {len(ddb_messages)} messages successfully migrated!")
        elif len(ddb_conversations) == 0:
            console.print("[yellow]⚠ No data found to verify[/yellow]")
            console.print("   Run: uv run python scripts/test_migration.py")
            console.print("   Then: uv run python -m tools.migrate_to_postgres --migrate")
        else:
            console.print("[red]❌ Migration verification FAILED[/red]")
            console.print("   Please check error logs above")

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
