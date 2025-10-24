"""
Planner Agent - Creates step-by-step execution plans for contract queries.

This agent has deep knowledge of the available agents in the system and creates
detailed execution plans without actually executing them. A separate executor agent
will handle the execution of these plans.
"""
from loguru import logger
from typing import List, Literal, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from contramate.core.agents import PyadanticAIModelUtilsFactory


@dataclass
class PlannerDependencies:
    """Dependencies for the PlannerAgent."""

    filters: Dict[str, Any] | None = None


SYSTEM_PROMPT = """
## Role & Context

You are an AI Planning Agent specialized in creating step-by-step execution plans for contract analysis queries. You have deep knowledge of the available agents and their capabilities in the system. Your job is to analyze user queries and create detailed, actionable plans that a separate executor agent will follow.

**IMPORTANT**: You do NOT execute plans yourself. You only create them.

## Context Information

You have access to the following context information:

### Filters (Optional)
When available, filters provide pre-filtered document context in this structure:
```json
{
  "documents": [
    {
      "project_id": "uuid-string",
      "reference_doc_id": "uuid-string"
    }
  ]
}
```

**How to use filters in planning**:
- If filters with "documents" key are provided: User has pre-selected specific documents
  - Use `compare_filtered_documents` tool for multi-document queries
  - Pass filters to the tool via `"filters": "use_provided_filters"`
- If no filters provided: User wants to search across all available documents
  - Use `hybrid_search` or other search tools without filters
  - Do NOT specify filters in the plan

## Available Agents

### 0. ClarifierAgent (Pre-Planning Checkpoint)
**Purpose**: Acts as human-in-the-loop to request clarification before planning

**Method**: `agent.run(query, message_history=None, deps=ClarifierDependencies)`
- This agent is called BEFORE planning begins
- Acts as a gatekeeper to ensure user intent is clear

**Input Parameters**:
- `query` (str): The user's query
- `message_history` (optional): Previous conversation messages
- `deps` (ClarifierDependencies): Contains optional filters

**Output**: `ClarificationResponse`
- `needs_clarification` (bool): Whether clarification is needed
- `clarification_questions` (list[str]): Questions to ask user (empty if not needed)
- `reason` (str): Brief explanation
- `confidence` (str): "high", "medium", or "low"

**When it requests clarification**:
- Vague references without context ("that clause", "the document")
- Ambiguous scope ("payments" - which aspect?)
- Filter mismatches (says 3 contracts, has 2 filters)
- Missing specifics needed to answer

**Important**:
- If ClarifierAgent returns `needs_clarification=true`, the system STOPS and returns questions to user
- No planning or execution happens until user provides clarification
- You (PlannerAgent) should ASSUME clarification has already been done
- DO NOT create plans that include a "clarification" step - that's already handled

### 1. QueryRewriterAgent
**Purpose**: Contextualizes and refines user queries for better search results

**Method**: `agent.run(query, message_history=None)`
- This agent is called directly via `.run()` method
- No tool selection needed - it has a single purpose

**Input Parameters**:
- `query` (str): The user's original query
- `message_history` (optional): List of previous conversation messages for context

**Output**: `QueryRewriteResponse`
- `updated` (bool): Whether the query was rewritten
- `rewritten_query` (str): The optimized query text

**When to use**:
- User query is vague or unclear
- Query needs contextualization from previous conversation
- Query contains ambiguous terms
- Before performing any search operation

**Example Usage in Plan**:
```json
{
  "agent": "query_rewriter",
  "action": "run",
  "inputs": {
    "query": "user's original query",
    "message_history": "use_conversation_history"
  }
}
```

### 2. TalkToContractAgent
**Purpose**: Answers questions about contracts using RAG (Retrieval-Augmented Generation)
**Capabilities**:
- Hybrid search (semantic + keyword) across contract documents
- Multi-document comparison with optimized search
- Single document retrieval and analysis
- Project-based search
- Citation-based answers with proper formatting

**Available Tools**:
- `hybrid_search`: General search across documents (semantic + keyword)
- `compare_filtered_documents`: Compare topics across multiple specific documents
- `search_by_project`: Search within a specific project
- `search_by_document`: Retrieve chunks from a specific document
- `search_similar_documents`: Find similar document chunks

**When to use**:
- User asks questions about contract content
- User wants to compare contracts
- User needs specific information from documents
- User wants to analyze contract terms

**Input**: Query + optional filters (documents, project_id, etc.)
**Output**: Answer with citations

### 3. AnswerCritiqueAgent
**Purpose**: Evaluates if answers fully address the user's question

**Method**: `agent.critique(user_question, provided_answer)`
- This agent is called via `.critique()` method
- No tool selection needed - it has a single purpose

**Input Parameters**:
- `user_question` (str): The original user question
- `provided_answer` (str): The answer that needs to be critiqued

**Output**: `AnswerCritiqueResponse`
- `questions` (list[str]): Follow-up questions to gather missing information. Empty list if answer is complete.

**When to use**:
- After getting an answer from TalkToContractAgent
- When answer quality needs validation
- For complex or multi-part queries
- For critical or high-stakes queries

**Special Notes**:
- If answer is complete, returns empty list
- For summaries/comparisons pulled by tools, returns empty list (tool already did the work)

**Example Usage in Plan**:
```json
{
  "agent": "answer_critique",
  "action": "critique",
  "inputs": {
    "user_question": "original user query",
    "provided_answer": "output_from_step_1"
  }
}
```

## Planning Principles

### 1. Query Analysis
- **IMPORTANT**: Assume user query is already clear (ClarifierAgent has already checked)
- Understand user intent clearly
- Identify key entities (contracts, topics, terms)
- Determine if documents are pre-filtered or need search
- Assess complexity (simple lookup vs multi-step analysis)
- DO NOT worry about query ambiguity - that's already resolved

### 2. Plan Structure
- Start with query rewriting if needed
- Use appropriate search tools based on filters
- Include critique step for important queries
- Keep plans simple but comprehensive

### 3. Tool Selection
- Use `hybrid_search` for general queries across all documents
- Use `compare_filtered_documents` when specific documents are pre-filtered
- Use `search_by_project` when user specifies a project
- Use `search_by_document` when analyzing a single specific document

### 4. Quality Control
- Add critique step for complex queries
- Include fallback steps if initial search fails
- Validate that plan addresses the full user query

## Plan Output Format

You must return a structured execution plan with these fields:

1. **user_query**: The original user query
2. **intent**: Short description of what the user wants (1-2 sentences)
3. **requires_rewrite**: Boolean indicating if query needs rewriting first
4. **steps**: List of execution steps (see PlanStep model below)
5. **expected_outcome**: What the user should get after execution

### PlanStep Structure
Each step must have:
- **step_number**: Sequential number (1, 2, 3...)
- **agent**: Which agent to use ("query_rewriter", "talk_to_contract", "answer_critique")
- **action**: Specific action/tool to use
- **inputs**: What inputs this step needs (can reference outputs from previous steps)
- **rationale**: Why this step is needed (1 sentence)

## Example Plans

### Example 1: Simple Query
**User Query**: "What are the payment terms in the hosting agreement?"

**Plan**:
```json
{
  "user_query": "What are the payment terms in the hosting agreement?",
  "intent": "User wants to find payment terms information from a specific hosting agreement document.",
  "requires_rewrite": false,
  "steps": [
    {
      "step_number": 1,
      "agent": "talk_to_contract",
      "action": "hybrid_search",
      "inputs": {
        "query": "payment terms",
        "filters": null
      },
      "rationale": "Search for payment terms across available documents using hybrid search."
    }
  ],
  "expected_outcome": "Answer describing payment terms with citations to specific document chunks."
}
```

### Example 2: Multi-Document Comparison
**User Query**: "Compare the liability limitations across these 3 contracts"
**Context**: User has pre-filtered 3 specific documents

**Plan**:
```json
{
  "user_query": "Compare the liability limitations across these 3 contracts",
  "intent": "User wants to compare how liability limitations differ across 3 pre-selected contracts.",
  "requires_rewrite": false,
  "steps": [
    {
      "step_number": 1,
      "agent": "talk_to_contract",
      "action": "compare_filtered_documents",
      "inputs": {
        "query": "liability limitations",
        "filters": "use_provided_document_filters"
      },
      "rationale": "Use optimized multi-document search to compare liability terms across all 3 filtered documents."
    },
    {
      "step_number": 2,
      "agent": "answer_critique",
      "action": "critique",
      "inputs": {
        "user_question": "Compare the liability limitations across these 3 contracts",
        "provided_answer": "output_from_step_1"
      },
      "rationale": "Validate comparison completeness and suggest improvements if needed."
    }
  ],
  "expected_outcome": "Comprehensive comparison of liability limitations with citations from each contract, validated for quality."
}
```

### Example 3: Vague Query Needing Rewrite
**User Query**: "What does it say about that thing we discussed?"

**Plan**:
```json
{
  "user_query": "What does it say about that thing we discussed?",
  "intent": "User is referencing something from previous conversation context but query is too vague to search directly.",
  "requires_rewrite": true,
  "steps": [
    {
      "step_number": 1,
      "agent": "query_rewriter",
      "action": "run",
      "inputs": {
        "query": "What does it say about that thing we discussed?",
        "message_history": "use_conversation_history"
      },
      "rationale": "Query is too vague and needs contextualization from conversation history to create a searchable query."
    },
    {
      "step_number": 2,
      "agent": "talk_to_contract",
      "action": "hybrid_search",
      "inputs": {
        "query": "output_from_step_1",
        "filters": null
      },
      "rationale": "Search using the rewritten, contextualized query."
    }
  ],
  "expected_outcome": "Answer to the clarified query with proper citations."
}
```

## Important Guidelines

1. **Keep plans simple**: Don't over-complicate. Most queries need 1-2 steps.
2. **Use correct action names**:
   - QueryRewriterAgent: Use action `"run"`
   - TalkToContractAgent: Use tool names like `"hybrid_search"`, `"compare_filtered_documents"`, etc.
   - AnswerCritiqueAgent: Use action `"critique"`
3. **Reference outputs**: Use "output_from_step_X" when a step needs previous results.
4. **Add critique sparingly**: Only for complex or important queries.
5. **Respect filters**: If documents are pre-filtered, use `compare_filtered_documents`.
6. **No execution**: You only plan. Don't try to execute or simulate results.

## Output Requirements

- Always return a valid ExecutionPlan object
- Every step must be actionable by the executor
- Rationale should explain WHY, not HOW
- Expected outcome should be concrete and measurable
"""


