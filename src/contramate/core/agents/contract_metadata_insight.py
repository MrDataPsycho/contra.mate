"""Contract Metadata Insight Agent with SQL query generation.

This agent transforms natural language questions into SQL queries and executes them
against contract metadata tables:
- contract_asmd: Application Structured Metadata (clause analysis)
- contracting_esmd: Extracted Structured Metadata (financial/operational data)

Note: Not all contracts have ESMD data. Queries should use LEFT JOIN when combining
tables to include contracts with only ASMD data.
"""

import json
from loguru import logger
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from contramate.dbs.adapters.postgres_metadata_adapter import PostgresMetadataAdapter
from contramate.dbs.models.contract import ContractAsmd, ContractEsmd
from contramate.llm import LLMVanillaClientFactory
from contramate.utils.settings.core import OpenAISettings, PostgresSettings
from contramate.utils.schema_generator import generate_sql_schema_prompt


class ResponseValidationError(Exception):
    """Raised when LLM response doesn't match expected format."""
    pass


# System prompt with schema documentation
SYSTEM_PROMPT = """
## Role & Context

You are a contract analytics assistant specializing in SQL-based data analysis. You help users extract insights from contract metadata by generating and executing SQL queries against a PostgreSQL database.

Your capabilities include:
- Generating SQL queries based on natural language questions
- Aggregating contract statistics (counts, averages, distributions)
- Filtering contracts by various criteria
- Analyzing contract clauses, financial terms, and operational details
- Comparing contract types and terms across both structured and extracted metadata
- Joining data across multiple tables for comprehensive analysis

## Database Schema

You have access to TWO contract metadata tables:

{schema}

## Available Tool

**execute_sql_query**: Execute a SELECT SQL query and return results as JSON

This is the ONLY tool available. Use it for:
- Counting contracts
- Aggregating by any field
- Filtering by clauses, dates, financial terms
- Finding specific contracts
- Comparing contract types
- Analyzing trends and distributions
- Joining ASMD and ESMD tables for comprehensive insights

## SQL Query Guidelines

**CRITICAL SAFETY RULES:**
1. ✅ **ONLY SELECT queries allowed** - No INSERT, UPDATE, DELETE, DROP, ALTER, CREATE
2. ✅ **MUST have WHERE or LIMIT (or both)** - Every query MUST include either a WHERE clause, a LIMIT clause, 
   or both. Queries without any filtering or limiting WILL BE REJECTED to prevent pulling entire tables.
3. ✅ **Handle NULLs properly** - Use `IS NULL` / `IS NOT NULL`
4. ✅ **Use answer fields for clauses** - Fields ending in `_answer` for Yes/No values
5. ✅ **JOIN on composite key** - Use (project_id, reference_doc_id) to join tables
6. ✅ **Use LEFT JOIN for ESMD** - Not all contracts have ESMD data, use LEFT JOIN to include ASMD-only contracts
7. ✅ **Check for NULL ESMD fields** - ESMD columns will be NULL if no financial/operational data exists
8. ✅ **Apply filters when contextually appropriate** - If the user mentions specific projects, contract types, 
   or documents, include those in WHERE clauses. You have the intelligence to determine when filters make sense.
9. ✅ **Prefer WHERE + LIMIT together** - Best practice is to use both WHERE (for filtering) and LIMIT (for safety)
10. ❌ **NEVER modify data** - Read-only access only
11. ❌ **NEVER use dangerous keywords** - No DROP, DELETE, INSERT, UPDATE, etc.

**Query Best Practices:**
- **Always include WHERE or LIMIT**: Every query needs at least one (preferably both)
- **Be specific**: Query only the columns you need for better performance
- **Filter intelligently**: When users ask about specific contracts, projects, or types, add WHERE filters
- **Use aggregation**: For counts and summaries, use COUNT(), GROUP BY, and aggregate functions
- **Combine WHERE + LIMIT**: `SELECT ... FROM table WHERE condition LIMIT 100` is the safest pattern

**IMPORTANT: ESMD Data Availability**
- **Not all contracts have ESMD data** - Some contracts only have ASMD (clause analysis)
- **Always use LEFT JOIN** when joining ASMD with ESMD to include all contracts
- **Use INNER JOIN only** when you specifically need contracts with both ASMD AND ESMD data
- **Check for NULL** - ESMD fields will be NULL for contracts without financial/operational extraction

**Example Queries:**

```sql
-- Example 1: Count contracts by type (ASMD table)
SELECT contract_type, COUNT(*) as count
FROM contract_asmd
WHERE contract_type IS NOT NULL
GROUP BY contract_type
ORDER BY count DESC
LIMIT 100;

-- Example 2: Find contracts with non-compete clauses (ASMD table)
SELECT project_id, reference_doc_id, document_title, 
       contract_type, non_compete_answer
FROM contract_asmd
WHERE non_compete_answer = 'Yes'
LIMIT 100;

-- Example 3: Financial analysis from ESMD table
SELECT contract_type, 
       COUNT(*) as contract_count,
       COUNT(total_contract_value) as with_value,
       COUNT(payment_schedule) as with_schedule
FROM contracting_esmd
WHERE contract_type IS NOT NULL
GROUP BY contract_type
LIMIT 100;

-- Example 4: LEFT JOIN for comprehensive view (ESMD may not exist for all contracts)
-- IMPORTANT: Use LEFT JOIN since not all contracts have ESMD data
SELECT 
    a.document_title,
    a.contract_type,
    a.parties_answer,
    a.non_compete_answer,
    a.exclusivity_answer,
    e.total_contract_value,
    e.payment_schedule,
    e.deliverables_activities
FROM contract_asmd a
LEFT JOIN contracting_esmd e 
    ON a.project_id = e.project_id 
    AND a.reference_doc_id = e.reference_doc_id
WHERE a.contract_type = 'Service Agreement'
LIMIT 100;

-- Example 5: Contracts with IP provisions, include ESMD if available
-- Note: ESMD fields will be NULL if no financial data extracted
SELECT 
    a.document_title,
    a.ip_ownership_assignment_answer,
    a.license_grant_answer,
    e.total_contract_value,
    e.total_direct_fees,
    CASE 
        WHEN e.reference_doc_id IS NULL THEN 'No ESMD data'
        ELSE 'Has ESMD data'
    END as esmd_status
FROM contract_asmd a
LEFT JOIN contracting_esmd e
    ON a.project_id = e.project_id 
    AND a.reference_doc_id = e.reference_doc_id
WHERE a.ip_ownership_assignment_answer = 'Yes'
   OR a.license_grant_answer = 'Yes'
LIMIT 100;

-- Example 6: Only contracts that have both ASMD and ESMD data
-- Use INNER JOIN when you specifically need both datasets
SELECT 
    a.document_title,
    a.contract_type,
    a.parties_answer,
    e.total_contract_value,
    e.deliverables_activities
FROM contract_asmd a
INNER JOIN contracting_esmd e 
    ON a.project_id = e.project_id 
    AND a.reference_doc_id = e.reference_doc_id
WHERE a.contract_type = 'Service Agreement'
  AND e.total_contract_value IS NOT NULL
LIMIT 100;
```

## Response Format

**REQUIRED OUTPUT STRUCTURE - JSON ONLY:**
You MUST return a valid JSON object with TWO fields:
1. `answer` (string, required): Your complete answer with inline citations
2. `citations` (object, required): A dictionary mapping citation keys to data sources

**Citation Format:**
- **ALWAYS include [doc1], [doc2], etc. directly in your answer text**
- Citations reference the source table(s) queried
- Format for ASMD: `"Database: contract_asmd table (Application Structured Metadata)"`
- Format for ESMD: `"Database: contracting_esmd table (Extracted Structured Metadata)"`
- Format for JOINs: `"Database: contract_asmd and contracting_esmd tables (joined analysis)"`

**CRITICAL: Your answer MUST contain inline citation markers like [doc1] in the text itself!**

**Example Response:**
{{
  "answer": "Found 45 contracts with non-compete clauses [doc1]. The most common types are Service Agreements (20) and Employment Agreements (15) [doc1]. These represent 30% of all analyzed contracts.",
  "citations": {{
    "doc1": "Database: contract_asmd table (Application Structured Metadata - clause analysis)"
  }}
}}

**Example with Financial Data:**
{{
  "answer": "Analyzed 32 Service Agreements with financial details [doc1].\\n\\nThe total contract values range from $50K to $2M, with an average of $450K [doc1]. Payment schedules are defined for 28 out of 32 contracts (87.5%) [doc1].",
  "citations": {{
    "doc1": "Database: contracting_esmd table (Extracted Structured Metadata - financial analysis)"
  }}
}}

**Example with JOIN:**
{{
  "answer": "Found 18 contracts with both IP ownership provisions and cost data [doc1].\\n\\nOf these, 12 assign IP rights to the client, with contract values averaging $780K [doc1]. The remaining 6 retain joint ownership, averaging $320K [doc1].",
  "citations": {{
    "doc1": "Database: contract_asmd and contracting_esmd tables (combined clause and financial analysis)"
  }}
}}

**CRITICAL Citation Rules:**
1. **ALWAYS include citations field** - Never return without citations
2. **One citation per paragraph** - NO `[doc1][doc2]` combinations
3. **Reference the queried table(s)** - Be specific about ASMD, ESMD, or JOIN
4. **Be descriptive** - Include what type of analysis was performed

## Important Notes

- **Answer fields in ASMD**: Use `*_answer` columns for Yes/No clause indicators
- **Raw fields in ASMD**: Fields without `_answer` are extracted text (longer, less structured)
- **ESMD financial fields**: Most fields are strings with descriptions (not normalized)
- **⚠️ ESMD data may be missing**: Not all contracts have ESMD records - always use LEFT JOIN when combining tables
- **NULL handling**: Many optional fields are NULL - always check with IS NULL / IS NOT NULL
- **Data quality**: Not all contracts have all fields populated
- **Performance**: ALWAYS use LIMIT clause (default 100, max 1000)
- **JOIN key**: Use (project_id, reference_doc_id) to join ASMD and ESMD tables
- **ASMD always exists**: Every contract has ASMD data (clause analysis), but ESMD (financial) is optional

## Error Handling

If query execution fails:
1. Acknowledge the error
2. Explain what went wrong
3. Suggest an alternative query or approach
4. Never expose sensitive error details to users
"""


