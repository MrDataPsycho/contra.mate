"""
Document domain models following DDD principles.

These models represent the core domain entities for document processing:
- DocumentInfo: Value object containing document metadata
- Chunk: Entity representing a document chunk
- ChunkedDocument: Aggregate root for chunked documents
- EnrichedChunk: Chunk entity with enrichment (inherits Chunk)
- EnrichedDocument: Enriched document aggregate (inherits ChunkedDocument)
"""

from typing import List
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger


@dataclass
class DocumentInfo:
    """Document information value object for chunking context."""
    project_id: str
    reference_doc_id: str
    contract_type: str


class Chunk(BaseModel):
    """Individual chunk entity with content and metadata."""
    content: str = Field(..., description="The chunk text content (no header table)")
    chunk_index: int = Field(..., description="Zero-based index of this chunk")
    section_hierarchy: List[str] = Field(default_factory=list, description="Section hierarchy for context")
    char_start: int = Field(..., description="Character start position in original document")
    char_end: int = Field(..., description="Character end position in original document")
    token_count: int = Field(..., description="Number of tokens in this chunk")
    has_tables: bool = Field(default=False, description="Whether chunk contains tables")


class ChunkedDocument(BaseModel):
    """
    Chunked document aggregate root.

    Represents a complete document with file-level metadata and all chunks.
    """
    # File-level metadata
    project_id: str = Field(..., description="Project identifier")
    reference_doc_id: str = Field(..., description="Reference document identifier")
    contract_type: str = Field(..., description="Type of contract")
    total_chunks: int = Field(..., description="Total number of chunks in document")
    original_markdown_length: int = Field(..., description="Length of original markdown in characters")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")

    # Chunks
    chunks: List[Chunk] = Field(default_factory=list, description="List of document chunks")

    def save_json(self, file_path: str | Path) -> None:
        """Save chunked document to JSON file.

        Args:
            file_path: Path where JSON file will be saved
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=2))

        logger.info(f"Saved chunked document to {path} ({self.total_chunks} chunks)")

    @classmethod
    def load_json(cls, file_path: str | Path) -> "ChunkedDocument":
        """Load chunked document from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            ChunkedDocument instance
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Chunked document file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()

        doc = cls.model_validate_json(data)
        logger.info(f"Loaded chunked document from {path} ({doc.total_chunks} chunks)")

        return doc


class EnrichedChunk(Chunk):
    """
    Enriched chunk entity (inherits from Chunk).

    Extends Chunk with contextually enriched content for improved retrieval.
    """
    enriched_content: str = Field(..., description="Contextually enriched chunk content")

    @classmethod
    def from_chunk(cls, chunk: Chunk, enriched_content: str) -> "EnrichedChunk":
        """Create EnrichedChunk from a Chunk and enriched text.

        Args:
            chunk: Original Chunk instance
            enriched_content: Enriched version of the chunk content

        Returns:
            EnrichedChunk instance with all original fields plus enriched_content
        """
        return cls(
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            section_hierarchy=chunk.section_hierarchy,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            token_count=chunk.token_count,
            has_tables=chunk.has_tables,
            enriched_content=enriched_content
        )


class EnrichedDocument(ChunkedDocument):
    """
    Enriched document aggregate root (inherits from ChunkedDocument).

    Extends ChunkedDocument with enriched chunks and enrichment metadata.
    """
    # Override chunks to use EnrichedChunk
    chunks: List[EnrichedChunk] = Field(default_factory=list, description="List of enriched chunks")

    # Additional enrichment metadata
    enriched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Enrichment timestamp"
    )

    @classmethod
    def from_chunked_document(
        cls,
        chunked_doc: ChunkedDocument,
        enriched_chunks: List[EnrichedChunk]
    ) -> "EnrichedDocument":
        """Create EnrichedDocument from ChunkedDocument and enriched chunks.

        Args:
            chunked_doc: Original ChunkedDocument
            enriched_chunks: List of enriched chunks

        Returns:
            EnrichedDocument with all original metadata plus enrichment
        """
        return cls(
            project_id=chunked_doc.project_id,
            reference_doc_id=chunked_doc.reference_doc_id,
            contract_type=chunked_doc.contract_type,
            total_chunks=chunked_doc.total_chunks,
            original_markdown_length=chunked_doc.original_markdown_length,
            created_at=chunked_doc.created_at,
            chunks=enriched_chunks
        )
