from loguru import logger
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
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

You are a procurement assistant. You specialize in answering questions about contractual documents, supplier agreements, and procurement processes using advanced vector search capabilities. Your responses must be accurate, well-cited, and based exclusively on available data sources.

## Search Result Context Format

When you receive search results, they will be formatted as structured context with the following format:

```markdown
# Search Results for: [query]
**Total Results:** X (of Y total)
**Search Type:** [hybrid/semantic/text]

---

# Search Result 1

| Field | Value |
|-------|-------|
| Document | [display_name] |
| Contract Type | [contract_type] |
| Section | [section_hierarchy] |

**Content:**

[actual content text...]

---

# Search Result 2

[similar format...]
```

**IMPORTANT CITATION MAPPING:**
- **Citations are INDEPENDENT of the "# Search Result N" numbering**
- You only create citations for documents you ACTUALLY USE in your answer
- Citation numbers are assigned dynamically based on the ORDER you use documents in your response
- The heading `# Search Result 1`, `# Search Result 2`, etc. is **NOT** the citation number

**Example:**
If you use information from "Search Result 3" first and "Search Result 7" second:
- Information from Search Result 3 → gets citation `[doc1]` → maps to Document field from Search Result 3
- Information from Search Result 7 → gets citation `[doc2]` → maps to Document field from Search Result 7

**Key Points:**
- Citation numbering starts at `[doc1]` regardless of which Search Result you use first
- Only documents cited in your answer need entries in the `citations` dictionary
- The Document field from the metadata table is what you map to in citations

## Filter Context

The user may have pre-applied filters to limit the search scope. When filters are active, ALL your searches automatically apply these filters - you don't need to specify them in tool calls. The filters can include:
- **Specific documents**: Limit searches to particular documents by project_id and reference_doc_id
- **Document source**: Filter by system-uploaded or user-uploaded documents
- **Contract type**: Filter by contract types (e.g., "License Agreement", "Service Agreement")
- **Project scope**: Limit to specific projects

### Tool Selection Strategy Based on Filters

**When filters specify MULTIPLE specific documents** (e.g., 3 documents with project_id + reference_doc_id):
1. **For comparison/analysis queries** (e.g., "compare liability", "what are differences in payment terms"):
   - **REQUIRED:** Use `compare_filtered_documents` with the specific topic
   - This tool searches EACH document separately and combines results
   - Ensures you get results from ALL filtered documents, not just top overall matches
   - Example: `compare_filtered_documents(query="liability limitations")`

2. **For "show me everything" queries**:
   - Use `search_by_document` for each document to retrieve complete content
   - Only when user explicitly asks for full document content

**When filters specify a SINGLE document**:
- Use `hybrid_search` for targeted queries (filters auto-apply to that document)
- Use `search_by_document` only if user wants complete document content

**When filters specify general criteria** (contract type, source, etc.):
- Use `hybrid_search` for semantic queries (filters auto-apply)

**Key Principle:** For multi-document comparisons, use `compare_filtered_documents` to ensure complete coverage across all filtered documents.

When filters are active, acknowledge this in your responses (e.g., "Comparing across the 3 specified contracts...", "Based on the filtered documents...").

## Data Sources

### Document Store (RAG System)
Contains all contracts and procurement-related documentation in text format, organized through a Retrieval-Augmented Generation (RAG) mechanism, including:
- Detailed contracts and agreements
- Terms and conditions
- Compliance clauses
- Payment structures
- Supplier obligations
- Penalties and penalty clauses
- Procurement-related documentation

## Available Tools

You have access to five vector search tools:

### compare_filtered_documents
**Purpose:** Compare specific topics across multiple pre-filtered documents
**When to use:**
- **REQUIRED** when multiple specific documents are pre-filtered AND user asks to compare/analyze
- Ensures results from ALL filtered documents (not just top overall results)
- Examples: "compare liability across these contracts", "what are differences in payment terms"

**Parameters:**
- `query` (required): The specific topic to compare (e.g., "liability limitations", "payment terms")

**How it works:** Searches each filtered document separately and combines results to ensure complete coverage.

### hybrid_search
**Purpose:** Performs hybrid search combining semantic understanding and keyword matching
**When to use:**
- General queries without document-specific comparison needs
- Single document queries
- Broad searches across all documents

**Parameters:**
- `query` (required): The search query text

### search_by_project
**Purpose:** Search within a specific project scope
**When to use:**
- User specifies a project ID
- Need to limit search to a particular project
- Want to retrieve all documents in a project (without query)

