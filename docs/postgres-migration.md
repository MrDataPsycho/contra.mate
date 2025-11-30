# PostgreSQL Migration Guide

## Overview

This guide covers the migration from DynamoDB to PostgreSQL for storing conversations and messages. The migration was implemented to overcome DynamoDB's 400KB text field limitation, which can be restrictive for storing long conversation messages with large AI-generated responses.

**Version**: 1.0.0
**Date**: 2025-11-30
**Status**: Ready for Implementation

---

## Why Migrate to PostgreSQL?

### DynamoDB Limitations
- **400KB field size limit**: Text fields cannot exceed 400KB, which is problematic for:
  - Long AI-generated responses with citations
  - Conversations with extensive context
  - Messages containing code snippets or documentation
- **Costly for large text**: DynamoDB charges based on storage and throughput
- **Complex querying**: Limited query capabilities compared to SQL

### PostgreSQL Advantages
- **Unlimited text size**: TEXT field type supports messages of any size
- **Rich querying**: Full SQL support for complex queries and analytics
- **ACID compliance**: Strong consistency guarantees
- **Cost-effective**: Better pricing for text-heavy workloads
- **Relational model**: Natural fit for conversations → messages relationship

---

## Architecture Changes

### Before (DynamoDB)
```
Single Table Design:
├── PK: USER#user_id
└── SK: CONV#conversation_id  (conversations)
    └── SK: MSG#conversation_id#message_id  (messages)
```

### After (PostgreSQL)
```
Two-Table Design:
├── conversations
│   ├── id (UUID, primary key)
│   ├── user_id (indexed)
│   ├── title
│   ├── filter_values (JSON)
│   ├── is_active
│   ├── created_at
│   └── updated_at
│
└── messages
    ├── id (UUID, primary key)
    ├── conversation_id (foreign key → conversations.id)
    ├── user_id (indexed)
    ├── role (user/assistant)
    ├── content (TEXT - unlimited size!)
    ├── feedback
    ├── filter_values (JSON)
    ├── is_user_filter_text
    ├── metadata (JSON)
    ├── created_at
    └── updated_at
```

---

## Components

### 1. SQLModel Models
**Location**: `src/contramate/dbs/models/postgres_conversation.py`

**Key Features**:
- Type-safe models using SQLModel (Pydantic + SQLAlchemy)
- `Conversation` and `Message` tables
- TEXT field for message content (no size limit)
- JSON fields for flexible metadata storage
- UUID primary keys
- Automatic timestamp management

**Example**:
```python
from contramate.dbs.models import Conversation, Message

# Create a conversation
conversation = Conversation(
    user_id="user_123",
    title="Contract Analysis",
    filter_values={"documents": ["doc1.pdf"]},
)

# Create a message (supports unlimited text!)
message = Message(
    conversation_id=conversation.id,
    user_id="user_123",
    role="assistant",
    content="Very long AI response..." * 10000,  # No 400KB limit!
)
```

### 2. PostgreSQL Adapter
**Location**: `src/contramate/dbs/adapters/postgres_conversation_adapter.py`

**Key Features**:
- Implements same interface as DynamoDB adapter (`AbstractConversationRepository`)
- Drop-in replacement - no code changes needed in services
- Async support with SQLModel
- All DynamoDB methods preserved

**Example**:
```python
from contramate.dbs.adapters import PostgreSQLConversationAdapter
from contramate.dbs.postgres_db import get_db

# Initialize adapter
db = get_db()
adapter = PostgreSQLConversationAdapter(session_factory=db.get_session)

# Use exactly like DynamoDB adapter
conversation = await adapter.create_conversation(
    user_id="user_123",
    title="New Chat"
)

messages = await adapter.get_messages(
    user_id="user_123",
    conversation_id=conversation["conversation_id"]
)
```

### 3. Database Management
**Location**: `src/contramate/dbs/postgres_db.py`

**Key Features**:
- Async PostgreSQL engine
- Session factory for dependency injection
- Connection pooling
- Table creation/deletion utilities

**Example**:
```python
from contramate.dbs.postgres_db import init_db
from contramate.utils.settings.core import PostgresSettings

# Initialize database
settings = PostgresSettings()
db = init_db(settings)

# Create tables
await db.create_tables()

# Get session for operations
async with db.get_session() as session:
    # Use session here
    pass
```

