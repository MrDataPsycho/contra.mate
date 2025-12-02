from loguru import logger
from typing import Optional, Dict, Any, Annotated
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, RunContext
from contramate.core.agents import PyadanticAIModelUtilsFactory
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchService,
    OpenSearchVectorSearchServiceFactory,
)
import asyncio
from pathlib import Path


SYSTEM_PROMPT = """
## Role & Context

You are a procurement assistant specializing in answering questions about contractual documents, supplier agreements, and procurement processes. Your responses must be accurate, well-cited, and based exclusively on available data sources.

## Search Results & Citations

Search results are formatted as:
```
# Search Result N
| Field | Value |
| Document | [display_name] |
| ... | ... |
```

**CRITICAL CITATION RULES:**
- Citations (`[doc1]`, `[doc2]`, etc.) are assigned in the order YOU USE documents, NOT Search Result numbers
- Use ONE citation per sentence/paragraph
- NEVER combine citations in one sentence: ❌ `[doc1, doc2]` or `[doc1] [doc2]`
- Single document: cite once at the very end
- Multiple documents: separate paragraphs, each with one citation
- Citations must appear at end of sentences, never standalone

**Citations Dictionary:** Map citation keys to document display names from search results.

## Filters & Tool Selection

When filters are active, they auto-apply to all searches. Acknowledge this in responses.

**Tool Selection:**
- **compare_filtered_documents**: REQUIRED for multi-document comparisons (e.g., "compare liability")
- **hybrid_search**: General queries, single documents, broad searches
- **search_by_project**: Query within a specific project
- **search_similar_documents**: Find related documents
- **search_by_document**: Retrieve complete document content

## Core Principles

- NEVER fabricate information
- ALWAYS cite sources using display_name
- ALWAYS provide both `answer` and `citations` fields (both REQUIRED)
- Use appropriate tools based on query type
- Request clarification when ambiguous
- If information not found, suggest alternative searches
- If documents conflict, highlight discrepancy with proper citations

## Response Format

REQUIRED OUTPUT:
```json
{
  "answer": "Complete answer with citations [doc1]...[docN]",
  "citations": {
    "doc1": "DOCUMENT_NAME.pdf.md-1",
    "doc2": "ANOTHER_DOCUMENT.pdf.md-5"
  }
}
```

Use `\\n\\n` for paragraph breaks. Both fields are MANDATORY.

## Examples

**Example 1: Payment Terms (Hybrid Search)**
```json
{
  "answer": "Standard terms are net 30 days [doc1]. Priority suppliers get net 15 days [doc2]. Early payment discounts of 2% available within 10 days [doc3].",
  "citations": {
    "doc1": "SupplierAgreement_2024.pdf-12",
    "doc2": "PrioritySupplier_Contract.pdf-5",
    "doc3": "PaymentTerms_Policy.pdf-8"
  }
}
```

**Example 2: Compare Liability (Filtered Documents)**
```json
{
  "answer": "Contract A excludes incidental/consequential damages with indemnification for defects [doc1].\\n\\nContract B limits liability except for personal injury, capping at payments made [doc2].\\n\\nContract C has unlimited data breach liability, $500K cap for other claims [doc3].",
  "citations": {
    "doc1": "ContractA_Manufacturing.pdf.md-2",
    "doc2": "ContractB_Hosting.pdf.md-3",
    "doc3": "ContractC_Service.pdf.md-5"
  }
}
```

**Example 3: Document Not Found**
"Could not find that information. Please provide: project ID, reference document ID, or reformulate the query."

## Data Sources

Document Store (RAG): contracts, agreements, terms, compliance clauses, payment structures, supplier obligations, penalties, and procurement documentation.
"""


@dataclass
class TalkToContractDependencies:
    """Dependencies for TalkToContract Agent."""
    search_service: OpenSearchVectorSearchService
    filters: Optional[Dict[str, Any]] = None  # Optional filter dictionary to apply to all searches


