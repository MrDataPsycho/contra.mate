"""
Gold Model for processed data ready for embedding.

This model represents the structured data fields that will be indexed 
in the vector database after processing through the data pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import StrEnum


class DocumentSource(StrEnum):
    """Source of the document."""
    system: str = "system"
    upload: str = "upload"


class GoldModel(BaseModel):
    """
    Gold model representing processed data ready for embedding.
    Contains all the structured data fields that will be indexed in the vector database.
    """
    chunk_id: int = Field(description="Unique identifier for the chunk")
    project_id: str = Field(description="Project identifier")
    internal_document_id: str = Field(description="Document identifier")
    document_title: str = Field(description="Name of the source file")
    display_name: str = Field(description="Human-readable display name")
    doc_source: DocumentSource = Field(description="Source of the document")
    contract_type: Optional[str] = Field(default="unknown", description="Type of contract")
    content: str = Field(description="Main text content for processing")
    enriched_content: str = Field(description="Optional enriched content with enhanced information")