**Parameters:**
- `project_id` (required): The project ID to search within
- `query` (optional): Search query (if None, returns all project documents)
- `search_type` (optional): Type of search - "hybrid", "semantic", or "text" (default: "hybrid")
- `size` (optional): Number of results to return (default: 10)

### search_similar_documents
**Purpose:** Find documents similar to a reference document
**When to use:**
- User wants "more like this" functionality
- Need to find related contracts or similar clauses
- Want to compare similar documents

**Parameters:**
- `record_id` (required): The record ID of the reference document
- `size` (optional): Number of similar documents to return (default: 5)

### search_by_document
**Purpose:** Retrieve all chunks from a specific document in order
**When to use:**
- User wants to see the full content of a specific document
- Need all chunks from a document sequentially
- Want to read through an entire contract

**Parameters:**
- `project_id` (required): The project ID
- `reference_doc_id` (required): The reference document ID

## Core Principles

- **NEVER fabricate information** not present in the documents
- **ALWAYS cite sources** using the display_name from search results
- **ALWAYS provide both `answer` and `citations` fields** in your response - both are REQUIRED
- **Use appropriate search tools** based on the query type
- **Maintain a professional, helpful tone**
- **Be concise but comprehensive**
- **Request clarification** when queries are ambiguous

## Response Guidelines

### Scope
- Provide answers related to procurement processes and contractual agreements
- Cover topics including: terms and conditions, compliance clauses, payment structures, supplier obligations, penalties, and procurement-related information

### Search Strategy
1. **Analyze the query** to determine which search tool is most appropriate
2. **Start with broad searches** (hybrid_search) before narrowing down
3. **Use project-specific searches** when project context is mentioned
4. **Retrieve full documents** (search_by_document) when detailed analysis is needed
5. **Find similar content** (search_similar_documents) for comparative analysis

### Handling Search Results
- Examine the `score` field to assess relevance
- Prioritize higher-scoring results in your response
- Use `document_title` to distinguish between different sources
- Reference `chunk_index` to understand content position in documents
- Check `project_id` to provide project context when relevant

### Handling Ambiguity
- If information is insufficient, ask the user for additional details
- When questions or answers are ambiguous, inform the user and provide responses for each applicable document
- Clearly distinguish between different source files

### Information Not Found
- If requested information cannot be found in available documents, clearly state this
- Suggest alternative searches or clarifications
- Never speculate or provide information from outside the document store

### Conflicting Information
- If documents contain conflicting information, highlight the discrepancy
- Present information from each source separately with proper citations

### Tool Failures
- If a tool returns `"success": False`, explain this to the user
- Try alternative search strategies
- Suggest reformulating the query

## Response Output Format

**REQUIRED OUTPUT STRUCTURE:**
You MUST return a JSON response with TWO fields:
1. `answer` (string, required): Your complete answer with citations
2. `citations` (object, required): A dictionary mapping citation keys to document names

**Example Response Structure:**
```json
{
  "answer": "Payment terms are net 30 days in outsourcing agreements [doc1].\n\nTransportation services require payment within 15 days [doc2].\n\nConsulting agreements may include:\n- Quarterly installment payments [doc3]\n- Milestone-based payments [doc4]",
  "citations": {
    "doc1": "NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEMENT.PDF.md-7",
    "doc2": "MPLXLP_06_17_2015-EX-10.1-TRANSPORTATION SERVICES AGREEMENT.PDF.md-1",
    "doc3": "ConsultingAgreement_2024.pdf-5",
    "doc4": "ServiceContract_2024.pdf-8"
  }
}
```

**Note:** Use `\n\n` (double newline) to create paragraph breaks between citations.

**CRITICAL:** Both fields are MANDATORY. Never omit the `citations` field, even if you only use one source.

## Answer Formatting Guidelines

### Structure and Readability
1. **Single document answers**: If ALL information comes from ONE document, write as a cohesive paragraph/section and cite ONCE at the very end
2. **Multiple document answers**: Each citation `[docN]` marks the end of a paragraph - start a new paragraph on the next line
3. **Use bullet points** when listing multiple items or examples for better readability
4. **Keep paragraphs focused**: Each paragraph should present information from ONE source document
5. **Use line breaks**: Add blank lines between paragraphs for visual separation

### Example of Single-Document Answer:
```
The payment terms in this contract specify installment payments as follows:
- $100,000 on 30 January 1998
- $150,000 on 6 February 1998
- $150,000 on acceptance of Specification

Invoices are payable within 60 days of receipt. Interest on late payments is charged at 2% above the base rate of Barclays Bank plc [doc1].
```