### 4. Migration Script
**Location**: `src/tools/migrate_to_postgres.py`

**Capabilities**:
- Create PostgreSQL tables
- Migrate data from DynamoDB
- Validate migration integrity
- Preserve all IDs, timestamps, and metadata

---

## Migration Steps

### Prerequisites

1. **Update Environment Variables**

Add to your `.envs/local.env` or `.envs/docker.env`:

```bash
# PostgreSQL Settings (for conversations/messages)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=cuad_user
POSTGRES_PASSWORD=cuad_password
POSTGRES_DATABASE=cuad
POSTGRES_ECHO_SQL=false

# DynamoDB Settings (for migration source)
DYNAMODB_TABLE_NAME=contramate-conversations
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8001  # for local dev
DYNAMODB_ACCESS_KEY_ID=dummy
DYNAMODB_SECRET_ACCESS_KEY=dummy
```

2. **Install Dependencies**

All required dependencies (SQLModel, asyncpg) are already in `pyproject.toml`:
```bash
uv sync
```

### Step 1: Create PostgreSQL Tables

```bash
# Create tables only (no data migration)
uv run python -m tools.migrate_to_postgres --create-tables
```

This creates:
- `conversations` table
- `messages` table
- All indexes and constraints

### Step 2: Test with Sample Data

Before full migration, test with a sample conversation:

```python
from contramate.dbs.adapters import PostgreSQLConversationAdapter
from contramate.dbs.postgres_db import init_db, get_db
from contramate.utils.settings.core import PostgresSettings
import asyncio

async def test():
    # Initialize
    settings = PostgresSettings()
    db = init_db(settings)
    adapter = PostgreSQLConversationAdapter(session_factory=db.get_session)

    # Create test conversation
    conv = await adapter.create_conversation(
        user_id="test_user",
        title="Test Conversation"
    )

    # Create test message with large content
    msg = await adapter.create_message(
        user_id="test_user",
        conversation_id=conv["conversation_id"],
        role="assistant",
        content="A" * 500_000  # 500KB - would fail in DynamoDB!
    )

    print(f"✓ Created conversation: {conv['conversation_id']}")
    print(f"✓ Created message: {msg['messageId']}")
    print(f"✓ Message size: {len(msg['content'])} bytes")

asyncio.run(test())
```

### Step 3: Migrate Existing Data

**WARNING**: Review the migration script first! Update `get_all_user_ids()` if needed.

```bash
# Migrate all data from DynamoDB
uv run python -m tools.migrate_to_postgres --migrate-data
```

This will:
1. Scan DynamoDB for all user IDs
2. For each user:
   - Migrate all conversations
   - Migrate all messages
   - Preserve IDs and timestamps
3. Report summary and errors

### Step 4: Validate Migration

```bash
# Validate data integrity
uv run python -m tools.migrate_to_postgres --validate
```

This compares:
- Total conversation counts
- Total message counts
- Provides detailed report

### Step 5: Update Service Layer

Update the conversation service to use PostgreSQL adapter:

**Location**: `src/contramate/services/conversation_service.py`

```python
# Before (DynamoDB)
from contramate.dbs.adapters import DynamoDBConversationAdapter

# After (PostgreSQL)
from contramate.dbs.adapters import PostgreSQLConversationAdapter
from contramate.dbs.postgres_db import get_db

class ConversationService:
    def __init__(self):
        # Before
        # self.adapter = DynamoDBConversationAdapter(...)

        # After
        db = get_db()
        self.adapter = PostgreSQLConversationAdapter(
            session_factory=db.get_session
        )
```

### Step 6: Update FastAPI Lifespan

Add database initialization to your FastAPI app:

**Location**: `src/contramate/api/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from contramate.dbs.postgres_db import init_db
from contramate.utils.settings.core import PostgresSettings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = PostgresSettings()
    db = init_db(settings)
    await db.create_tables()  # Create if not exists

    yield

    # Shutdown
    await db.close()

app = FastAPI(lifespan=lifespan)
```

---

## Testing

### Unit Tests

