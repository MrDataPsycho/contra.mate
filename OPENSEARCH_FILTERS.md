# OpenSearch Filters for Contramate

## Overview

The `OpenSearchFilter` model provides a type-safe, Pydantic-based interface for building OpenSearch queries with filters. This integrates seamlessly with the chat application for context-aware contract searching.

## Quick Start

```python
from contramate.models import OpenSearchFilter, DocumentFilter, DocumentSource

# Simple filter by document source
filter = OpenSearchFilter(doc_source=DocumentSource.system)
opensearch_filters = filter.to_opensearch_filters()

# Filter by specific documents
filter = OpenSearchFilter(
    documents=[
        DocumentFilter(project_id="cuad", reference_doc_id="doc001"),
        DocumentFilter(project_id="cuad", reference_doc_id="doc002")
    ]
)

# Combined filters
filter = OpenSearchFilter(
    doc_source=DocumentSource.system,
    contract_type=["NDA", "Service Agreement"],
    project_id=["cuad"]
)

# Build complete bool query with KNN
bool_query = filter.to_opensearch_bool_query(
    query={
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": 10
            }
        }
    }
)
```

## Integration with Chat API

### Scenario: User asks a question with contract filters

**User Request:**
```json
POST /api/chat/conversations/{id}/messages
{
  "content": "What are the payment terms?",
  "context_filters": {
    "doc_source": "system",
    "contract_type": ["NDA", "Service Agreement"],
    "project_id": ["cuad"]
  }
}
```

**Backend Processing:**
```python
# In GetAIResponseUseCase or tool execution
from contramate.models import OpenSearchFilter, DocumentSource

# Parse user's context filters
filter_data = message.filter_value  # From DynamoDB message
opensearch_filter = OpenSearchFilter(
    doc_source=DocumentSource(filter_data.get("doc_source")),
    contract_type=filter_data.get("contract_type"),
    project_id=filter_data.get("project_id")
)

# Use in vector search
query_embedding = embedding_client.embed(user_question)
knn_query = {
    "knn": {
        "embedding": {
            "vector": query_embedding,
            "k": 10
        }
    }
}

# Build filtered search query
search_query = opensearch_filter.to_opensearch_bool_query(query=knn_query)

# Execute search
results = opensearch_client.search(
    index="contracts",
    body={"query": search_query, "size": 5}
)
```

## Filter Model Reference

### DocumentFilter

Filters for specific documents:

```python
DocumentFilter(
    project_id: str,              # Required
    reference_doc_id: str,        # Required
    project_reference_doc_id: str,  # Auto-generated as "project_id-reference_doc_id"
    document_title: str           # Optional
)
```

### OpenSearchFilter

Main filter model supporting multiple criteria:

```python
OpenSearchFilter(
    documents: List[DocumentFilter],  # Filter by specific documents
    doc_source: DocumentSource,       # Filter by source (system/upload)
    contract_type: List[str],         # Filter by contract types
    project_id: List[str]             # Filter by projects
)
```

**Key Methods:**

- `to_opensearch_filters(force_default_filter=True)` → Returns list of filter clauses
- `to_opensearch_bool_query(query=None)` → Returns complete bool query
- `has_filters()` → Check if any filters are set

## OpenSearch Query Structure

### Single Value Filter (term)
```json
{
  "term": {
    "contract_type": "NDA"
  }
}
```

### Multiple Values Filter (terms)
```json
{
  "terms": {
    "project_id": ["cuad", "project2"]
  }
}
```

### Complete Bool Query
```json
{
  "bool": {
    "must": [
      {
        "knn": {
          "embedding": {
            "vector": [...],
            "k": 10
          }
        }
      }
    ],
    "filter": [
      {"term": {"content_source": "system"}},
      {"terms": {"contract_type": ["NDA", "Service Agreement"]}}
    ]
  }
}
```

## Usage in Vector Retrieval Tool

Update `vector_db_retriver_tool` in `core/agents/tools.py`:

```python
def vector_db_retriver_tool(
    question: str,
    filters: Optional[dict] = None
) -> str:
    """Query vector database with optional filters."""
    from contramate.models import OpenSearchFilter
    from contramate.services.opensearch_vector_search_service import OpenSearchVectorSearchService

    # Create filter from dict
    search_filter = OpenSearchFilter(**(filters or {}))

    # Get embedding for question
    embedding_client = OpenAIEmbeddingClient()
    query_vector = embedding_client.embed(question)

    # Build KNN query
    knn_query = {
        "knn": {
            "embedding": {
                "vector": query_vector,
                "k": 10
            }
        }
    }

    # Apply filters
    opensearch_query = search_filter.to_opensearch_bool_query(query=knn_query)

    # Search
    search_service = OpenSearchVectorSearchService()
    results = search_service.search(
        index_name="contracts",
        query=opensearch_query,
        size=5
    )

    return results
```

## Testing

Run the test examples:

```bash
uv run python test_opensearch_filters.py
```

This will show examples of all filter types and their OpenSearch query output.

## Field Mapping

| Filter Field | OpenSearch Field | Type |
|-------------|-----------------|------|
| `documents[].project_reference_doc_id` | `project_reference_doc_id` | term/terms |
| `doc_source` | `content_source` | term |
| `contract_type` | `contract_type` | term/terms |
| `project_id` | `project_id` | term/terms |

## Default Behavior

When no filters are provided and `force_default_filter=True`:
- Applies: `{"term": {"content_source": "system"}}`
- This ensures searches default to system documents only

To disable default filter:
```python
filter.to_opensearch_filters(force_default_filter=False)
```
