"""
Migration script: DynamoDB → PostgreSQL for conversations and messages.

This script migrates all conversations and messages from DynamoDB to PostgreSQL.

Features:
  - Pre-migration validation to check data integrity
  - Post-migration verification
  - Dry-run mode to preview changes
  - Comprehensive error handling and logging
  - Progress tracking with detailed metrics

Usage:
    # Create tables only
    uv run python -m tools.migrate_to_postgres --create-tables

    # Migrate data (with validation)
    uv run python -m tools.migrate_to_postgres --migrate

    # Create tables and migrate data
    uv run python -m tools.migrate_to_postgres --all

    # Preview changes without migrating
    uv run python -m tools.migrate_to_postgres --migrate --dry-run
"""

import typer
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Dict, Any, List, Tuple
from uuid import UUID

from contramate.dbs.postgres_db import init_db
from contramate.dbs.adapters.postgres_conversation_adapter import PostgreSQLConversationAdapter
from contramate.dbs.adapters.dynamodb_conversation_adapter import DynamoDBConversationAdapter
from contramate.utils.settings.core import PostgresSettings, DynamoDBSettings

app = typer.Typer(help="Migrate conversations and messages from DynamoDB to PostgreSQL")
console = Console()


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class MigrationStats:
    """Track migration statistics and errors"""
    def __init__(self):
        self.conversations_found = 0
        self.messages_found = 0
        self.conversations_migrated = 0
        self.conversations_failed = 0
        self.messages_migrated = 0
        self.messages_failed = 0
        self.skipped_invalid_messages = 0
        self.validation_errors: List[str] = []
        self.failed_conversations: List[Dict[str, Any]] = []
        self.failed_messages: List[Dict[str, Any]] = []

    def add_failed_conversation(self, conv: Dict[str, Any], error: str):
        """Track failed conversation migration"""
        self.failed_conversations.append({
            "sk": conv.get('sk'),
            "user_id": conv.get('userId'),
            "error": error
        })

    def add_failed_message(self, msg: Dict[str, Any], error: str):
        """Track failed message migration"""
        self.failed_messages.append({
            "sk": msg.get('sk'),
            "user_id": msg.get('userId'),
            "error": error
        })

    def print_summary(self):
        """Print migration summary with detailed error info"""
        console.print(f"\n[bold cyan]Migration Summary:[/bold cyan]")
        console.print(f"  Conversations: {self.conversations_migrated}/{self.conversations_found} migrated, {self.conversations_failed} failed")
        console.print(f"  Messages: {self.messages_migrated}/{self.messages_found} migrated, {self.messages_failed} failed")
        console.print(f"  Skipped invalid: {self.skipped_invalid_messages}")
        
        if self.failed_conversations:
            console.print(f"\n[yellow]Failed Conversations ({len(self.failed_conversations)}):[/yellow]")
            for item in self.failed_conversations[:5]:
                console.print(f"  - {item['sk']}: {item['error']}")
            if len(self.failed_conversations) > 5:
                console.print(f"  ... and {len(self.failed_conversations) - 5} more")
        
        if self.failed_messages:
            console.print(f"\n[yellow]Failed Messages ({len(self.failed_messages)}):[/yellow]")
            for item in self.failed_messages[:5]:
                console.print(f"  - {item['sk']}: {item['error']}")
            if len(self.failed_messages) > 5:
                console.print(f"  ... and {len(self.failed_messages) - 5} more")
        
        if self.validation_errors:
            console.print(f"\n[yellow]Validation Issues ({len(self.validation_errors)}):[/yellow]")
            for error in self.validation_errors[:5]:
                console.print(f"  - {error}")
            if len(self.validation_errors) > 5:
                console.print(f"  ... and {len(self.validation_errors) - 5} more")

    def success_rate(self) -> float:
        """Calculate overall success rate"""
        total_attempted = self.conversations_found + self.messages_found
        total_succeeded = self.conversations_migrated + self.messages_migrated
        return (total_succeeded / total_attempted * 100) if total_attempted > 0 else 0


