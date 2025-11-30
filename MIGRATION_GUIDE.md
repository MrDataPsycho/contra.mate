# DynamoDB to PostgreSQL Migration Guide

## Overview

This guide covers migrating conversation and message data from DynamoDB to PostgreSQL using the `migrate_to_postgres.py` script.

**Script Location:** `src/tools/migrate_to_postgres.py`

## Quick Start

### 1. Preview Changes (No Risk)
```bash
uv run python -m tools.migrate_to_postgres --migrate --dry-run
```
Shows what will be migrated without making changes. Perfect for validation before actual migration.

### 2. Create Tables
```bash
uv run python -m tools.migrate_to_postgres --create-tables
```
Initializes PostgreSQL with `conversations` and `messages` tables.

### 3. Run Migration
```bash
uv run python -m tools.migrate_to_postgres --migrate
```
Performs full migration with validation and error handling.

### 4. One-Step Setup
```bash
uv run python -m tools.migrate_to_postgres --all
```
Creates tables and migrates data in one command.

## Features

### Data Validation
- ✅ SK format validation (`CONV#`, `MSG#`)
- ✅ UUID format validation for IDs
- ✅ Required field verification
- ✅ Pre-migration validation report

### Error Handling
- ✅ Validates before migrating (no surprises)
- ✅ Continues on individual record failures
- ✅ Detailed error reporting per record
- ✅ Success rate calculation

### Progress Tracking
- ✅ Real-time progress bars
- ✅ Step-by-step output
- ✅ Color-coded results
- ✅ Comprehensive summary

## Command Reference

### Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--create-tables` | Create PostgreSQL schema only | `--create-tables` |
| `--migrate` | Migrate data from DynamoDB | `--migrate` |
| `--dry-run` | Preview without making changes | `--migrate --dry-run` |
| `--all` | Create tables + migrate | `--all` |

### Full Command Examples

**Preview migration (recommended first step):**
```bash
uv run python -m tools.migrate_to_postgres --migrate --dry-run
```

**Fresh deployment (create + migrate):**
```bash
uv run python -m tools.migrate_to_postgres --all
```

**Just initialize tables:**
```bash
uv run python -m tools.migrate_to_postgres --create-tables
```

**Migrate existing tables:**
```bash
uv run python -m tools.migrate_to_postgres --migrate
```

## Output Examples

### Dry-Run Output
```
[cyan]Step 1: Scanning DynamoDB for conversations and messages...[/cyan]
Found 250 total items in DynamoDB

[cyan]Step 2: Validating data structure...[/cyan]
Valid: 45 conversations, 230 messages
Found 3 validation issues

[yellow]DRY RUN: Would migrate 45 conversations and 230 messages[/yellow]

Sample conversations:
  1. user123 - Contract Review Session (conv-uuid-1)
  2. user123 - Clause Analysis (conv-uuid-2)

Sample messages:
  1. user message in conv conv-uuid-1
  2. assistant message in conv conv-uuid-1

Migration Summary:
  Conversations: 45 found, 0 validation issues
  Messages: 230 found, 0 validation issues
  Success Rate: 100.0%
```

### Migration Output
```
[cyan]Step 3: Migrating 45 conversations...[/cyan]
⠋ Migrating conversations...
[green]✓ Migrated 44 conversations[/green]
[yellow]! 1 conversation failed[/yellow]

[cyan]Step 4: Migrating 230 messages...[/cyan]
⠋ Migrating messages...
[green]✓ Migrated 228 messages[/green]
[yellow]! 2 messages failed[/yellow]

[bold green]✅ Migration Summary[/bold green]
  Conversations: 44/45 migrated, 1 failed
  Messages: 228/230 migrated, 2 failed
  Skipped invalid: 2

Failed Conversations (1):
  - CONV#invalid-uuid: Invalid UUID format: not-a-uuid

Failed Messages (2):
  - MSG#conv-uuid#msg-id: Missing userId field

Success Rate: 98.7%
```

## Troubleshooting

### Issue: "Cannot do operations on a non-existent table"
**Solution:** Run `--create-tables` first
```bash
uv run python -m tools.migrate_to_postgres --create-tables
```

### Issue: "Connection refused" on PostgreSQL
**Solution:** Ensure PostgreSQL is running
```bash
# Via Docker
docker-compose up postgres

# Via local installation
psql -U postgres  # Test connection
```

### Issue: "Cannot connect to DynamoDB"
**Solution:** Check DynamoDB Local is running
```bash
# Via Docker
docker-compose up dynamodb

# Or ensure endpoint_url is correct in settings
```

