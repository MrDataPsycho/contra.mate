"""
Gold Model for processed data ready for embedding.

This model represents the structured data fields that will be indexed
in the vector database after processing through the data pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import StrEnum


class DocumentSource(StrEnum):
    """Source of the document."""
    system = "system"
    upload = "upload"


class GoldModel(BaseModel):
    """
    Gold model representing processed data ready for embedding.
    Contains all the structured data fields that will be indexed in the vector database.
    """
    # Core identification fields
    chunk_id: int = Field(description="Unique identifier for the chunk")
    project_id: str = Field(description="Project identifier")
    reference_doc_id: str = Field(description="Reference document identifier")
    document_title: str = Field(description="Name of the source file")
    display_name: str = Field(description="Human-readable display name (filename-chunk_id)")
    content_source: DocumentSource = Field(description="Source of the document")
    contract_type: Optional[str] = Field(default=None, description="Type of contract")

    # Content fields
    content: str = Field(description="Main text content for processing")

    # Chunk-level metadata
    chunk_index: int = Field(description="Zero-based index of this chunk")
    section_hierarchy: List[str] = Field(default_factory=list, description="Section hierarchy for context")
    char_start: int = Field(description="Character start position in original document")
    char_end: int = Field(description="Character end position in original document")
    token_count: int = Field(description="Number of tokens in this chunk")
    has_tables: bool = Field(default=False, description="Whether chunk contains tables")