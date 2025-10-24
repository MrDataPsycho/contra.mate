"""Vanilla OpenAI Talk To Contract Agent with function calling.

This implementation uses vanilla OpenAI SDK instead of pydantic-ai to avoid
structured output validation issues when using message history.
"""

from loguru import logger
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import json
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchService,
    OpenSearchVectorSearchServiceFactory,
)
from contramate.llm import LLMVanillaClientFactory
from contramate.utils.settings.core import OpenAISettings


class ResponseValidationError(Exception):
    """Raised when LLM response doesn't match expected format."""
    pass


# System prompt remains the same
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

## Response Output Format

**REQUIRED OUTPUT STRUCTURE - JSON ONLY:**
You MUST return a valid JSON object with TWO fields:
1. `answer` (string, required): Your complete answer with citations
2. `citations` (object, required): A dictionary mapping citation keys to document names

**Example Response:**
{
  "answer": "Payment terms are net 30 days in outsourcing agreements [doc1].\\n\\nTransportation services require payment within 15 days [doc2].",
  "citations": {
    "doc1": "NICELTD_06_26_2003-EX-4.5-OUTSOURCING AGREEMENT.PDF.md-7",
    "doc2": "MPLXLP_06_17_2015-EX-10.1-TRANSPORTATION SERVICES AGREEMENT.PDF.md-1"
  }
}

**CRITICAL:**
- Both fields are MANDATORY
- Response must be valid JSON
- Citations values must be full document names from search results (not just 'doc1', 'source', or numbers)

## Citation Rules

### CRITICAL Format Requirements - ONE CITATION PER LINE
1. **Single document case**: If using ONLY ONE document, cite it ONCE at the very end of your complete answer
2. **Multiple documents case**: Write **separate paragraphs** for each source document
3. Add `[doc{_id}]` at the end of each paragraph, starting from `[doc1]`
4. **ABSOLUTE RULE: ONLY ONE CITATION PER LINE/PARAGRAPH** - This is MANDATORY
5. **NEVER EVER combine multiple citations together** - NO `[doc1][doc2]`, NO `[doc1,doc2]`, NO multiple citations on same line
6. **Each citation `[docN]` marks the END OF A PARAGRAPH** - You MUST start a new paragraph (new line with `\n\n`) after each citation
7. **If information comes from multiple sources, write SEPARATE paragraphs for EACH source with its OWN citation**

### Citation Format Examples

**CORRECT ✓:**
```
The payment terms require net 30 days for all invoices [doc1].

The warranty period extends for 12 months from delivery date [doc2].

Indemnification clauses cover both parties for negligence claims [doc3].
```

**WRONG ✗:**
```
The payment terms require net 30 days and warranty is 12 months [doc1][doc2].
```

**WRONG ✗:**
```
Effects and warranty survival [doc1][doc2].
```

**Key Rule**: ONE paragraph = ONE citation. Multiple sources = Multiple paragraphs.

## Tools Available

You have access to the following tools to search for information:

1. **hybrid_search**: Semantic + keyword search across all documents
2. **search_by_project**: Find all documents in a specific project
3. **search_similar_documents**: Find documents similar to a given document
4. **search_by_document**: Retrieve full content of a specific document
5. **compare_filtered_documents**: Compare specific topic across multiple filtered documents

