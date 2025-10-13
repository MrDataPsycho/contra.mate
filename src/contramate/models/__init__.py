"""
Domain models for document processing and vector storage.

Following DDD (Domain-Driven Design), this package contains:
- Document entities (Chunk, ChunkedDocument, EnrichedChunk, EnrichedDocument)
- Value objects (DocumentInfo)
- Vector models (VectorModel, VectorBatch)
- Enums (ContentSource)
"""

from contramate.models.document import (
    DocumentInfo,
    Chunk,
    ChunkedDocument,
    EnrichedChunk,
    EnrichedDocument,
)

from contramate.models.vector import (
    ContentSource,
    VectorModel,
)

from contramate.models.gold import (
    DocumentSource,
    GoldModel,
)

__all__ = [
    # Document models
    "DocumentInfo",
    "Chunk",
    "ChunkedDocument",
    "EnrichedChunk",
    "EnrichedDocument",
    # Vector models
    "ContentSource",
    "VectorModel",
    # Gold models
    "DocumentSource",
    "GoldModel",
]