### Issue: "Invalid table name" error
**Solution:** Verify `DynamoDBSettings` has correct `table_name`
- Default: `ConversationTable`
- Check: `DYNAMODB_TABLE_NAME` environment variable

### Issue: High failure rate (>5% failures)
**Solution:** 
1. Check validation errors reported
2. Review DynamoDB data format
3. Run with increased logging: `export RUST_LOG=debug`

## Data Validation Details

### Conversation Validation
- ✅ SK starts with `CONV#`
- ✅ Conversation ID is valid UUID
- ✅ `userId` field exists
- ✅ `createdAt` and `updatedAt` present

**Example valid item:**
```json
{
  "pk": "USER#user123",
  "sk": "CONV#550e8400-e29b-41d4-a716-446655440000",
  "userId": "user123",
  "title": "My Conversation",
  "createdAt": "2025-11-30T10:00:00Z",
  "updatedAt": "2025-11-30T10:00:00Z"
}
```

### Message Validation
- ✅ SK format: `MSG#{conversation_id}#{message_id}`
- ✅ Both IDs are valid UUIDs
- ✅ `userId`, `role`, `content` fields exist
- ✅ `createdAt` and `updatedAt` present

**Example valid item:**
```json
{
  "pk": "USER#user123",
  "sk": "MSG#550e8400-e29b-41d4-a716-446655440000#660e8400-e29b-41d4-a716-446655440001",
  "userId": "user123",
  "role": "user",
  "content": "What are the payment terms?",
  "createdAt": "2025-11-30T10:01:00Z",
  "updatedAt": "2025-11-30T10:01:00Z"
}
```

## Performance Expectations

- **Scan time:** ~10-30 seconds for 1000 items
- **Validation time:** ~5 seconds for 1000 items
- **Migration rate:** ~100-200 items/second
- **Total time:** ~1-2 minutes for typical dataset

## PostgreSQL Table Schemas

### conversations
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  title VARCHAR(500),
  filter_values JSONB,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### messages
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id),
  user_id VARCHAR(255) NOT NULL,
  role VARCHAR(50),
  content TEXT,
  feedback VARCHAR(50),
  filter_values JSONB,
  is_user_filter_text BOOLEAN DEFAULT false,
  msg_metadata JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

## Best Practices

1. **Always dry-run first**
   ```bash
   uv run python -m tools.migrate_to_postgres --migrate --dry-run
   ```

2. **Review validation errors**
   - Check if any validation issues are expected
   - Understand why records might fail

3. **Backup before migration**
   ```bash
   # DynamoDB backup
   aws dynamodb create-backup --table-name ConversationTable --backup-name pre-migration-backup
   ```

4. **Verify after migration**
   ```bash
   # Count records in PostgreSQL
   psql -c "SELECT COUNT(*) FROM conversations; SELECT COUNT(*) FROM messages;"
   ```

5. **Keep DynamoDB as fallback**
   - Keep DynamoDB running during transition
   - Switch application gradually
   - Monitor for issues before cleanup

## Post-Migration Steps

1. **Verify record counts**
   ```bash
   # DynamoDB count
   uv run python -c "
   import boto3
   from contramate.utils.settings.core import DynamoDBSettings
   settings = DynamoDBSettings()
   dynamodb = boto3.resource('dynamodb', endpoint_url=settings.endpoint_url)
   table = dynamodb.Table(settings.table_name)
   response = table.scan()
   print(f'DynamoDB items: {len(response[\"Items\"])}')
   "
   
   # PostgreSQL count
   uv run python -c "
   from contramate.dbs.postgres_db import init_db
   from contramate.utils.settings.core import PostgresSettings
   from sqlmodel import select, Session
   from contramate.dbs.models import Conversation, Message
   
   db = init_db(PostgresSettings())
   with db.session_factory() as session:
       convs = session.query(Conversation).count()
       msgs = session.query(Message).count()
       print(f'PostgreSQL: {convs} conversations, {msgs} messages')
   "
   ```

2. **Compare sample records**
   - Pick random DynamoDB records
   - Verify they exist in PostgreSQL
   - Check field values match

3. **Update application configuration**
   - Switch from DynamoDB to PostgreSQL adapter
   - Update `get_conversation_service()` dependency
   - Test all conversation endpoints

4. **Monitor logs**
   - Watch for any adapter-related errors
   - Verify message persistence works
   - Check response times

5. **Archive DynamoDB**
   - Keep backup for 30 days
   - Export to S3 if needed
   - Eventually remove from docker-compose

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review migration output logs
3. Check PostgreSQL and DynamoDB connectivity
4. Examine validation errors for data issues
