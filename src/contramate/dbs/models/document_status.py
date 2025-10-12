"""Document processing status models for tracking data pipeline stages

This module contains all status tracking models for the document processing pipeline:
- Bronze to Silver: PDF to Markdown conversion
- Silver to Gold: Markdown to Chunks
- Gold to Platinum: Chunks to Vector Index
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class ProcessingStatus(str, Enum):
    """Unified status enum for all document processing stages"""
    READY = "ready"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentConversionStatus(SQLModel, table=True):
    """Track PDF to markdown conversion status for each document

    This table tracks the bronze to silver conversion process where PDFs
    are converted to markdown using pymupdf4llm.
    """

    __tablename__ = "document_conversion_status"

    # Composite primary key matching contract_asmd
    project_id: str = Field(
        primary_key=True,
        max_length=50,
        description="Project identifier (matches contract_asmd.project_id)"
    )
    reference_doc_id: str = Field(
        primary_key=True,
        max_length=100,
        description="Reference document identifier (matches contract_asmd.reference_doc_id)"
    )

    # Processing status
    status: ProcessingStatus = Field(
        default=ProcessingStatus.READY,
        index=True,
        description="Current conversion status: ready, processed, or failed"
    )

    # Execution tracking
    execution_time: Optional[float] = Field(
        default=None,
        description="Execution time in seconds for the conversion process"
    )

    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Error message if conversion failed"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record last update timestamp"
    )

    class Config:
        """SQLModel configuration"""
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "reference_doc_id": "98765432-e89b-12d3-a456-426614174999",
                "status": "ready",
                "execution_time": None,
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class DocumentChunkingStatus(SQLModel, table=True):
    """Track markdown to chunks conversion status for each document

    This table tracks the silver to gold conversion process where markdown
    documents are chunked and prepared for embedding/vectorization.
    """

    __tablename__ = "document_chunking_status"

    # Composite primary key matching contract_asmd
    project_id: str = Field(
        primary_key=True,
        max_length=50,
        description="Project identifier (matches contract_asmd.project_id)"
    )
    reference_doc_id: str = Field(
        primary_key=True,
        max_length=100,
        description="Reference document identifier (matches contract_asmd.reference_doc_id)"
    )

    # Processing status
    status: ProcessingStatus = Field(
        default=ProcessingStatus.READY,
        index=True,
        description="Current chunking status: ready, processed, or failed"
    )

    # Chunking metrics
    chunk_count: Optional[int] = Field(
        default=None,
        description="Number of chunks created from the document"
    )

    # Execution tracking
    execution_time: Optional[float] = Field(
        default=None,
        description="Execution time in seconds for the chunking process"
    )

    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Error message if chunking failed"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record last update timestamp"
    )

    class Config:
        """SQLModel configuration"""
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "reference_doc_id": "98765432-e89b-12d3-a456-426614174999",
                "status": "ready",
                "chunk_count": None,
                "execution_time": None,
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class DocumentIndexingStatus(SQLModel, table=True):
    """Track chunks to vector index conversion status for each document

    This table tracks the gold to platinum conversion process where document
    chunks are embedded and indexed into the vector store (OpenSearch).
    """

    __tablename__ = "document_indexing_status"

    # Composite primary key matching contract_asmd
    project_id: str = Field(
        primary_key=True,
        max_length=50,
        description="Project identifier (matches contract_asmd.project_id)"
    )
    reference_doc_id: str = Field(
        primary_key=True,
        max_length=100,
        description="Reference document identifier (matches contract_asmd.reference_doc_id)"
    )

    # Processing status
    status: ProcessingStatus = Field(
        default=ProcessingStatus.READY,
        index=True,
        description="Current indexing status: ready, processed, or failed"
    )

    # Indexing metrics
    indexed_chunks_count: Optional[int] = Field(
        default=None,
        description="Number of chunks successfully indexed"
    )

    vector_dimension: Optional[int] = Field(
        default=None,
        description="Dimension of the embedding vectors"
    )

    index_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Name of the vector index where chunks are stored"
    )

    # Execution tracking
    execution_time: Optional[float] = Field(
        default=None,
        description="Execution time in seconds for the indexing process"
    )

    # Error tracking
    error_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Error message if indexing failed"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record last update timestamp"
    )

    class Config:
        """SQLModel configuration"""
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "reference_doc_id": "98765432-e89b-12d3-a456-426614174999",
                "status": "ready",
                "indexed_chunks_count": None,
                "vector_dimension": None,
                "index_name": None,
                "execution_time": None,
                "error_message": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
