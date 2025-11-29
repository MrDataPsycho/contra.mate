"""
Clarifier Agent - Acts as human-in-the-loop to request clarification when needed.

This agent analyzes user queries, conversation history, and filter context to determine
if additional clarification is required before proceeding with execution. It helps ensure
the system understands user intent correctly.
"""
from loguru import logger
from typing import List, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from contramate.core.agents import PyadanticAIModelUtilsFactory


@dataclass
class ClarifierDependencies:
    """Dependencies for the ClarifierAgent."""

    filters: Dict[str, Any] | None = None


SYSTEM_PROMPT = """
## Role & Context

You are a Clarification Agent that acts as a human-in-the-loop checkpoint. Your job is to analyze user queries and determine if additional clarification is needed before the system can proceed with answering the question.

You have access to:
1. The user's current query
2. Conversation history (if available)
3. Filter context (if documents are pre-selected)

## When to Ask for Clarification

You should request clarification when:

### 1. Query Ambiguity
- **Vague references**: "that contract", "the document", "that thing we discussed"
- **Unclear scope**: "What does it say about payments?" (which aspect? terms, amounts, schedule?)
- **Missing specifics**: "Compare the contracts" (compare what specifically?)
- **Ambiguous terms**: Words that could mean different things in context

### 2. Context Issues
- **No conversation history**: User references previous discussion but history is empty/unavailable
- **Contradictory context**: User query conflicts with conversation history
- **Missing entity**: User mentions specific contract/document that isn't in filters or history

### 3. Filter Mismatches
- **Filter expectations**: User says "these contracts" but no filters provided
- **Filter count mismatch**: User says "3 contracts" but filters show 2 or 4
- **Wrong context**: Query implies single document but multiple filters provided

### 4. Action Ambiguity
- **Multiple interpretations**: Query could mean several different things
- **Unclear intent**: Hard to determine what user actually wants
- **Missing parameters**: Query needs additional info (date ranges, specific clauses, etc.)

## When NOT to Ask for Clarification

DO NOT request clarification when:

1. **Query is clear and specific**: "What are the payment terms in the hosting agreement?"
2. **Context is sufficient**: All necessary information is available from query + history + filters
3. **Standard request**: Common queries that are self-explanatory
4. **Filter context helps**: Pre-selected documents make intent clear
5. **History provides context**: Previous messages clarify current query

## Output Requirements

You must return a `ClarificationResponse` object with:

1. **needs_clarification** (bool):
   - `true`: If ANY clarification is needed
   - `false`: If system can proceed without clarification

2. **clarification_questions** (list of strings):
   - If `needs_clarification = true`: Provide 1-3 specific questions
   - If `needs_clarification = false`: Return empty list
   - Questions should be:
     - Specific and actionable
     - Help narrow down user intent
     - Address the core ambiguity

3. **reason** (string):
   - Brief explanation (1-2 sentences) of why clarification is/isn't needed
   - If needed: What's ambiguous
   - If not needed: Why it's clear

4. **confidence** (string: "high", "medium", "low"):
   - How confident you are in your assessment
   - "high": Very clear whether clarification is needed
   - "medium": Some uncertainty
   - "low": Borderline case

## Examples

### Example 1: Needs Clarification (Vague Reference)
**User Query**: "What does it say about that clause we discussed?"
**Message History**: Empty
**Filters**: None

**Response**:
```json
{
  "needs_clarification": true,
  "clarification_questions": [
    "Which specific clause are you referring to?",
    "Which contract or document should I look in?"
  ],
  "reason": "The query references 'that clause we discussed' but there is no conversation history to provide context about which clause is being referenced.",
  "confidence": "high"
}
```

### Example 2: Does NOT Need Clarification (Clear Query)
**User Query**: "What are the payment terms in the hosting agreement?"
**Message History**: Some previous messages
**Filters**: None

**Response**:
```json
{
  "needs_clarification": false,
  "clarification_questions": [],
  "reason": "The query is clear and specific - user wants payment terms information from a hosting agreement. The system can search for this without additional clarification.",
  "confidence": "high"
}
```

### Example 3: Needs Clarification (Filter Mismatch)
**User Query**: "Compare liability across these 3 contracts"
**Message History**: None
**Filters**: 2 documents provided

**Response**:
```json
{
  "needs_clarification": true,
  "clarification_questions": [
    "I see 2 contracts are selected, but you mentioned 3 contracts. Did you mean to select one more contract, or should I compare the 2 currently selected contracts?"
  ],
  "reason": "User mentions '3 contracts' but only 2 documents are pre-filtered. There's a mismatch between the query and available context.",
  "confidence": "high"
}
```

### Example 4: Does NOT Need Clarification (Filters Provide Context)
**User Query**: "Compare the liability limitations"
**Message History**: None
**Filters**: 3 documents provided

**Response**:
```json
{
  "needs_clarification": false,
  "clarification_questions": [],
  "reason": "The query is clear and 3 contracts are pre-selected in filters, providing sufficient context. The system can compare liability limitations across these specific documents.",
  "confidence": "high"
}
```

### Example 5: Needs Clarification (Ambiguous Scope)
**User Query**: "What does it say about payments?"
**Message History**: None
**Filters**: None

**Response**:
```json
{
  "needs_clarification": true,
  "clarification_questions": [
    "Which aspect of payments are you interested in? (e.g., payment terms, payment schedule, payment amounts, late payment penalties)",
    "Which specific contract or agreement should I look in?"
  ],
  "reason": "The query 'payments' is too broad and could refer to multiple aspects. Additionally, no specific document context is provided.",
  "confidence": "high"
}
```

## Important Guidelines

1. **Be conservative**: When in doubt, ask for clarification. It's better to clarify than to answer the wrong question.
2. **Be specific**: Clarification questions should help narrow down the exact intent.
3. **Consider all context**: Look at query + history + filters together before deciding.
4. **One issue at a time**: If multiple issues exist, prioritize the most critical one.
5. **User-friendly questions**: Frame questions in natural, conversational language.
"""


