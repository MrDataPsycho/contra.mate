"""Database package for Contramate

This package contains:
- adapters: Database adapter implementations (DynamoDB, PostgreSQL, etc.)
- interfaces: Abstract base classes for database operations
- models: Data models and types
"""

# Only import models by default to avoid triggering settings initialization
# Adapters should be imported explicitly when needed:
#   from contramate.dbs.adapters import DynamoDBConversationAdapter

from contramate.dbs.models import (
    FeedbackType,
    ContractAsmd,
    ProcessingStatus,
    DocumentConversionStatus,
    DocumentChunkingStatus,
    DocumentIndexingStatus,
)

__all__ = [
    "FeedbackType",
    "ContractAsmd",
    "ProcessingStatus",
    "DocumentConversionStatus",
    "DocumentChunkingStatus",
    "DocumentIndexingStatus",
]