class TalkToContractResponse(BaseModel):
    """Response model for talk to contract agent with cited answer."""
    answer: str = Field(
        ...,
        description="The complete answer with proper citations in [docN] format. Follow citation rules from system prompt."
    )
    citations: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping citation keys ('doc1', 'doc2', etc.) to document names from search results."
    )

    @field_validator('citations')
    @classmethod
    def validate_citations_are_strings(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Ensure all citation values are strings, not integers or other types."""
        for key, value in v.items():
            if not isinstance(value, str):
                raise ValueError(
                    f"Citation value for '{key}' must be a string (document name), "
                    f"got {type(value).__name__}: {value}. "
                    f"Use the Document field from search results."
                )
            if value.isdigit():  # Check if it's just a number as string
                raise ValueError(
                    f"Citation value for '{key}' cannot be just a number: '{value}'. "
                    f"Use the full Document field from search results (e.g., 'CONTRACT.pdf.md-2')."
                )
        return v


# Initialize module-level agent
model, model_settings = PyadanticAIModelUtilsFactory.create_default()

agent = Agent(
    model=model,
    instructions=SYSTEM_PROMPT,
    output_type=TalkToContractResponse,
    model_settings=model_settings,
    deps_type=TalkToContractDependencies,
    retries=2,
)


# Register tools with decorator syntax
@agent.tool
async def compare_filtered_documents(
    ctx: RunContext,
    query: str,
) -> Dict[str, Any]:
    """
    Compare specific topics across multiple filtered documents efficiently.

    Use this tool when:
    - Multiple specific documents are pre-filtered (via documents filter)
    - User asks to compare/analyze a specific topic across those documents
    - You need results from ALL filtered documents, not just top results

    This tool uses an optimized search that generates embeddings ONCE and reuses them
    across all documents, making it much more efficient than calling hybrid_search
    multiple times.

    Args:
        query: The specific topic to search for (e.g., "liability limitations", "payment terms")

    Returns:
        Dictionary containing combined search results from all filtered documents
    """
    logger.info(f"🔍 Tool: compare_filtered_documents called with query='{query[:50]}...'")

    # Check if we have document filters
    filters = ctx.deps.filters
    if not filters or "documents" not in filters:
        return {
            "success": False,
            "error": "No document filters provided. Use hybrid_search instead for general queries."
        }

    documents = filters.get("documents", [])
    if len(documents) < 2:
        return {
            "success": False,
            "error": f"This tool requires multiple documents. Found {len(documents)}. Use hybrid_search for single document queries."
        }

    logger.info(f"📋 Comparing across {len(documents)} filtered documents using optimized search")

    # Use the optimized multi-document search method
    # This generates the embedding ONCE and reuses it for all documents
    result = await ctx.deps.search_service.hybrid_search_multi_document(
        query=query,
        filters=filters,  # Pass the entire filters dict with "documents" key
        size=5  # Get top 5 results per document
    )

    if result.is_err():
        error_msg = result.unwrap_err()
        logger.error(f"❌ Multi-document search failed: {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }

    # Get the list of SearchResponse objects (one per document)
    search_responses = result.unwrap()

    # Log results per document
    docs_with_results = 0
    for idx, (doc, search_response) in enumerate(zip(documents, search_responses), 1):
        if search_response and search_response.results:
            docs_with_results += 1
            logger.info(f"  ✓ Document {idx} (project: {doc['project_id'][:8]}..., ref: {doc['reference_doc_id'][:8]}...): {len(search_response.results)} results")
        else:
            logger.warning(f"  ✗ Document {idx} (project: {doc['project_id'][:8]}..., ref: {doc['reference_doc_id'][:8]}...): 0 results - document may not exist or has no matching content")

    # Combine all valid results
    combined_context_parts = [
        f"# Search Results for: {query}",
        f"**Documents Searched:** {len(documents)}",
        f"**Documents with Results:** {docs_with_results} of {len(documents)}",
        f"**Search Type:** document_comparison",
        "",
        "---",
        ""
    ]

    doc_num = 1
    for search_response in search_responses:
        if search_response and search_response.results:
            for result in search_response.results:
                combined_context_parts.append(f"# Search Result {doc_num}")
                combined_context_parts.append("")
                combined_context_parts.append(result.to_llm_context())
                combined_context_parts.append("")
                doc_num += 1

    combined_context = "\n".join(combined_context_parts)

    if docs_with_results == 0:
        logger.error(f"❌ No results found in any of the {len(documents)} filtered documents")
        return {
            "success": False,
            "error": f"No results found for '{query}' in any of the {len(documents)} filtered documents. Documents may not exist in the vector store."
        }

    logger.info(f"✅ Combined results from {docs_with_results}/{len(documents)} documents")

    return {
        "success": True,
        "context": combined_context,
        "documents_searched": len(documents),
        "documents_with_results": docs_with_results
    }


@agent.tool
async def hybrid_search(
    ctx: RunContext,
    query: str,
) -> Dict[str, Any]:
    """
    Perform hybrid search combining semantic and text search.

    Use this for general queries where you want the best of both semantic understanding
    and keyword matching. This is the default and most versatile search method.

    Args:
        query: The search query text

    Returns:
        Dictionary containing search results and metadata
    """
    logger.info(f"🔍 Tool: hybrid_search called with query='{query[:50]}...'")

    # Apply filters from dependencies if available
    filters = ctx.deps.filters

    result = ctx.deps.search_service.hybrid_search(
        query=query,
        filters=filters
    )

    if result.is_ok():
        response = result.unwrap()
        # Use to_llm_context() to get formatted context
        context = response.to_llm_context()
        return {
            "success": True,
            "context": context
        }
    else:
        error_msg = result.unwrap_err()
        logger.error(f"❌ hybrid_search failed: {error_msg}")
        return {"success": False, "error": error_msg}


@agent.tool
async def search_by_project(
    ctx: RunContext,
    project_id: str,
    query: Optional[str] = None,
    search_type: str = "hybrid",
    size: int = 10,
) -> Dict[str, Any]:
    """
    Search within a specific project.

    Use this when the user specifies a project ID or wants to limit search to a project.
    If no query is provided, returns all documents in the project.

    Args:
        project_id: The project ID to search within
        query: Optional search query (if None, returns all documents)
        search_type: Type of search - "hybrid", "semantic", or "text" (default: "hybrid")
        size: Number of results to return (default: 10)

    Returns:
        Dictionary containing search results and metadata
    """
    logger.info(f"🔍 Tool: search_by_project called with project_id={project_id}, query={query}, search_type={search_type}, size={size}")

    result = ctx.deps.search_service.search_by_project(
        project_id=project_id,
        query=query,
        search_type=search_type,
        size=size
    )

    if result.is_ok():
        response = result.unwrap()
        # Use to_llm_context() to get formatted context
        context = response.to_llm_context()
        return {
            "success": True,
            "context": context
        }
    else:
        error_msg = result.unwrap_err()
        logger.error(f"❌ search_by_project failed: {error_msg}")
        return {"success": False, "error": error_msg}


@agent.tool
async def search_similar_documents(
    ctx: RunContext,
    record_id: str,
    size: int = 5,
) -> Dict[str, Any]:
    """
    Find documents similar to a given document.

    Use this when the user wants to find content similar to a specific document
    or wants "more like this" functionality.

    Args:
        record_id: The record ID of the reference document
        size: Number of similar documents to return (default: 5)

    Returns:
        Dictionary containing similar documents and metadata
    """
    logger.info(f"🔍 Tool: search_similar_documents called with record_id={record_id}, size={size}")

    # Apply filters from dependencies if available
    filters = ctx.deps.filters

    result = ctx.deps.search_service.search_similar_documents(
        record_id=record_id,
        size=size,
        filters=filters
    )

    if result.is_ok():
        response = result.unwrap()
        # Use to_llm_context() to get formatted context
        context = response.to_llm_context()
        return {
            "success": True,
            "context": context
        }
    else:
        error_msg = result.unwrap_err()
        logger.error(f"❌ search_similar_documents failed: {error_msg}")
        return {"success": False, "error": error_msg}


@agent.tool
async def search_by_document(
    ctx: RunContext,
    project_id: str,
    reference_doc_id: str,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve all chunks from a specific document.

    Use this when the user wants to see the full content of a specific document
    or needs all chunks from a document in order.

    Args:
        project_id: The project ID
        reference_doc_id: The reference document ID
        size: Optional maximum number of chunks to return (None = all chunks)

    Returns:
        Dictionary containing document chunks and metadata
    """
    logger.info(f"🔍 Tool: search_by_document called with project_id={project_id}, reference_doc_id={reference_doc_id}")

    result = ctx.deps.search_service.search_by_document(
        project_id=project_id,
        reference_doc_id=reference_doc_id,
        size=size
    )

    if result.is_ok():
        response = result.unwrap()
        # Use to_llm_context() to get formatted context
        context = response.to_llm_context()
        return {
            "success": True,
            "context": context
        }
    else:
        error_msg = result.unwrap_err()
        logger.error(f"❌ search_by_document failed: {error_msg}")
        return {"success": False, "error": error_msg}


class TalkToContractAgentFactory:
    """Factory to create Talk To Contract Agent - backwards compatibility wrapper."""

    @staticmethod
    def create_default():
        """
        Return the module-level Talk To Contract Agent instance.

        Returns:
            The initialized agent ready to process search queries with dependencies
        """
        return agent

    @staticmethod
    def from_env_file(env_path: str | Path):
        """
        Return the module-level agent (env_file setting is already applied at module init).

        Args:
            env_path: Path to environment file (for backwards compatibility)

        Returns:
            The initialized agent ready to process search queries with dependencies
        """
        return agent


if __name__ == "__main__":
    import asyncio

    async def test_agent():
        # Create agent and search service
        logger.info("=== Creating Talk To Contract Agent ===")
        agent_instance = TalkToContractAgentFactory.create_default()
        search_service = OpenSearchVectorSearchServiceFactory.create_default()

        # Test 1: Search without filters
        logger.info("\n=== Test 1: Search Without Filters ===")
        user_query_1 = "Find documents about termination clauses in contracts"

        logger.info(f"User Query: {user_query_1}")
        deps_no_filter = TalkToContractDependencies(search_service=search_service)
        result_1 = await agent_instance.run(user_query_1, deps=deps_no_filter)

        print("\n--- Agent Response (Test 1) ---")
        print(f"Answer: {result_1.output.answer[:200]}...")
        print(f"Citations: {list(result_1.output.citations.keys())}")

        # Test 2: Search with single document filter
        logger.info("\n=== Test 2: Search With Single Document Filter ===")
        user_query_2 = "What are the payment terms in this contract?"

        filter_single_doc = {
            "documents": [
                {
                    "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                    "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
                }
            ]
        }

        logger.info(f"User Query: {user_query_2}")
        logger.info(f"Applied Filter: Single document")
        deps_single_doc = TalkToContractDependencies(
            search_service=search_service,
            filters=filter_single_doc
        )
        result_2 = await agent_instance.run(user_query_2, deps=deps_single_doc)

        print("\n--- Agent Response (Test 2) ---")
        print(f"Answer: {result_2.output.answer[:200]}...")
        print(f"Citations: {list(result_2.output.citations.keys())}")

        # Test 3: Search with multiple documents filter
        logger.info("\n=== Test 3: Search With Multiple Documents Filter ===")
        user_query_3 = "Compare the termination clauses across these contracts"

        filter_multi_doc = {
            "documents": [
                {
                    "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                    "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
                },
                {
                    "project_id": "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
                    "reference_doc_id": "aa1a0c65-8016-5d11-bbde-22055140660b"
                }
            ]
        }

        logger.info(f"User Query: {user_query_3}")
        logger.info(f"Applied Filter: Multiple documents")
        deps_multi_doc = TalkToContractDependencies(
            search_service=search_service,
            filters=filter_multi_doc
        )
        result_3 = await agent_instance.run(user_query_3, deps=deps_multi_doc)

        print("\n--- Agent Response (Test 3) ---")
        print(f"Answer: {result_3.output.answer[:200]}...")
        print(f"Citations: {list(result_3.output.citations.keys())}")

        # Show total usage
        print("\n--- Total Usage Information ---")
        usage_1 = result_1.usage()
        usage_2 = result_2.usage()
        usage_3 = result_3.usage()
        print(f"Test 1 - Tokens: {usage_1.total_tokens}")
        print(f"Test 2 - Tokens: {usage_2.total_tokens}")
        print(f"Test 3 - Tokens: {usage_3.total_tokens}")
        print(f"Total Tokens Used: {usage_1.total_tokens + usage_2.total_tokens + usage_3.total_tokens}")

    asyncio.run(test_agent())