```python
import pytest
from contramate.dbs.adapters import PostgreSQLConversationAdapter

@pytest.mark.asyncio
async def test_create_conversation(postgres_adapter):
    conv = await postgres_adapter.create_conversation(
        user_id="test_user",
        title="Test"
    )
    assert conv["userId"] == "test_user"
    assert "conversation_id" in conv

@pytest.mark.asyncio
async def test_large_message(postgres_adapter):
    """Test messages larger than DynamoDB's 400KB limit"""
    conv = await postgres_adapter.create_conversation(
        user_id="test_user",
        title="Large Message Test"
    )

    # Create 1MB message
    large_content = "A" * 1_000_000
    msg = await postgres_adapter.create_message(
        user_id="test_user",
        conversation_id=conv["conversation_id"],
        role="assistant",
        content=large_content
    )

    assert len(msg["content"]) == 1_000_000

    # Retrieve and verify
    messages = await postgres_adapter.get_messages(
        user_id="test_user",
        conversation_id=conv["conversation_id"]
    )
    assert len(messages[0]["content"]) == 1_000_000
```

### Integration Tests

```bash
# Run with test database
POSTGRES_DATABASE=cuad_test pytest tests/integration/test_postgres_adapter.py
```

---

## Rollback Plan

If issues occur, you can roll back:

### Option 1: Keep Both Systems Running

Run PostgreSQL and DynamoDB in parallel:
- Write to both databases
- Read from PostgreSQL (primary)
- Fall back to DynamoDB if PostgreSQL fails

```python
class HybridConversationService:
    def __init__(self):
        self.postgres_adapter = PostgreSQLConversationAdapter(...)
        self.dynamodb_adapter = DynamoDBConversationAdapter(...)

    async def get_messages(self, user_id, conversation_id):
        try:
            return await self.postgres_adapter.get_messages(user_id, conversation_id)
        except Exception as e:
            logger.warning(f"PostgreSQL failed: {e}, falling back to DynamoDB")
            return await self.dynamodb_adapter.get_messages(user_id, conversation_id)
```

### Option 2: Full Rollback

1. Update service to use DynamoDB adapter
2. Restart application
3. DynamoDB data is unchanged

---

## Performance Considerations

### Indexing
Ensure proper indexes are created:
```sql
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
```

### Connection Pooling
Configured in `postgres_db.py`:
```python
engine = create_async_engine(
    connection_string,
    pool_size=10,      # Adjust based on load
    max_overflow=20,   # Additional connections if needed
    pool_pre_ping=True # Verify connections before use
)
```

### Query Optimization
- Use pagination for large result sets
- Add `LIMIT` clauses to prevent memory issues
- Consider materialized views for analytics

---

## Monitoring

### Key Metrics to Track

1. **Database Size**
   ```sql
   SELECT pg_size_pretty(pg_database_size('cuad'));
   ```

2. **Table Sizes**
   ```sql
   SELECT
       tablename,
       pg_size_pretty(pg_total_relation_size(tablename::text))
   FROM pg_tables
   WHERE schemaname = 'public';
   ```

3. **Query Performance**
   ```sql
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;
   ```

4. **Connection Count**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

---

## Troubleshooting

### Common Issues

**Issue**: Migration fails with "table already exists"
**Solution**: Drop tables first or use `--create-tables` without migration

**Issue**: Slow migration for large datasets
**Solution**: Migrate in batches by user ID or date range

**Issue**: Connection pool exhausted
**Solution**: Increase `pool_size` and `max_overflow` in engine config

**Issue**: Messages still failing with size limits
**Solution**: Verify TEXT field type, not VARCHAR

---

## Future Enhancements

1. **Alembic Migrations**: Add proper schema versioning
2. **Read Replicas**: For scaling read operations
3. **Partitioning**: Partition messages table by date for better performance
4. **Full-Text Search**: Add PostgreSQL full-text search on message content
5. **Archival Strategy**: Move old conversations to cold storage

---

## References

- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [PostgreSQL TEXT Type](https://www.postgresql.org/docs/current/datatype-character.html)
- [AsyncPG Documentation](https://magicstack.github.io/asyncpg/)
- [DynamoDB Item Size Limits](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ServiceQuotas.html)

---

## Support

For issues or questions:
- Check logs in `/var/log/contramate/`
- Review error messages from migration script
- Consult database logs: `docker logs rag-postgres`

**Document Owner**: Development Team
**Review Cycle**: Quarterly
**Next Review**: 2026-02-28
