"""
Pydantic models for OpenSearch filter structures.

These models provide a clean interface for building OpenSearch queries
with type safety and validation.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from contramate.models.gold import DocumentSource


class DocumentFilter(BaseModel):
    """
    Filter criteria for a specific document.

    Allows filtering by document-specific fields like project and document IDs.
    """

    project_id: str = Field(..., description="Project identifier")
    reference_doc_id: str = Field(..., description="Reference document identifier")
    project_reference_doc_id: Optional[str] = Field(
        None, description="Composite project-document identifier"
    )
    document_title: Optional[str] = Field(None, description="Document title")

    def model_post_init(self, _: Any) -> None:
        """Post-initialization to set composite field if not provided."""
        if self.project_reference_doc_id is None:
            self.project_reference_doc_id = (
                f"{self.project_id}-{self.reference_doc_id}"
            )


class OpenSearchFilter(BaseModel):
    """
    Global filter criteria for OpenSearch queries.

    Supports filtering by:
    - Specific documents (via DocumentFilter list)
    - Document source (system/upload)
    - Contract types
    - Project IDs
    """

    documents: Optional[List[DocumentFilter]] = Field(
        None, description="List of specific document filters"
    )
    doc_source: Optional[DocumentSource] = Field(
        None, description="Source of the document (system/upload)"
    )
    contract_type: Optional[List[str]] = Field(
        None, description="List of contract types to filter"
    )
    project_id: Optional[List[str]] = Field(
        None, description="List of project identifiers to filter"
    )

    def to_opensearch_filters(self, force_default_filter: bool = True) -> List[Dict[str, Any]]:
        """
        Convert filter criteria to OpenSearch compatible filter clauses.

        Uses 'term' for single values and 'terms' for multiple values.
        If no filters are provided and force_default_filter is True,
        applies a default doc_source=system filter.

        Args:
            force_default_filter: If True, applies doc_source=system filter
                                when no other filters are provided

        Returns:
            List of OpenSearch filter clauses in bool query format

        Example:
            >>> filter = OpenSearchFilter(
            ...     project_id=["proj1", "proj2"],
            ...     doc_source=DocumentSource.system
            ... )
            >>> filter.to_opensearch_filters()
            [
                {"terms": {"project_id": ["proj1", "proj2"]}},
                {"term": {"doc_source": "system"}}
            ]
        """
        filter_clauses = []
        has_filters = False

        # Handle document-specific filters
        if self.documents:
            document_ids = [doc.project_reference_doc_id for doc in self.documents]

            if len(document_ids) == 1:
                # Single document - use term query
                filter_clauses.append({
                    "term": {"project_reference_doc_id": document_ids[0]}
                })
            else:
                # Multiple documents - use terms query
                filter_clauses.append({
                    "terms": {"project_reference_doc_id": document_ids}
                })

            has_filters = True

        # Handle doc_source as single optional value
        if self.doc_source:
            filter_clauses.append({"term": {"content_source": self.doc_source.value}})
            has_filters = True

        # Handle fields that might have single or multiple values
        field_mappings = {
            "contract_type": self.contract_type,
            "project_id": self.project_id,
        }

        for field_name, values in field_mappings.items():
            if values:
                if len(values) == 1:
                    # Single value - use term query
                    filter_clauses.append({"term": {field_name: values[0]}})
                else:
                    # Multiple values - use terms query
                    filter_clauses.append({"terms": {field_name: values}})

                has_filters = True

        # Apply default filter if no filters are provided and force_default_filter is True
        if not has_filters and force_default_filter:
            filter_clauses.append({"term": {"content_source": DocumentSource.system.value}})

        return filter_clauses

    def to_opensearch_bool_query(
        self,
        query: Optional[Dict[str, Any]] = None,
        force_default_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Build a complete OpenSearch bool query with filters.

        Combines optional query clause with filter clauses.

        Args:
            query: Optional query clause (e.g., match, knn, etc.)
            force_default_filter: Apply default filter if no filters provided

        Returns:
            Complete OpenSearch bool query structure

        Example:
            >>> filter = OpenSearchFilter(project_id=["proj1"])
            >>> knn_query = {"knn": {"vector_field": {...}}}
            >>> filter.to_opensearch_bool_query(query=knn_query)
            {
                "bool": {
                    "must": [{"knn": {...}}],
                    "filter": [{"term": {"project_id": "proj1"}}]
                }
            }
        """
        filter_clauses = self.to_opensearch_filters(force_default_filter)

        bool_query: Dict[str, Any] = {"bool": {}}

        if query:
            bool_query["bool"]["must"] = [query]

        if filter_clauses:
            bool_query["bool"]["filter"] = filter_clauses

        return bool_query

    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return bool(
            self.documents or
            self.doc_source or
            self.contract_type or
            self.project_id
        )
