# Filter Model Migration Summary

## Overview

Successfully migrated from the old `GlobalFilter` class to the new unified `OpenSearchFilter` model across the entire codebase.

## Changes Made

### 1. Created New Filter Models (`src/contramate/models/filters.py`)

**DocumentFilter**
- Filters for specific documents
- Auto-generates composite ID: `project_id-reference_doc_id`
- Fields: `project_id`, `reference_doc_id`, `document_title`

**OpenSearchFilter**
- Main filter model for all search operations
- Supports: documents, doc_source, contract_type, project_id
- Methods:
  - `to_opensearch_filters(force_default_filter=True)` → List of filter clauses
  - `to_opensearch_bool_query(query=None)` → Complete bool query
  - `has_filters()` → Check if any filters set

### 2. Updated OpenSearch Vector Search Service

**File**: `src/contramate/services/opensearch_vector_search_service.py`

**Removed:**
- Old `GlobalFilter` class (107 lines removed)
- Complex field mappings for content characteristics and date filters
- Union type hints accepting both `Dict` and `GlobalFilter`

**Updated:**
- `_create_global_filter()` → `_create_opensearch_filter()`
- All method signatures now accept **only** `Dict[str, Any]`
- Internal conversion to `OpenSearchFilter`
- Applied `force_default_filter=False` to avoid automatic defaults

**Methods Updated:**
1. `semantic_search()` - Semantic/vector search with filters
2. `text_search()` - Full-text search with filters
3. `hybrid_search()` - Combined semantic + text search
4. `search_similar_documents()` - Find similar docs with filters

### 3. Key Improvements

✅ **Simplified API**
- Single filter model across codebase
- Only accept dict input (no union types)
- Clear conversion path: `dict` → `OpenSearchFilter` → `filter_clauses`

✅ **Better Type Safety**
- Pydantic validation on filter construction
- Enum support for `DocumentSource`
- Optional fields with clear defaults

✅ **Cleaner Code**
- Removed 107 lines of duplicate filter logic
- Single source of truth for filter conversion
- Consistent naming (`OpenSearchFilter` vs `GlobalFilter`)

✅ **No Breaking Changes**
- All service methods still accept `filters: Optional[Dict[str, Any]]`
- Existing code continues to work
- Internal implementation cleaner

## Usage Examples

### Basic Filter Usage

```python
from contramate.models import OpenSearchFilter, DocumentSource

# Create filter
filter_dict = {
    "doc_source": DocumentSource.system,
    "contract_type": ["NDA", "Service Agreement"],
    "project_id": ["cuad"]
}

# Use in search
search_service = OpenSearchVectorSearchService()
result = search_service.semantic_search(
    query="payment terms",
    filters=filter_dict,  # Pass dict directly
    k=10
)
```

### Chat API Integration

```python
# In GetAIResponseUseCase or tool
user_filters = message.filter_value  # From DynamoDB

# Pass directly to search service
search_result = vector_search_service.semantic_search(
    query=user_question,
    filters=user_filters,  # Dict from message
    size=5
)
```

### Advanced: Direct Filter Object

```python
from contramate.models import OpenSearchFilter, DocumentFilter

# Create filter object
opensearch_filter = OpenSearchFilter(
    documents=[
        DocumentFilter(project_id="cuad", reference_doc_id="doc001"),
        DocumentFilter(project_id="cuad", reference_doc_id="doc002")
    ],
    doc_source=DocumentSource.system
)

# Get filter clauses
filter_clauses = opensearch_filter.to_opensearch_filters()

# Or build complete query
knn_query = {"knn": {"embedding": {"vector": [...], "k": 10}}}
bool_query = opensearch_filter.to_opensearch_bool_query(query=knn_query)
```

## Filter Field Mapping

| Filter Field | OpenSearch Field | Query Type | Example |
|-------------|-----------------|------------|---------|
| `documents[].project_reference_doc_id` | `project_reference_doc_id` | term/terms | Single or multiple docs |
| `doc_source` | `content_source` | term | "system" or "upload" |
| `contract_type` | `contract_type` | term/terms | ["NDA", "Service Agreement"] |
| `project_id` | `project_id` | term/terms | ["cuad", "project2"] |

## Migration Checklist

- [x] Create new `OpenSearchFilter` model
- [x] Remove old `GlobalFilter` class
- [x] Update all service method signatures
- [x] Update filter conversion method
- [x] Update all filter application logic
- [x] Test syntax compilation
- [x] Create integration tests
- [x] Document usage examples

## Testing

Run the integration tests:

```bash
# Test new filter models
uv run python test_opensearch_filters.py

# Test service integration
uv run python test_opensearch_service_integration.py
```

## Next Steps

1. **Update vector retrieval tool** (`core/agents/tools.py`)
   - Add filters parameter to `vector_db_retriver_tool`
   - Pass filters from message context

2. **Frontend Integration**
   - Add filter UI components
   - Send filters in `context_filters` field

3. **Documentation**
   - Update API docs with filter examples
   - Add filter guide to developer documentation

## Files Modified

1. `src/contramate/models/filters.py` (NEW - 166 lines)
2. `src/contramate/models/__init__.py` (Updated exports)
3. `src/contramate/services/opensearch_vector_search_service.py` (Simplified - removed 107 lines)
4. `test_opensearch_filters.py` (NEW - test examples)
5. `test_opensearch_service_integration.py` (NEW - integration test)
6. `OPENSEARCH_FILTERS.md` (NEW - complete documentation)

## Benefits

1. **Single Source of Truth**: One filter model for all OpenSearch operations
2. **Type Safety**: Pydantic validation ensures correct filter structure
3. **Maintainability**: Less code duplication, clearer responsibilities
4. **Extensibility**: Easy to add new filter types to `OpenSearchFilter`
5. **Consistency**: Same filter model used in chat API and vector search