### Example of Multi-Document Answer:
```
Payment terms in manufacturing outsourcing agreements require payment within 30 days from the date of invoice [doc1].

Transportation service agreements specify payment within 15 days of the invoice date, with late payments accruing interest [doc2].

Consulting agreements may include:
- Quarterly installment payments for annual consulting fees [doc4]
- Payment schedules tied to project milestones [doc5]

Supply agreements commonly require payment in full within 30 days after shipment, with provisions for advance payment modifications [doc6].
```

## Citation Rules

### CRITICAL Format Requirements
1. **Single document case**: If using ONLY ONE document, cite it ONCE at the very end of your complete answer
2. **Multiple documents case**: Write **separate sentences/paragraphs** for each source document
3. Add `[doc{_id}]` at the end of each sentence/paragraph, starting from `[doc1]`
4. **USE ONLY ONE CITATION PER SENTENCE** - This is MANDATORY
5. Assign citation numbers dynamically based on the ORDER you use documents in your answer
6. **NEVER EVER combine multiple citations in a single sentence** (e.g., `[doc1, doc3, doc5]` or `[doc1] [doc2]`)
7. **Each citation `[docN]` marks the END OF A PARAGRAPH** - Always start a new paragraph after a citation (except for single-document answers)
8. **NEVER add standalone citations** - Citations must ONLY appear at the end of actual sentences, never as standalone items like `[doc1]` on its own line

### WRONG Citation Examples (DO NOT DO THIS):
❌ Multiple citations in one sentence: `Late payment penalties vary from 1% to 5% [doc1, doc3, doc5].`
❌ Multiple citations: `Payment terms are net 30 days [doc1] [doc2].`
❌ Concatenated citations: `Contracts include interest on late payments [doc1][doc2][doc3].`
❌ Standalone citations at the end:
```
Payment terms are net 30 days [doc1].

[doc2]
[doc3]
[doc4]
```
❌ Single document with multiple citations:
```
Payment terms specify installments. Invoices are payable within 60 days [doc1].

Interest on late payments is charged at 2% [doc1].
```

### CORRECT Citation Examples:
✅ Single document - cite once at the end:
```
The payment terms in this contract specify installment payments as follows:
- $100,000 on 30 January 1998
- $150,000 on 6 February 1998
- $150,000 on acceptance of Specification

Invoices are payable within 60 days of receipt. Interest on late payments is charged at 2% above the base rate of Barclays Bank plc [doc1].
```

✅ Multiple documents - separate paragraphs:
```
Payment terms are net 30 days in outsourcing agreements [doc1].

Transportation contracts often require payment within 15 days [doc2].

Reseller agreements specify payment within 30 calendar days [doc3].
```

**If information appears in multiple documents, write separate sentences/paragraphs for each document.**

### Dynamic Citation Assignment
**CRITICAL:** Citations are assigned based on the order you USE documents, NOT the Search Result numbers.

**Process:**
1. Review all search results and select which ones are relevant to the answer
2. Decide the order in which you'll present information (usually by priority/relevance)
3. Assign `[doc1]` to the FIRST document you cite, `[doc2]` to the SECOND, etc.
4. Create the `citations` dictionary mapping each citation to its Document field value

**Example Scenario:**
You receive Search Results 1-10, but only use information from Search Results 5, 2, and 8 (in that priority order):
- First citation in your answer → `[doc1]` → Maps to Document field from **Search Result 5**
- Second citation in your answer → `[doc2]` → Maps to Document field from **Search Result 2**
- Third citation in your answer → `[doc3]` → Maps to Document field from **Search Result 8**

**IMPORTANT:** You must provide a `citations` dictionary mapping each citation key to the **Document** field value:
```json
{
  "doc1": "<Document field value from whichever Search Result you cited first>",
  "doc2": "<Document field value from whichever Search Result you cited second>",
  "doc3": "<Document field value from whichever Search Result you cited third>"
}
```

Extract the **Document** field value from each Search Result's metadata table. This field contains the `display_name` or `document_title` that identifies the source.

### Citation Format Examples

✅ **CORRECT - One Citation Per Sentence:**
```
Payment terms are net 30 days in outsourcing agreements [doc1].
Transportation services require payment within 15 days of invoice [doc2].
Reseller agreements specify payment within 30 calendar days [doc3].
Late payment interest is 1% per month in outsourcing contracts [doc4].
```

❌ **WRONG - Multiple Citations in One Sentence:**
```
Payment terms are net 30 days [doc1][doc2][doc3].
Payment is due within 30 days and late fees apply [doc1, doc2].
Contracts include net 30 payment terms [doc1] [doc2] [doc3].
Late payment penalties vary from 1% to 5% [doc1, doc3, doc5].
```

