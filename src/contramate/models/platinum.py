"""
Platinum Model for vector-ready data with embeddings.

This model represents the final processed data with embeddings that will be
indexed in OpenSearch (platinum layer - vector database).

Inherits from GoldModel and adds embedding-specific fields.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from pydantic import Field, computed_field

from contramate.models.gold import GoldModel, DocumentSource


class PlatinumModel(GoldModel):
    """
    Platinum model for vector database storage with embeddings.

    Extends GoldModel with vector embeddings and timestamps ready for indexing
    in OpenSearch. It follows the platinum layer pattern for vector storage.
    """

    # Vector embedding field (added to GoldModel)
    vector: List[float] = Field(description="Vector embedding of the content")

    # Timestamp field (added to GoldModel)
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

    def to_opensearch_doc(self) -> Dict[str, Any]:
        """
        Convert PlatinumModel to OpenSearch compatible document format.

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
    def from_opensearch_doc(cls, doc: Dict[str, Any]) -> "PlatinumModel":
        """
        Create PlatinumModel from OpenSearch document.

        Args:
            doc: OpenSearch document dictionary (should include record_id)

        Returns:
            PlatinumModel: Reconstructed PlatinumModel instance
        """
        return cls(
            chunk_id=doc["chunk_id"],
            project_id=doc["project_id"],
            reference_doc_id=doc["reference_doc_id"],
            document_title=doc["document_title"],
            display_name=doc["display_name"],
            content_source=DocumentSource(doc["content_source"]),
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

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PlatinumModel to dictionary for Parquet serialization.

        Returns:
            dict: Dictionary representation compatible with Polars/Parquet
        """
        return {
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
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlatinumModel":
        """
        Create PlatinumModel from dictionary (Parquet deserialization).

        Args:
            data: Dictionary from Parquet file

        Returns:
            PlatinumModel: Reconstructed PlatinumModel instance
        """
        return cls(
            chunk_id=data["chunk_id"],
            project_id=data["project_id"],
            reference_doc_id=data["reference_doc_id"],
            document_title=data["document_title"],
            display_name=data["display_name"],
            content_source=DocumentSource(data["content_source"]),
            contract_type=data.get("contract_type"),
            content=data["content"],
            chunk_index=data["chunk_index"],
            section_hierarchy=data.get("section_hierarchy", []),
            char_start=data["char_start"],
            char_end=data["char_end"],
            token_count=data["token_count"],
            has_tables=data.get("has_tables", False),
            vector=data["vector"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
