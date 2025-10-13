"""
Vector domain model for vector database storage with embeddings.

This model represents content chunks that will be indexed in OpenSearch
for semantic search. It follows the platinum model pattern for vector storage
and can be used for various types of content that need to be vectorized.
"""

from typing import List, Optional
from datetime import datetime, timezone
from enum import StrEnum
from pydantic import BaseModel, Field, computed_field


class ContentSource(StrEnum):
    """Source types for content data"""
    upload = "upload"
    system = "system"


class VectorModel(BaseModel):
    """
    Vector model for vector database storage with embeddings.
    Contains all fields needed for OpenSearch storage with proper types.
    Schema exactly matches OpenSearch IndexMappingConfig requirements.
    """
    
    # Core identification fields (matching ChunkedDocument)
    chunk_id: int = Field(description="Unique identifier for the chunk")
    project_id: str = Field(description="Project identifier")
    reference_doc_id: str = Field(description="Reference document identifier")
    document_title: str = Field(description="Name of the source document")
    display_name: Optional[str] = Field(default=None, description="Human-readable display name")
    content_source: ContentSource = Field(description="Source of the content")
    contract_type: Optional[str] = Field(default=None, description="Type of contract")
    
    # Chunk-level fields (matching Chunk model)
    content: str = Field(description="The chunk text content")
    chunk_index: int = Field(description="Zero-based index of this chunk")
    section_hierarchy: List[str] = Field(default_factory=list, description="Section hierarchy for context")
    char_start: int = Field(description="Character start position in original document")
    char_end: int = Field(description="Character end position in original document")
    token_count: int = Field(description="Number of tokens in this chunk")
    has_tables: bool = Field(default=False, description="Whether chunk contains tables")
    
    # Vector embedding field
    vector: List[float] = Field(description="Vector embedding of the content")
    
    # Timestamp field
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the document was created in UTC"
    )
    
    @computed_field
    @property
    def record_id(self) -> str:
        """
        Generate unique record ID from combination of project_id, reference_doc_id, and chunk_id.
        This will be used as OpenSearch document _id.
        Format: {project_id}-{reference_doc_id}-{chunk_id}
        """
        return f"{self.project_id}-{self.reference_doc_id}-{self.chunk_id}"
    
    @computed_field
    @property
    def project_reference_doc_id(self) -> str:
        """
        Composite field for project_id and reference_doc_id.  
        Format: {project_id}-{reference_doc_id}
        """
        return f"{self.project_id}-{self.reference_doc_id}"
    
    @computed_field
    @property
    def display_name_safe(self) -> str:
        """
        Display name for indexing, combining document title and chunk ID.
        """
        return f"{self.document_title}-{self.chunk_id}"
    
    def to_opensearch_doc(self) -> dict:
        """
        Convert VectorModel to OpenSearch compatible document format.
        Note: record_id is not included in the document body as it will be used as OpenSearch _id.
        
        Returns:
            dict: Document ready for OpenSearch indexing
        """
        return {
            "record_id": self.record_id,
            "chunk_id": self.chunk_id,
            "project_id": self.project_id,
            "reference_doc_id": self.reference_doc_id,
            "document_title": self.document_title,
            "display_name": self.display_name,
            "content_source": self.content_source.value,
            "contract_type": self.contract_type,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "section_hierarchy": self.section_hierarchy,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_count": self.token_count,
            "has_tables": self.has_tables,
            "vector": self.vector,
            "project_reference_doc_id": self.project_reference_doc_id,
            "display_name_safe": self.display_name_safe,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_opensearch_doc(cls, doc: dict) -> "VectorModel":
        """
        Create VectorModel from OpenSearch document.
        
        Args:
            doc: OpenSearch document dictionary (should include record_id)
            
        Returns:
            VectorModel: Reconstructed VectorModel instance
        """
        return cls(
            chunk_id=doc["chunk_id"],
            project_id=doc["project_id"],
            reference_doc_id=doc["reference_doc_id"],
            document_title=doc["document_title"],
            display_name=doc.get("display_name"),
            content_source=ContentSource(doc["content_source"]),
            contract_type=doc.get("contract_type"),
            content=doc["content"],
            chunk_index=doc["chunk_index"],
            section_hierarchy=doc.get("section_hierarchy", []),
            char_start=doc["char_start"],
            char_end=doc["char_end"],
            token_count=doc["token_count"],
            has_tables=doc.get("has_tables", False),
            vector=doc["vector"],
            created_at=datetime.fromisoformat(doc["created_at"].replace('Z', '+00:00'))
        )