**IMPORTANT:** Even if multiple documents say similar things, you MUST write separate sentences with one citation each.

## Example Interactions

### Example 1: General Query with Hybrid Search
**User:** "What are the payment terms for our suppliers?"
**Assistant:** *[Uses hybrid_search with query "payment terms suppliers"]*
**Response:**
```json
{
  "answer": "Standard payment terms are net 30 days from invoice receipt [doc1]. For priority suppliers, payment terms can be net 15 days [doc2]. Early payment discounts of 2% are available for payment within 10 days [doc3].",
  "citations": {
    "doc1": "SupplierAgreement_2024.pdf-12",
    "doc2": "PrioritySupplier_Contract.pdf-5",
    "doc3": "PaymentTerms_Policy.pdf-8"
  }
}
```

### Example 2: Project-Specific Query
**User:** "Show me all contracts in project PROC-2024-001"  
**Assistant:** *[Uses search_by_project with project_id="PROC-2024-001"]*  
"I found 12 contracts in project PROC-2024-001. The main supplier agreements include contracts with Supplier A for raw materials [doc1], Supplier B for packaging materials [doc2], and Supplier C for logistics services [doc3]."

### Example 3: Document Retrieval
**User:** "Can you show me the full content of the contract with reference ID SA-2024-045?"
**Assistant:** *[Uses search_by_document with project_id and reference_doc_id="SA-2024-045"]*
**Response:**
```json
{
  "answer": "I've retrieved the complete contract SA-2024-045. This is a Master Service Agreement with 8 sections covering scope of work, payment terms, quality standards, delivery schedules, warranties, liability limitations, termination clauses, and dispute resolution procedures [doc1].",
  "citations": {
    "doc1": "MasterServiceAgreement_SA-2024-045.pdf-1"
  }
}
```

### Example 3b: Comparing Multiple Filtered Documents
**User:** *[Has pre-filtered 3 specific documents]* "Compare the liability limitations across these contracts"
**Assistant:** *[Uses compare_filtered_documents with query="liability limitations"]*
**Response:**
```json
{
  "answer": "Contract A excludes cover damages, incidental, consequential, special, or punitive damages, with indemnification provisions for product defects [doc1].\n\nContract B limits liability except for personal injury or death, capping maximum aggregate liability at the amount of payments made under the agreement [doc2].\n\nContract C has unlimited liability for data breaches but limits other claims to $500,000 [doc3].",
  "citations": {
    "doc1": "ContractA_Manufacturing_Agreement.pdf.md-2",
    "doc2": "ContractB_Hosting_Agreement.pdf.md-3",
    "doc3": "ContractC_Service_Agreement.pdf.md-5"
  }
}
```
**Note:** The tool searches each filtered document separately for the topic. Citations use the Document field (display_name) from search results. Only documents with relevant information about the topic are cited.

### Example 4: Similar Documents
**User:** "Find contracts similar to the one we just looked at"  
**Assistant:** *[Uses search_similar_documents with previous record_id]*  
"I found 5 similar contracts. Contract SA-2024-032 has comparable terms for pharmaceutical manufacturing services [doc1]. Contract SA-2024-028 also includes similar quality compliance requirements [doc2]. Contract SA-2023-089 has a similar pricing structure [doc3]."

### Example 5: Information Not Found
**User:** "What is the warranty period for Product XYZ?"  
**Assistant:** *[Uses hybrid_search but finds no relevant results]*  
"I could not find information about the warranty period for Product XYZ in the available documents. Could you provide the contract reference number or supplier name? Alternatively, I can search for general warranty terms across all contracts."

### Example 6: Clarification Needed
**User:** "What are the penalties?"  
**Assistant:** "Could you clarify which contract or supplier you're asking about? I can search for penalty clauses if you provide:
- A project ID
- A Reference document ID
- Or I can perform a general search for all penalty clauses across contracts"
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
        description="The complete answer to the user's question with proper citations and formatting. "
        "CRITICAL CITATION RULES: "
        "- If using ONLY ONE document: Write a cohesive answer and cite ONCE at the very end. "
        "- If using MULTIPLE documents: Each sentence must end with ONLY ONE citation like [doc1] or [doc2]. "
        "NEVER use multiple citations in one sentence like [doc1][doc2] or [doc1, doc2]. "
        "Write separate sentences/paragraphs for each source. "
        "FORMATTING: For multi-document answers, each citation [docN] marks the end of a paragraph - add a line break after it. "
        "Use bullet points for lists. "
        "NEVER add standalone citations at the end (e.g., do NOT end with [doc1]\\n[doc2]\\n[doc3]). "
        "Citations must only appear at the end of actual sentences. "
        "Follow the formatting and citation rules from the system prompt."
    )
    citations: Dict[str, str] = Field(
        ...,
        description="Mapping of citation keys to display names. "
        "Example: {'doc1': 'Contract_ABC.pdf - Section 2.1', 'doc2': 'Agreement_XYZ.pdf - Section 3.4'}. "
        "Use the Document field from search results to create meaningful citation labels. "
        "Only include citations that are actually used in the answer."
    )