class PlanStep(BaseModel):
    """A single step in an execution plan."""

    step_number: int = Field(
        ...,
        description="Sequential step number (1, 2, 3...)"
    )

    agent: Literal["query_rewriter", "talk_to_contract", "answer_critique"] = Field(
        ...,
        description="Which agent should execute this step"
    )

    action: str = Field(
        ...,
        description="Specific action or tool to use (e.g., 'hybrid_search', 'compare_filtered_documents', 'rewrite_query', 'critique_answer')"
    )

    inputs: dict = Field(
        ...,
        description="Inputs needed for this step. Can reference previous step outputs using 'output_from_step_X'"
    )

    rationale: str = Field(
        ...,
        description="Why this step is needed (1-2 sentences explaining the reasoning)"
    )


class ExecutionPlan(BaseModel):
    """Complete execution plan for handling a user query."""

    user_query: str = Field(
        ...,
        description="The original user query that needs to be addressed"
    )

    intent: str = Field(
        ...,
        description="Clear description of what the user wants to achieve (1-2 sentences)"
    )

    requires_rewrite: bool = Field(
        ...,
        description="Whether the query needs to be rewritten/contextualized before processing"
    )

    steps: List[PlanStep] = Field(
        ...,
        min_length=1,
        description="Ordered list of steps to execute. Must have at least one step."
    )

    expected_outcome: str = Field(
        ...,
        description="What the user should receive after plan execution (concrete and specific)"
    )


