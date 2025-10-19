"""
Domain models for document processing and vector storage.

Following DDD (Domain-Driven Design), this package contains:
- Document entities (Chunk, ChunkedDocument, EnrichedChunk, EnrichedDocument)
- Value objects (DocumentInfo)
- Vector models (VectorModel, GoldModel)
- Filter models (DocumentFilter, OpenSearchFilter)
- Enums (ContentSource, DocumentSource)
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

from contramate.models.filters import (
    DocumentFilter,
    OpenSearchFilter,
)

__all__ = [
    "DocumentInfo",
    "Chunk",
    "ChunkedDocument",
    "EnrichedChunk",
    "EnrichedDocument",
    "ContentSource",
    "VectorModel",
    "DocumentSource",
    "GoldModel",
    "DocumentFilter",
    "OpenSearchFilter",
]