Use these tools to find relevant information before answering questions.
"""


@dataclass
class TalkToContractVanillaDependencies:
    """Dependencies for vanilla Talk To Contract Agent."""
    search_service: OpenSearchVectorSearchService
    filters: Optional[Dict[str, Any]] = None


# Tool definitions in OpenAI format
def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get OpenAI-compatible tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "hybrid_search",
                "description": "Perform hybrid search combining semantic (vector) and keyword (BM25) search. Use this for most queries about contract content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find relevant contract information"
                        },
                        "size": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_by_project",
                "description": "Retrieve all documents from a specific project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The project ID to search within"
                        },
                        "size": {
                            "type": "integer",
                            "description": "Maximum number of chunks to return",
                            "default": 100
                        }
                    },
                    "required": ["project_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_similar_documents",
                "description": "Find documents similar to a given document by record_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "record_id": {
                            "type": "string",
                            "description": "The record ID of the reference document"
                        },
                        "size": {
                            "type": "integer",
                            "description": "Maximum number of similar documents to return",
                            "default": 5
                        }
                    },
                    "required": ["record_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_by_document",
                "description": "Retrieve all chunks from a specific document.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The project ID"
                        },
                        "reference_doc_id": {
                            "type": "string",
                            "description": "The reference document ID"
                        },
                        "size": {
                            "type": "integer",
                            "description": "Maximum number of chunks to return (None = all)",
                        }
                    },
                    "required": ["project_id", "reference_doc_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "compare_filtered_documents",
                "description": "Search for a specific topic across multiple filtered documents and combine results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The topic or query to search for in each document"
                        },
                        "size_per_doc": {
                            "type": "integer",
                            "description": "Number of results to get from each document",
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]


class TalkToContractVanillaAgent:
    """Vanilla OpenAI implementation of Talk To Contract agent."""

    def __init__(
        self,
        client: AsyncOpenAI,
        search_service: OpenSearchVectorSearchService,
        model: str = "gpt-4",
        max_iterations: int = 5,
    ):
        """
        Initialize the vanilla agent.

        Args:
            client: Async OpenAI client
            search_service: OpenSearch vector search service
            model: OpenAI model to use
            max_iterations: Maximum tool call iterations
        """
        self.client = client
        self.search_service = search_service
        self.model = model
        self.max_iterations = max_iterations
        self.tools = get_tool_definitions()

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute a tool and return the result as a string."""
        logger.info(f"🔧 Executing tool: {tool_name} with args: {tool_args}")

        try:
            if tool_name == "hybrid_search":
                result = self.search_service.hybrid_search(
                    query=tool_args["query"],
                    size=tool_args.get("size", 10),
                    filters=filters,
                )
            elif tool_name == "search_by_project":
                result = self.search_service.search_by_project(
                    project_id=tool_args["project_id"],
                    size=tool_args.get("size", 100),
                    filters=filters,
                )
            elif tool_name == "search_similar_documents":
                result = self.search_service.search_similar_documents(
                    record_id=tool_args["record_id"],
                    size=tool_args.get("size", 5),
                    filters=filters,
                )
            elif tool_name == "search_by_document":
                result = self.search_service.search_by_document(
                    project_id=tool_args["project_id"],
                    reference_doc_id=tool_args["reference_doc_id"],
                    size=tool_args.get("size"),
                )
            elif tool_name == "compare_filtered_documents":
                result = self.search_service.compare_filtered_documents(
                    query=tool_args["query"],
                    size_per_doc=tool_args.get("size_per_doc", 3),
                    filters=filters,
                )
            else:
                return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})

            if result.is_ok():
                response = result.unwrap()
                context = response.to_llm_context()
                return json.dumps({"success": True, "context": context})
            else:
                error_msg = result.unwrap_err()
                logger.error(f"❌ Tool {tool_name} failed: {error_msg}")
                return json.dumps({"success": False, "error": error_msg})

        except Exception as e:
            logger.error(f"❌ Tool execution error: {e}")
            return json.dumps({"success": False, "error": str(e)})

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ResponseValidationError),
        before_sleep=before_sleep_log(logger, logger.level("WARNING").no),
        reraise=True,
    )
    async def run(
        self,
        user_query: str,
        filters: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Run the agent with vanilla OpenAI function calling.

        Includes retry logic with exponential backoff for validation errors.

        Args:
            user_query: The user's question
            filters: Optional search filters
            message_history: Optional conversation history in OpenAI format
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Returns:
            Dictionary with answer and citations

        Raises:
            ResponseValidationError: If response validation fails after max retries
        """
        logger.info(f"🚀 Running vanilla agent with query: {user_query[:100]}...")

        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add message history if provided
        if message_history:
            logger.info(f"Adding {len(message_history)} historical messages")
            messages.extend(message_history)

        # Add current user query
        messages.append({"role": "user", "content": user_query})

        # Agent loop with tool calling
        for iteration in range(self.max_iterations):
            logger.info(f"📍 Iteration {iteration + 1}/{self.max_iterations}")

            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                response_format={"type": "json_object"},
            )

            message = response.choices[0].message
            messages.append(message)

            # Check if we have tool calls
            if message.tool_calls:
                logger.info(f"🔧 Processing {len(message.tool_calls)} tool calls")

                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool
                    tool_result = await self._execute_tool(tool_name, tool_args, filters)

                    # Add tool response to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    })

                # Continue loop to get next response
                continue

            # No tool calls - check if we have a final answer
            if message.content:
                logger.info("✅ Got final response")
                try:
                    # Try to parse as JSON
                    result = json.loads(message.content)

                    # Validate required fields
                    if "answer" not in result or "citations" not in result:
                        error_msg = "Response missing required fields (answer, citations)"
                        logger.error(error_msg)
                        raise ResponseValidationError(error_msg)

                    # Validate citations format
                    citations = result.get("citations", {})
                    if not isinstance(citations, dict):
                        error_msg = f"Citations must be a dictionary, got {type(citations).__name__}"
                        logger.error(error_msg)
                        raise ResponseValidationError(error_msg)

                    # Validate citation values are strings and not placeholders
                    for key, value in citations.items():
                        if not isinstance(value, str):
                            error_msg = f"Citation value for '{key}' must be string, got {type(value).__name__}: {value}"
                            logger.error(error_msg)
                            raise ResponseValidationError(error_msg)

                        # Check for invalid placeholder values
                        if value.lower() in ["source", "doc1", "doc2", "doc3"] or value.isdigit():
                            error_msg = f"Citation value for '{key}' is invalid placeholder: '{value}'. Must be full document name."
                            logger.error(error_msg)
                            raise ResponseValidationError(error_msg)

                    # All validations passed
                    logger.info(f"✅ Response validated successfully with {len(citations)} citation(s)")
                    return {
                        "success": True,
                        "answer": result["answer"],
                        "citations": citations,
                    }

                except json.JSONDecodeError as e:
                    error_msg = f"Response is not valid JSON: {str(e)}"
                    logger.warning(error_msg)
                    raise ResponseValidationError(error_msg)

            # Should not reach here
            logger.warning("No content in message")
            break

        # Max iterations reached
        logger.error("Max iterations reached without final answer")
        return {
            "success": False,
            "error": "Max iterations reached",
            "answer": "",
            "citations": {},
        }


class TalkToContractVanillaAgentFactory:
    """Factory for creating vanilla Talk To Contract agents."""

    @staticmethod
    def create_default() -> TalkToContractVanillaAgent:
        """
        Create agent with default settings from environment.

        Returns:
            Configured vanilla agent instance
        """
        # Get OpenAI client
        factory = LLMVanillaClientFactory()
        client = factory.get_default_client(async_mode=True)

        # Get search service
        search_service = OpenSearchVectorSearchServiceFactory.create_default()

        # Get model name from settings
        settings = OpenAISettings()

        return TalkToContractVanillaAgent(
            client=client,
            search_service=search_service,
            model=settings.model,
        )

    @staticmethod
    def from_env_file(env_path: str) -> TalkToContractVanillaAgent:
        """
        Create agent from specific environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured vanilla agent instance
        """
        # Get OpenAI client
        factory = LLMVanillaClientFactory()
        client = factory.get_default_client(async_mode=True)

        # Get search service
        search_service = OpenSearchVectorSearchServiceFactory.from_env_file(env_path)

        # Get model name from settings
        settings = OpenAISettings(_env_file=env_path)

        return TalkToContractVanillaAgent(
            client=client,
            search_service=search_service,
            model=settings.model,
        )