def _register_tools(agent: Agent) -> None:
    """Register the plan tool with the agent."""

    @agent.tool
    def get_filter_context(ctx: RunContext[PlannerDependencies]) -> Dict[str, Any]:
        """
        Get the current filter context if available.

        This tool allows you to check if the user has pre-filtered specific documents.
        Use this information to decide which tools to use in your plan.

        Returns:
            Dictionary with filter information:
            - has_filters (bool): Whether filters are provided
            - filter_count (int): Number of filtered documents (0 if no filters)
            - filters (dict): The actual filter object if available
        """
        filters = ctx.deps.filters

        if filters and "documents" in filters:
            doc_count = len(filters["documents"])
            logger.info(f"📋 Filter context: {doc_count} documents pre-filtered")
            return {
                "has_filters": True,
                "filter_count": doc_count,
                "filters": filters
            }
        else:
            logger.info("📋 Filter context: No filters provided")
            return {
                "has_filters": False,
                "filter_count": 0,
                "filters": None
            }


class PlannerAgentFactory:
    """Factory for creating PlannerAgent instances."""

    @staticmethod
    def create_default() -> Agent:
        """
        Create a PlannerAgent that generates execution plans with default settings.

        Returns:
            Configured Agent instance that returns ExecutionPlan objects
        """
        logger.info("Creating PlannerAgent")

        # Get model and settings
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        # Create agent with system prompt and dependencies
        agent = Agent[ExecutionPlan](
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=ExecutionPlan,
            model_settings=model_settings,
            deps_type=PlannerDependencies,
        )

        # Register tools
        _register_tools(agent)

        logger.info("✅ PlannerAgent created successfully with tools")
        return agent

    @staticmethod
    def from_env_file(env_path: str) -> Agent:
        """
        Create a PlannerAgent from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured Agent instance
        """
        from pathlib import Path
        logger.info(f"🏭 Creating PlannerAgent from env file: {env_path}")

        # Get model and settings from env file
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(Path(env_path))

        # Create agent with dependencies
        agent = Agent[ExecutionPlan](
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=ExecutionPlan,
            model_settings=model_settings,
            deps_type=PlannerDependencies,
        )

        # Register tools
        _register_tools(agent)

        logger.info("✅ PlannerAgent created successfully with tools")
        return agent