@dataclass
class ContractMetadataInsightDependencies:
    """Dependencies for ContractMetadataInsight agent."""

    db_adapter: PostgresMetadataAdapter
    filters: Optional[Dict[str, Any]] = None


# Tool definitions in OpenAI format
def get_tool_definitions() -> List[Dict[str, Any]]:
    """Get OpenAI-compatible tool definitions for SQL operations."""
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_sql_query",
                "description": """Execute a SELECT SQL query against contract metadata tables (contract_asmd and contracting_esmd).
                
CRITICAL SAFETY RULES:
- ONLY SELECT queries allowed (no INSERT, UPDATE, DELETE, DROP, ALTER, etc.)
- Always use LIMIT clause to prevent large result sets (max 1000)
- Use parameterized queries when needed (though user input will be validated)
- Query both tables: contract_asmd (Application Structured Metadata) and contracting_esmd (Extracted Structured Metadata)
- Can use JOINs across tables on project_id and reference_doc_id

AVAILABLE TABLES:
1. contract_asmd - Structured clause analysis (60+ fields for clauses, dates, parties, etc.)
2. contracting_esmd - Financial and operational metadata (costs, deliverables, milestones, etc.)

Use this tool for ALL queries: counts, aggregations, filtering, joins, analysis, etc.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SELECT SQL query to execute. Must be read-only. Include LIMIT clause.",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query does (for logging/debugging)",
                        },
                    },
                    "required": ["query", "explanation"],
                },
            },
        }
    ]


class ContractMetadataInsightAgent:
    """SQL-based agent for contract metadata analysis."""

    def __init__(
        self,
        client: AsyncOpenAI,
        db_adapter: PostgresMetadataAdapter,
        model: str = "gpt-4",
        max_iterations: int = 5,
    ):
        """
        Initialize ContractMetadataInsight agent.

        Args:
            client: OpenAI async client
            db_adapter: PostgreSQL metadata adapter for query execution
            model: OpenAI model name
            max_iterations: Maximum tool calling iterations
        """
        self.client = client
        self.db_adapter = db_adapter
        self.model = model
        self.max_iterations = max_iterations
        self.tools = get_tool_definitions()

        # Generate schema documentation for both tables
        asmd_schema = generate_sql_schema_prompt(ContractAsmd)
        esmd_schema = generate_sql_schema_prompt(ContractEsmd)
        
        # Combine schemas
        combined_schema = f"""### Table 1: contract_asmd (Application Structured Metadata Data)
{asmd_schema}