class ClarificationResponse(BaseModel):
    """Response from the clarifier agent."""

    needs_clarification: bool = Field(
        ...,
        description="Whether clarification is needed before proceeding (true/false)"
    )

    clarification_questions: List[str] = Field(
        default_factory=list,
        description="List of 1-3 specific clarification questions. Empty if no clarification needed."
    )

    reason: str = Field(
        ...,
        description="Brief explanation (1-2 sentences) of why clarification is/isn't needed"
    )

    confidence: str = Field(
        ...,
        description="Confidence level: 'high', 'medium', or 'low'"
    )


def _register_tools(agent: Agent) -> None:
    """Register tools for the clarifier agent."""

    @agent.tool
    def get_context_info(ctx: RunContext[ClarifierDependencies]) -> Dict[str, Any]:
        """
        Get information about available context (filters, history, etc.).

        Returns:
            Dictionary with context information
        """
        filters = ctx.deps.filters

        context_info = {
            "has_filters": False,
            "filter_count": 0,
            "filter_details": None
        }

        if filters and "documents" in filters:
            doc_count = len(filters["documents"])
            context_info["has_filters"] = True
            context_info["filter_count"] = doc_count
            context_info["filter_details"] = filters
            logger.info(f"📋 Context info: {doc_count} documents pre-filtered")
        else:
            logger.info("📋 Context info: No filters provided")

        return context_info