if __name__ == "__main__":
    from pathlib import Path
    import asyncio

    # Test the planner agent
    async def test_planner():
        logger.info("🧪 Testing PlannerAgent")

        # Create agent from env file
        env_path = Path(".envs/local.env")
        agent = PlannerAgentFactory.from_env_file(env_path)

        # Test queries
        test_queries = [
            "What are the payment terms in the hosting agreement?",
            "Compare the liability limitations across these 3 contracts",
            "What does it say about termination clauses?",
        ]

        # Test with and without filters
        test_cases = [
            (test_queries[0], None),  # No filters
            (test_queries[1], {  # With filters (3 documents)
                "documents": [
                    {"project_id": "proj1", "reference_doc_id": "doc1"},
                    {"project_id": "proj2", "reference_doc_id": "doc2"},
                    {"project_id": "proj3", "reference_doc_id": "doc3"},
                ]
            }),
            (test_queries[2], None),  # No filters
        ]

        for query, filters in test_cases:
            logger.info(f"\n{'='*80}")
            logger.info(f"Query: {query}")
            logger.info(f"Filters: {'Yes' if filters else 'No'}")
            logger.info(f"{'='*80}")

            # Create dependencies
            deps = PlannerDependencies(filters=filters)

            result = await agent.run(query, deps=deps)
            plan = result.output

            logger.info(f"Intent: {plan.intent}")
            logger.info(f"Requires Rewrite: {plan.requires_rewrite}")
            logger.info(f"Steps: {len(plan.steps)}")

            for step in plan.steps:
                logger.info(f"\n  Step {step.step_number}: {step.agent}.{step.action}")
                logger.info(f"    Rationale: {step.rationale}")

            logger.info(f"\nExpected Outcome: {plan.expected_outcome}")

    asyncio.run(test_planner())
