"""Services package for high-level business logic."""

from contramate.services.metadata_extraction_service import (
    MetadataExtractionService,
    MetadataExtractionServiceFactory,
)
from contramate.services.markdown_chunking_service import MarkdownChunkingService
from contramate.services.enrich_content_service import EnrichmentService
from contramate.services.opensearch_infra_service import (
    OpenSearchInfraService,
    create_opensearch_infra_service,
)
from contramate.services.opensearch_vector_crud_service import (
    OpenSearchVectorCRUDService,
    OpenSearchVectorCRUDServiceFactory,
)
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchService,
    SearchResult,
    SearchResponse,
)

__all__ = [
    "MetadataExtractionService",
    "MetadataExtractionServiceFactory",
    "MarkdownChunkingService",
    "EnrichmentService",
    "OpenSearchInfraService",
    "create_opensearch_infra_service",
    "OpenSearchVectorCRUDService",
    "OpenSearchVectorCRUDServiceFactory",
    "OpenSearchVectorSearchService",
    "SearchResult",
    "SearchResponse",
]