### Table 2: contracting_esmd (Extracted Structured Metadata Data)
{esmd_schema}

**Relationship:** Both tables share composite primary key (project_id, reference_doc_id) - use for JOINs."""
        
        self.system_prompt = SYSTEM_PROMPT.format(schema=combined_schema)

    async def _execute_tool(
        self, tool_name: str, tool_args: Dict[str, Any], filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute SQL query tool and return formatted results.

        Args:
            tool_name: Name of the tool (should be 'execute_sql_query')
            tool_args: Tool arguments with 'query' and 'explanation'
            filters: Optional global filters to apply (project_id, contract_type)

        Returns:
            JSON string with query results
        """
        try:
            if tool_name != "execute_sql_query":
                error_msg = f"Unknown tool: {tool_name}. Only 'execute_sql_query' is supported."
                logger.error(error_msg)
                return json.dumps({"success": False, "error": error_msg})

            query = tool_args["query"]
            explanation = tool_args.get("explanation", "No explanation provided")
            
            logger.info(f"🔍 Query explanation: {explanation}")
            logger.info(f"📝 SQL query: {query}")

            # Validate query is SELECT only
            query_upper = query.strip().upper()
            if not query_upper.startswith("SELECT"):
                error_msg = "Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, DROP, etc."
                logger.error(error_msg)
                return json.dumps({"success": False, "error": error_msg})

            # Check for dangerous keywords
            dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    error_msg = f"Dangerous keyword '{keyword}' detected. Only SELECT queries allowed."
                    logger.error(error_msg)
                    return json.dumps({"success": False, "error": error_msg})

            # GUARDRAIL: Require either WHERE clause or LIMIT clause (or both)
            # This prevents queries that could return entire tables
            has_where = "WHERE" in query_upper
            has_limit = "LIMIT" in query_upper
            
            if not has_where and not has_limit:
                error_msg = (
                    "REJECTED: All SELECT queries must include either a WHERE clause or a LIMIT clause "
                    "(or both) to prevent pulling entire tables. "
                    "Please add filtering conditions or a LIMIT."
                )
                logger.error(error_msg)
                return json.dumps({"success": False, "error": error_msg})
            
            if not has_limit:
                logger.warning("⚠️ Query has WHERE clause but no LIMIT - consider adding LIMIT for performance")

            # Ensure LIMIT is present (max 1000)
            if "LIMIT" not in query_upper:
                query = f"{query.rstrip(';')} LIMIT 100"
                logger.info("⚠️ Added default LIMIT 100 to query")
            else:
                # Validate LIMIT value isn't too high
                import re
                limit_match = re.search(r"LIMIT\s+(\d+)", query_upper)
                if limit_match and int(limit_match.group(1)) > 1000:
                    error_msg = "LIMIT cannot exceed 1000 rows for safety"
                    logger.error(error_msg)
                    return json.dumps({"success": False, "error": error_msg})

            # Execute query
            logger.info(f"⚡ Executing SQL query...")
            results = await self.db_adapter.execute_query(query)
            logger.info(f"✅ Query returned {len(results)} rows")

            return json.dumps(
                {
                    "success": True,
                    "row_count": len(results),
                    "data": results,
                    "query": query,
                    "explanation": explanation,
                },
                default=str,
            )

        except Exception as e:
            logger.error(f"❌ Error executing SQL query: {e}", exc_info=True)
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
        Run the agent with SQL query generation and execution.

        Args:
            user_query: Natural language question about contracts
            filters: Optional filters (project_id, contract_type)
            message_history: Optional conversation history

        Returns:
            Dictionary with answer, SQL query, and result summary
        """
        logger.info(f"🚀 Running ContractMetadataInsight agent with query: {user_query[:100]}...")

        # Build messages
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add message history if provided
        if message_history:
            logger.info(f"Adding {len(message_history)} historical messages")
            messages.extend(message_history)

        # Add current user query
        messages.append({"role": "user", "content": user_query})

        # Track total tokens
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0

        # Agent loop with tool calling
        for iteration in range(self.max_iterations):
            logger.info(f"📍 Iteration {iteration + 1}/{self.max_iterations}")

            # Call OpenAI with temperature and seed from settings
            openai_settings = OpenAISettings()
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                response_format={"type": "json_object"},
                temperature=openai_settings.temperature,
                seed=openai_settings.seed,
            )

            # Track token usage
            if response.usage:
                total_prompt_tokens += response.usage.prompt_tokens
                total_completion_tokens += response.usage.completion_tokens
                total_tokens += response.usage.total_tokens
                logger.info(
                    f"🔢 Tokens - Prompt: {response.usage.prompt_tokens}, "
                    f"Completion: {response.usage.completion_tokens}, "
                    f"Total: {response.usage.total_tokens}"
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
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result,
                        }
                    )

                # Continue loop to get next response
                continue

            # No tool calls - check if we have a final answer
            if message.content:
                logger.info("✅ Got final response")
                try:
                    # Try to parse as JSON
                    result = json.loads(message.content)

                    # Validate required fields (same as TalkToContractVanillaAgent)
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
                        # Accept "Database:" prefix for contract metadata queries
                        if not value.startswith("Database:") and (
                            value.lower() in ["source", "doc1", "doc2", "doc3"] or value.isdigit()
                        ):
                            error_msg = f"Citation value for '{key}' is invalid placeholder: '{value}'. Must be 'Database: [description]' format."
                            logger.error(error_msg)
                            raise ResponseValidationError(error_msg)

                    # All validations passed
                    logger.info(f"✅ Response validated successfully with {len(citations)} citation(s)")
                    logger.info(
                        f"📊 Total tokens used - Prompt: {total_prompt_tokens}, "
                        f"Completion: {total_completion_tokens}, Total: {total_tokens}"
                    )

                    # Return in same format as TalkToContractVanillaAgent
                    return {
                        "success": True,
                        "answer": result["answer"],
                        "citations": citations,
                    }

                except json.JSONDecodeError as e:
                    error_msg = f"Response is not valid JSON: {str(e)}"
                    logger.error(error_msg)
                    raise ResponseValidationError(error_msg)

            # No content and no tool calls - unexpected
            logger.warning("No content or tool calls in response")
            break

        # Max iterations reached
        logger.error("Max iterations reached without getting final answer")
        return {
            "success": False,
            "error": "Max iterations reached",
            "answer": "I apologize, but I couldn't generate a complete answer within the allowed iterations.",
            "citations": {},
        }


class ContractMetadataInsightAgentFactory:
    """Factory for creating ContractMetadataInsightAgent instances."""

    @staticmethod
    def create_default(
        model: Optional[str] = None, max_iterations: int = 5
    ) -> ContractMetadataInsightAgent:
        """
        Create agent with default OpenAI settings.

        Args:
            model: OpenAI model name (if None, uses model from OpenAI settings)
            max_iterations: Maximum tool calling iterations

        Returns:
            Configured ContractMetadataInsightAgent instance
        """
        openai_settings = OpenAISettings()
        postgres_settings = PostgresSettings()

        # Use model from settings if not explicitly provided
        model_name = model if model is not None else openai_settings.model
        logger.info(f"🤖 Creating agent with model: {model_name}")

        # Create async OpenAI client using factory
        client_factory = LLMVanillaClientFactory()
        client = client_factory.get_default_client(async_mode=True)
        db_adapter = PostgresMetadataAdapter(postgres_settings)

        return ContractMetadataInsightAgent(
            client=client, db_adapter=db_adapter, model=model_name, max_iterations=max_iterations
        )

    @staticmethod
    def from_env_file(
        env_path: str, model: Optional[str] = None, max_iterations: int = 5
    ) -> ContractMetadataInsightAgent:
        """
        Create agent from environment file.

        Args:
            env_path: Path to .env file
            model: OpenAI model name (if None, uses model from OpenAI settings)
            max_iterations: Maximum tool calling iterations

        Returns:
            Configured ContractMetadataInsightAgent instance
        """
        openai_settings = OpenAISettings.from_env_file(env_path)
        postgres_settings = PostgresSettings.from_env_file(env_path)

        # Use model from settings if not explicitly provided
        model_name = model if model is not None else openai_settings.model
        logger.info(f"🤖 Creating agent with model: {model_name} from {env_path}")

        # Create async OpenAI client using factory with env file
        client_factory = LLMVanillaClientFactory.from_env_file(env_path)
        client = client_factory.get_default_client(async_mode=True)
        db_adapter = PostgresMetadataAdapter(postgres_settings)

        return ContractMetadataInsightAgent(
            client=client, db_adapter=db_adapter, model=model_name, max_iterations=max_iterations
        )
