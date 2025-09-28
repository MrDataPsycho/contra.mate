#!/usr/bin/env python3
"""
Import Examples - Following CLAUDE.md Guidelines

This script demonstrates the proper import patterns for the Contramate project.
"""

print("📚 Contramate Import Guidelines Examples")
print("=" * 50)

print("\n✅ CORRECT: Package-level imports (preferred)")
print("from contramate.dbs import DynamoDBConversationAdapter, FeedbackType")
print("from contramate.services import ConversationService")

from contramate.dbs import DynamoDBConversationAdapter, FeedbackType
from contramate.services import ConversationService

print("\n✅ CORRECT: Sub-package imports")
print("from contramate.dbs.adapters import DynamoDBConversationAdapter")
print("from contramate.dbs.models import FeedbackType")

from contramate.dbs.adapters import DynamoDBConversationAdapter as AdapterAlt
from contramate.dbs.models import FeedbackType as FeedbackAlt

print("\n✅ CORRECT: Direct interface imports (interfaces not re-imported)")
print("from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository")

from contramate.dbs.interfaces.conversation_store import AbstractConversationRepository

print("\n❌ INCORRECT: Relative imports (never use these)")
print("# from .adapters import DynamoDBConversationAdapter  # DON'T DO THIS")
print("# from ..models import FeedbackType                  # DON'T DO THIS")

print("\n🏗️ Usage Examples:")
print("-" * 20)

# Initialize service using package import
service = ConversationService(table_name="example")
print(f"✅ Service initialized: {type(service).__name__}")

# Initialize adapter using package import  
adapter = DynamoDBConversationAdapter(table_name="example")
print(f"✅ Adapter initialized: {type(adapter).__name__}")

# Use feedback enum
feedback = FeedbackType.LIKE
print(f"✅ Feedback enum: {feedback.name} = {feedback.value}")

print(f"\n🎉 All imports following CLAUDE.md guidelines!")

print("\n📋 Summary of Guidelines:")
print("1. ❌ No relative imports - always use 'contramate' as root")
print("2. ✅ Re-import modules in package-level __init__.py files")
print("3. ✅ Import from packages when possible (contramate.dbs vs contramate.dbs.adapters)")
print("4. ✅ Interfaces imported directly (not re-imported in __init__.py)")
print("5. ✅ Use absolute imports from contramate root package")