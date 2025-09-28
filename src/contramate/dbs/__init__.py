"""Database package for Contramate

This package contains:
- adapters: Database adapter implementations (DynamoDB, PostgreSQL, etc.)
- interfaces: Abstract base classes for database operations
- models: Data models and types
"""

# Import from adapters package
from contramate.dbs.adapters import DynamoDBConversationAdapter

# Import from models package  
from contramate.dbs.models import FeedbackType

__all__ = [
    "DynamoDBConversationAdapter",
    "FeedbackType",
]