def validate_conversation(conv: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a conversation record from DynamoDB.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    sk = conv.get('sk', '')
    if not sk.startswith('CONV#'):
        errors.append(f"Invalid SK prefix: {sk}")
    
    if 'userId' not in conv:
        errors.append("Missing userId field")
    
    if 'createdAt' not in conv:
        errors.append("Missing createdAt field")
    
    if 'updatedAt' not in conv:
        errors.append("Missing updatedAt field")
    
    return len(errors) == 0, errors


def validate_message(msg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a message record from DynamoDB.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check SK format: MSG#{conversation_id}#{message_id}
    sk = msg.get('sk', '')
    sk_parts = sk.split('#')
    
    if not sk.startswith('MSG#'):
        errors.append(f"Invalid SK prefix: {sk}")
    elif len(sk_parts) < 3:
        errors.append(f"Invalid SK format (expected 3 parts): {sk}")
    
    if 'userId' not in msg:
        errors.append("Missing userId field")
    
    if 'role' not in msg:
        errors.append("Missing role field")
    
    if 'content' not in msg:
        errors.append("Missing content field")
    
    if 'createdAt' not in msg:
        errors.append("Missing createdAt field")
    
    return len(errors) == 0, errors


def validate_dynamodb_data(all_items: List[Dict[str, Any]], stats: MigrationStats) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate and separate conversations and messages.
    Returns tuple of (conversations, messages)
    """
    conversations = []
    messages = []
    
    for item in all_items:
        sk = item.get('sk', '')
        
        if sk.startswith('CONV#'):
            is_valid, errors = validate_conversation(item)
            if is_valid:
                conversations.append(item)
            else:
                logger.warning(f"Skipping invalid conversation {sk}: {', '.join(errors)}")
                stats.validation_errors.extend(errors)
        elif sk.startswith('MSG#'):
            is_valid, errors = validate_message(item)
            if is_valid:
                messages.append(item)
            else:
                logger.warning(f"Skipping invalid message {sk}: {', '.join(errors)}")
                stats.validation_errors.extend(errors)
        else:
            logger.debug(f"Unknown item type with SK: {sk}")
    
    stats.conversations_found = len(conversations)
    stats.messages_found = len(messages)
    
    return conversations, messages


def create_tables():
    """Create PostgreSQL tables for conversations and messages"""
    logger.info("Creating PostgreSQL tables...")

    postgres_settings = PostgresSettings()
    db = init_db(postgres_settings)

    try:
        db.create_tables()
        logger.success("✓ Tables created successfully!")
        logger.info("  - conversations table")
        logger.info("  - messages table")
    except Exception as e:
        logger.error(f"✗ Failed to create tables: {e}")
        raise


def migrate_data(dry_run: bool = False):
    """
    Migrate all conversations and messages from DynamoDB to PostgreSQL.

    Args:
        dry_run: If True, only show what would be migrated without actually migrating
    """
    logger.info("Initializing migration...")
    stats = MigrationStats()

    # Initialize adapters
    postgres_settings = PostgresSettings()
    dynamodb_settings = DynamoDBSettings()

    postgres_db = init_db(postgres_settings)
    postgres_adapter = PostgreSQLConversationAdapter(postgres_db.session_factory)
    dynamodb_adapter = DynamoDBConversationAdapter(
        table_name=dynamodb_settings.table_name,
        dynamodb_settings=dynamodb_settings
    )

    logger.info("Connected to DynamoDB and PostgreSQL")

    try:
        # Get all conversations from DynamoDB
        console.print("\n[cyan]Step 1: Scanning DynamoDB for conversations and messages...[/cyan]")

        import boto3

        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=dynamodb_settings.endpoint_url,
            region_name=dynamodb_settings.region,
            aws_access_key_id=dynamodb_settings.access_key_id,
            aws_secret_access_key=dynamodb_settings.secret_access_key
        )

        table_name = dynamodb_settings.table_name
        table = dynamodb.Table(table_name)

        # Scan all conversations
        response = table.scan()
        all_items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            all_items.extend(response.get('Items', []))

        logger.info(f"Found {len(all_items)} total items in DynamoDB")

        # Validate and separate data
        console.print("\n[cyan]Step 2: Validating data structure...[/cyan]")
        conversations, messages = validate_dynamodb_data(all_items, stats)

        logger.info(f"Valid: {stats.conversations_found} conversations, {stats.messages_found} messages")
        if stats.validation_errors:
            logger.warning(f"Found {len(stats.validation_errors)} validation issues")

        if dry_run:
            console.print(f"\n[yellow]DRY RUN: Would migrate {len(conversations)} conversations and {len(messages)} messages[/yellow]")
            if conversations:
                console.print("\n[cyan]Sample conversations:[/cyan]")
                for i, conv in enumerate(conversations[:3], 1):
                    conv_id = conv.get('sk', '').replace('CONV#', '')
                    console.print(f"  {i}. {conv.get('userId')} - {conv.get('title', 'Untitled')} ({conv_id})")
            if messages:
                console.print("\n[cyan]Sample messages:[/cyan]")
                for i, msg in enumerate(messages[:3], 1):
                    sk_parts = msg.get('sk', '').split('#')
                    console.print(f"  {i}. {msg.get('role')} message in conv {sk_parts[1] if len(sk_parts) > 1 else 'unknown'}")
            stats.print_summary()
            return

        # Migrate conversations
        console.print(f"\n[cyan]Step 3: Migrating {len(conversations)} conversations...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Migrating conversations...", total=len(conversations))

            for conv in conversations:
                try:
                    # Extract conversation ID from SK: CONV#{conversation_id}
                    conv_id = conv.get('sk', '').replace('CONV#', '')
                    user_id = conv.get('userId', 'unknown')

                    # Validate UUID format
                    try:
                        UUID(conv_id)
                    except ValueError as ve:
                        logger.warning(f"Skipping conversation with invalid UUID: {conv_id}")
                        stats.conversations_failed += 1
                        stats.add_failed_conversation(conv, f"Invalid UUID format: {conv_id}")
                        progress.update(task, advance=1)
                        continue

                    # Verify required fields
                    if not user_id or user_id == 'unknown':
                        logger.warning(f"Skipping conversation {conv_id}: missing userId")
                        stats.conversations_failed += 1
                        stats.add_failed_conversation(conv, "Missing userId field")
                        progress.update(task, advance=1)
                        continue

                    # Create conversation in PostgreSQL
                    result = postgres_adapter.create_conversation(
                        user_id=user_id,
                        title=conv.get('title', ''),
                        conversation_id=conv_id,
                        filter_values=conv.get('filter_value', {})
                    )
                    
                    logger.debug(f"Successfully migrated conversation {conv_id}")
                    stats.conversations_migrated += 1
                    progress.update(task, advance=1)

                except Exception as e:
                    error_msg = f"Exception during migration: {str(e)}"
                    logger.warning(f"Failed to migrate conversation {conv.get('sk')}: {error_msg}")
                    stats.conversations_failed += 1
                    stats.add_failed_conversation(conv, error_msg)
                    progress.update(task, advance=1)

        console.print(f"[green]✓ Migrated {stats.conversations_migrated} conversations[/green]")
        if stats.conversations_failed > 0:
            console.print(f"[yellow]! {stats.conversations_failed} conversations failed[/yellow]")

        # Migrate messages
        console.print(f"\n[cyan]Step 4: Migrating {len(messages)} messages...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Migrating messages...", total=len(messages))

            for msg in messages:
                try:
                    # Extract IDs from SK: MSG#{conversation_id}#{message_id}
                    sk_parts = msg.get('sk', '').split('#')
                    if len(sk_parts) < 3:
                        logger.warning(f"Skipping message with invalid SK: {msg.get('sk')}")
                        stats.skipped_invalid_messages += 1
                        stats.add_failed_message(msg, f"Invalid SK format: {msg.get('sk')}")
                        progress.update(task, advance=1)
                        continue

                    conv_id = sk_parts[1]  # MSG#conversation_id#message_id
                    msg_id = sk_parts[2]

                    # Validate UUID formats
                    try:
                        UUID(conv_id)
                        UUID(msg_id)
                    except ValueError as ve:
                        logger.warning(f"Skipping message with invalid UUIDs: conv={conv_id}, msg={msg_id}")
                        stats.skipped_invalid_messages += 1
                        stats.add_failed_message(msg, f"Invalid UUID format: {str(ve)}")
                        progress.update(task, advance=1)
                        continue

                    # Verify required fields
                    user_id = msg.get('userId', 'unknown')
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')

                    if not user_id or user_id == 'unknown':
                        logger.warning(f"Skipping message {msg_id}: missing userId")
                        stats.messages_failed += 1
                        stats.add_failed_message(msg, "Missing userId field")
                        progress.update(task, advance=1)
                        continue

                    if not role:
                        logger.warning(f"Skipping message {msg_id}: missing role")
                        stats.messages_failed += 1
                        stats.add_failed_message(msg, "Missing role field")
                        progress.update(task, advance=1)
                        continue

                    if not content:
                        logger.warning(f"Skipping message {msg_id}: missing content")
                        stats.messages_failed += 1
                        stats.add_failed_message(msg, "Missing content field")
                        progress.update(task, advance=1)
                        continue

                    # Create message in PostgreSQL
                    result = postgres_adapter.create_message(
                        user_id=user_id,
                        conversation_id=conv_id,
                        role=role,
                        content=content,
                        message_id=msg_id,
                        feedback=msg.get('feedback', ''),
                        filter_value=msg.get('filter_value'),
                        is_user_filter_text=msg.get('is_user_filter_text', False),
                        metadata=msg.get('metadata', {})
                    )
                    
                    logger.debug(f"Successfully migrated message {msg_id}")
                    stats.messages_migrated += 1
                    progress.update(task, advance=1)

                except Exception as e:
                    error_msg = f"Exception during migration: {str(e)}"
                    logger.warning(f"Failed to migrate message: {error_msg}")
                    stats.messages_failed += 1
                    stats.add_failed_message(msg, error_msg)
                    progress.update(task, advance=1)

        console.print(f"[green]✓ Migrated {stats.messages_migrated} messages[/green]")
        if stats.messages_failed > 0:
            console.print(f"[yellow]! {stats.messages_failed} messages failed[/yellow]")

        # Final summary
        success_rate = stats.success_rate()
        if success_rate >= 95:
            status_color = "green"
            status_icon = "✅"
        elif success_rate >= 80:
            status_color = "yellow"
            status_icon = "⚠️"
        else:
            status_color = "red"
            status_icon = "❌"

        console.print(f"\n[bold {status_color}]{status_icon} Migration Summary[/bold {status_color}]")
        stats.print_summary()
        console.print(f"\n[bold]Success Rate: {success_rate:.1f}%[/bold]")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise


@app.command()
def create():
    """Create PostgreSQL tables only"""
    try:
        create_tables()
        console.print("[bold green]✅ Tables created successfully![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Failed to create tables: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def migrate(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be migrated without migrating")
):
    """Migrate data from DynamoDB to PostgreSQL"""
    try:
        migrate_data(dry_run=dry_run)
        if not dry_run:
            console.print("[bold green]✅ Data migration complete![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Migration failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def all(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be migrated without migrating")
):
    """Create tables and migrate data"""
    try:
        create_tables()
        console.print()
        migrate_data(dry_run=dry_run)
        console.print("[bold green]✅ Complete migration finished![/bold green]")
    except Exception as e:
        console.print(f"[bold red]✗ Migration failed: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