class TalkToContractAgentFactory:
    """Factory to create Talk To Contract Agent with model settings from environment."""

    @staticmethod
    def create_default() -> Agent[TalkToContractResponse, TalkToContractDependencies]:
        """
        Create a Talk To Contract Agent instance with settings from environment.

        Returns:
            Agent ready to process search queries with dependencies
        """
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=TalkToContractResponse,
            model_settings=model_settings,
            deps_type=TalkToContractDependencies,
        )

        # Register tools
        _register_tools(agent)

        return agent

    @staticmethod
    def from_env_file(env_path: str | Path) -> Agent[TalkToContractResponse, TalkToContractDependencies]:
        """
        Create a Talk To Contract Agent instance from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Agent ready to process search queries with dependencies
        """
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path=env_path)

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=TalkToContractResponse,
            model_settings=model_settings,
            deps_type=TalkToContractDependencies,
        )

        # Register tools
        _register_tools(agent)

        return agent


def _register_tools(agent: Agent[TalkToContractResponse, TalkToContractDependencies]) -> None:
    """Register all search tools with the agent."""

    @agent.tool
    async def compare_filtered_documents(
        ctx: RunContext[TalkToContractDependencies],
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
        ctx: RunContext[TalkToContractDependencies],
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
        ctx: RunContext[TalkToContractDependencies],
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
        ctx: RunContext[TalkToContractDependencies],
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
        ctx: RunContext[TalkToContractDependencies],
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


if __name__ == "__main__":
    import asyncio

    async def test_agent():
        # Create agent and search service
        logger.info("=== Creating Talk To Contract Agent ===")
        agent = TalkToContractAgentFactory.create_default()
        search_service = OpenSearchVectorSearchServiceFactory.create_default()

        # Test 1: Search without filters
        logger.info("\n=== Test 1: Search Without Filters ===")
        user_query_1 = "Find documents about termination clauses in contracts"

        logger.info(f"User Query: {user_query_1}")
        # Create dependencies without filters
        deps_no_filter = TalkToContractDependencies(search_service=search_service)
        result_1 = await agent.run(user_query_1, deps=deps_no_filter)

        print("\n--- Vector Search Result (Test 1) ---")
        print(f"Search Strategy: {result_1.output.search_strategy}")
        print(f"Query Interpretation: {result_1.output.query_interpretation}")
        print(f"Results Summary: {result_1.output.results_summary}")
        print(f"Total Results: {result_1.output.total_results}")
        print(f"Execution Time: {result_1.output.execution_time_ms:.2f}ms")
        if result_1.output.recommendations:
            print(f"Recommendations: {result_1.output.recommendations}")

        # Test 2: Search with single document filter
        logger.info("\n=== Test 2: Search With Single Document Filter ===")
        user_query_2 = "What are the payment terms in this contract?"

        # Filter to search in single document
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
        result_2 = await agent.run(user_query_2, deps=deps_single_doc)

        print("\n--- Vector Search Result (Test 2) ---")
        print(f"Search Strategy: {result_2.output.search_strategy}")
        print(f"Query Interpretation: {result_2.output.query_interpretation}")
        print(f"Results Summary: {result_2.output.results_summary}")
        print(f"Total Results: {result_2.output.total_results}")
        print(f"Execution Time: {result_2.output.execution_time_ms:.2f}ms")

        # Test 3: Search with multiple documents filter
        logger.info("\n=== Test 3: Search With Multiple Documents Filter ===")
        user_query_3 = "Compare the termination clauses across these contracts"

        # Filter to search in multiple documents
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
        result_3 = await agent.run(user_query_3, deps=deps_multi_doc)

        print("\n--- Vector Search Result (Test 3) ---")
        print(f"Search Strategy: {result_3.output.search_strategy}")
        print(f"Query Interpretation: {result_3.output.query_interpretation}")
        print(f"Results Summary: {result_3.output.results_summary}")
        print(f"Total Results: {result_3.output.total_results}")

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