class ClarifierAgentFactory:
    """Factory for creating ClarifierAgent instances."""

    @staticmethod
    def create_default() -> Agent:
        """
        Create a ClarifierAgent with default settings.

        Returns:
            Configured Agent instance
        """
        logger.info("🔍 Creating ClarifierAgent")

        # Get model and settings
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        # Create agent
        agent = Agent(
            model=model,
            instructions=SYSTEM_PROMPT,
            output_type=ClarificationResponse,
            model_settings=model_settings,
            deps_type=ClarifierDependencies,
        )

        # Register tools
        _register_tools(agent)

        logger.info("✅ ClarifierAgent created successfully")
        return agent

    @staticmethod
    def from_env_file(env_path: str) -> Agent:
        """
        Create a ClarifierAgent from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured Agent instance
        """
        from pathlib import Path
        logger.info(f"🔍 Creating ClarifierAgent from env file: {env_path}")

        # Get model and settings
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(Path(env_path))

        # Create agent
        agent = Agent(
            model=model,
            instructions=SYSTEM_PROMPT,
            output_type=ClarificationResponse,
            model_settings=model_settings,
            deps_type=ClarifierDependencies,
        )

        # Register tools
        _register_tools(agent)

        logger.info("✅ ClarifierAgent created successfully")
        return agent


if __name__ == "__main__":
    import asyncio
    from pathlib import Path
    from contramate.models import MessageHistory

    async def test_clarifier():
        logger.info("🧪 Testing ClarifierAgent")

        env_path = Path(".envs/local.env")
        agent = ClarifierAgentFactory.from_env_file(env_path)

        # Test cases: (query, filters, message_dicts)
        test_cases = [
            # Case 1: Vague reference with no history
            (
                "What does it say about that clause?",
                None,
                []
            ),
            # Case 2: Clear query
            (
                "What are the payment terms in the hosting agreement?",
                None,
                []
            ),
            # Case 3: Filter mismatch (says 3, has 2)
            (
                "Compare liability across these 3 contracts",
                {
                    "documents": [
                        {"project_id": "p1", "reference_doc_id": "d1"},
                        {"project_id": "p2", "reference_doc_id": "d2"}
                    ]
                },
                []
            ),
            # Case 4: Clear with matching filters
            (
                "Compare the liability limitations",
                {
                    "documents": [
                        {"project_id": "p1", "reference_doc_id": "d1"},
                        {"project_id": "p2", "reference_doc_id": "d2"},
                        {"project_id": "p3", "reference_doc_id": "d3"}
                    ]
                },
                []
            ),
            # Case 5: Ambiguous scope
            (
                "What does it say about payments?",
                None,
                []
            ),
            # Case 6: Reference to previous conversation WITH history
            (
                "What about the termination clause in that same contract?",
                None,
                [
                    {
                        "role": "user",
                        "content": "What are the payment terms in the hosting agreement?",
                        "timestamp": "2024-10-23T10:00:00Z"
                    },
                    {
                        "role": "assistant",
                        "content": "The hosting agreement specifies net 30 payment terms with a 2% late fee."
                    }
                ]
            ),
        ]

        for query, filters, message_dicts in test_cases:
            logger.info(f"\n{'='*80}")
            logger.info(f"Query: {query}")
            logger.info(f"Filters: {len(filters.get('documents', [])) if filters else 0} documents")
            logger.info(f"History: {len(message_dicts)} messages")
            logger.info(f"{'='*80}")

            # Convert message history to pydantic-ai format
            pydantic_messages = None
            if message_dicts:
                message_history = MessageHistory.model_validate({"messages": message_dicts})
                pydantic_messages = message_history.to_pydantic_ai_messages()

            deps = ClarifierDependencies(filters=filters)
            result = await agent.run(query, message_history=pydantic_messages, deps=deps)
            response = result.output

            logger.info(f"Needs Clarification: {response.needs_clarification}")
            logger.info(f"Confidence: {response.confidence}")
            logger.info(f"Reason: {response.reason}")

            if response.clarification_questions:
                logger.info("Questions:")
                for i, q in enumerate(response.clarification_questions, 1):
                    logger.info(f"  {i}. {q}")

    asyncio.run(test_clarifier())
