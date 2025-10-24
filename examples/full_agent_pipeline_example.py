"""
Full Agent Pipeline Example

This example demonstrates the complete agent orchestration pipeline:
1. ClarifierAgent - Checks if query needs clarification
2. PlannerAgent - Creates execution plan
3. ExecutorAgent - Executes the plan using sub-agents:
   - QueryRewriterAgent (optional, configurable)
   - TalkToContractAgent (always enabled)
   - AnswerCritiqueAgent (optional, configurable)

The pipeline shows how to:
- Toggle agents on/off via environment variables
- Pass filters and conversation history
- Handle the complete flow from query to final answer
"""
import asyncio
from pathlib import Path
from loguru import logger

from contramate.core.agents import (
    ClarifierAgentFactory,
    ClarifierDependencies,
    PlannerAgentFactory,
    PlannerDependencies,
)
from contramate.core.agents import ExecutorAgentFactory
from contramate.models import MessageHistory
from contramate.utils.settings.core import AgentToggleSettings


async def run_pipeline_example(
    user_query: str,
    filters: dict | None = None,
    message_history: list | None = None,
    env_path: Path | None = None,
):
    """
    Run the complete agent pipeline for a user query.

    Args:
        user_query: The user's question
        filters: Optional document filters
        message_history: Optional conversation history
        env_path: Path to environment file (defaults to .envs/local.env)
    """
    if env_path is None:
        env_path = Path(".envs/local.env")

    logger.info(f"\n{'='*100}")
    logger.info(f"🚀 STARTING AGENT PIPELINE")
    logger.info(f"{'='*100}")
    logger.info(f"Query: {user_query}")
    logger.info(f"Filters: {len(filters.get('documents', [])) if filters else 0} documents")
    logger.info(f"History: {len(message_history) if message_history else 0} messages")
    logger.info(f"{'='*100}\n")

    # =========================================================================
    # STEP 1: CLARIFICATION (Gatekeeper)
    # =========================================================================
    logger.info(f"\n{'#'*100}")
    logger.info("# STEP 1: CLARIFIER AGENT (Human-in-the-loop checkpoint)")
    logger.info(f"{'#'*100}\n")

    clarifier = ClarifierAgentFactory.from_env_file(str(env_path))
    clarifier_deps = ClarifierDependencies(filters=filters)

    # Convert message history to pydantic-ai format
    pydantic_messages = None
    if message_history:
        msg_history = MessageHistory.model_validate({"messages": message_history})
        pydantic_messages = msg_history.to_pydantic_ai_messages()

    clarification_result = await clarifier.run(
        user_query, message_history=pydantic_messages, deps=clarifier_deps
    )

    logger.info(f"Needs Clarification: {clarification_result.output.needs_clarification}")
    logger.info(f"Confidence: {clarification_result.output.confidence}")
    logger.info(f"Reason: {clarification_result.output.reason}")

    if clarification_result.output.needs_clarification:
        logger.warning("\n⚠️  PIPELINE STOPPED: User clarification required")
        logger.info("Questions to ask user:")
        for i, q in enumerate(clarification_result.output.clarification_questions, 1):
            logger.info(f"  {i}. {q}")
        return {
            "status": "needs_clarification",
            "questions": clarification_result.output.clarification_questions,
        }

    logger.info("✅ Query is clear - proceeding to planning")

    # =========================================================================
    # STEP 2: PLANNING
    # =========================================================================
    logger.info(f"\n{'#'*100}")
    logger.info("# STEP 2: PLANNER AGENT (Creating execution plan)")
    logger.info(f"{'#'*100}\n")

    planner = PlannerAgentFactory.from_env_file(str(env_path))
    planner_deps = PlannerDependencies(filters=filters)

    plan_result = await planner.run(user_query, deps=planner_deps)
    plan = plan_result.output

    logger.info(f"📋 Plan Created:")
    logger.info(f"  Intent: {plan.intent}")
    logger.info(f"  Requires Rewrite: {plan.requires_rewrite}")
    logger.info(f"  Steps: {len(plan.steps)}")
    logger.info(f"  Expected Outcome: {plan.expected_outcome}")

    logger.info("\n  Execution Steps:")
    for step in plan.steps:
        logger.info(f"    {step.step_number}. {step.agent}.{step.action}")
        logger.info(f"       → {step.rationale}")

    # =========================================================================
    # STEP 3: EXECUTION
    # =========================================================================
    logger.info(f"\n{'#'*100}")
    logger.info("# STEP 3: EXECUTOR AGENT (Intelligent execution with tools)")
    logger.info(f"{'#'*100}\n")

    # Load agent toggle settings
    agent_settings = AgentToggleSettings.from_env_file(env_path)
    logger.info("Agent Configuration:")
    logger.info(f"  Clarifier: {'✓ Enabled' if agent_settings.enable_clarifier_agent else '✗ Disabled'}")
    logger.info(f"  Query Rewriter: {'✓ Enabled' if agent_settings.enable_query_rewriter_agent else '✗ Disabled'}")
    logger.info(f"  Answer Critique: {'✓ Enabled' if agent_settings.enable_answer_critique_agent else '✗ Disabled'}")
    logger.info(f"  TalkToContract: ✓ Always Enabled\n")

    # Create executor
    executor = ExecutorAgentFactory.from_env_file(env_path)

    # Create dependencies (sub-agents initialized automatically, NO env_path needed!)
    executor_deps = ExecutorAgentFactory.create_dependencies(
        filters=filters,
        message_history=message_history,
    )

    # Convert plan to TEXT (not object!)
    plan_text = f"""
Answer this question: "{plan.user_query}"

Follow this plan:
"""
    for step in plan.steps:
        plan_text += f"\n{step.step_number}. {step.rationale}"

    plan_text += f"\n\nExpected outcome: {plan.expected_outcome}"

    # Execute with intelligent tool selection
    execution_result = await executor.run(plan_text, deps=executor_deps)

    # =========================================================================
    # RESULTS
    # =========================================================================
    logger.info(f"\n{'#'*100}")
    logger.info("# EXECUTION RESULTS")
    logger.info(f"{'#'*100}\n")

    logger.info(f"Success: {execution_result.output.success}")
    logger.info(f"Tools Used: {', '.join(execution_result.output.tools_used)}")

    if execution_result.output.success:
        logger.info(f"\n📄 Final Answer:")
        logger.info(f"{execution_result.output.final_answer}\n")
    else:
        logger.error(f"❌ Execution Failed: {execution_result.output.error_message}")

    return {
        "status": "completed" if execution_result.output.success else "failed",
        "answer": execution_result.output.final_answer,
        "plan": plan,
        "tools_used": execution_result.output.tools_used,
    }


async def main():
    """Run example scenarios."""
    logger.info("="*100)
    logger.info("FULL AGENT PIPELINE EXAMPLES")
    logger.info("="*100)

    env_path = Path(".envs/local.env")

    # =========================================================================
    # Example 1: Simple query with no filters
    # =========================================================================
    logger.info("\n\n" + "="*100)
    logger.info("EXAMPLE 1: Simple Query (No Filters)")
    logger.info("="*100)

    result1 = await run_pipeline_example(
        user_query="What are the payment terms in the hosting agreement?",
        filters=None,
        message_history=None,
        env_path=env_path,
    )

    # =========================================================================
    # Example 2: Multi-document comparison with filters
    # =========================================================================
    logger.info("\n\n" + "="*100)
    logger.info("EXAMPLE 2: Multi-Document Comparison (With Filters)")
    logger.info("="*100)

    result2 = await run_pipeline_example(
        user_query="Compare the liability limitations across these contracts",
        filters={
            "documents": [
                {"project_id": "proj1", "reference_doc_id": "doc1"},
                {"project_id": "proj2", "reference_doc_id": "doc2"},
                {"project_id": "proj3", "reference_doc_id": "doc3"},
            ]
        },
        message_history=None,
        env_path=env_path,
    )

    # =========================================================================
    # Example 3: Query with conversation history
    # =========================================================================
    logger.info("\n\n" + "="*100)
    logger.info("EXAMPLE 3: Query with Conversation History")
    logger.info("="*100)

    result3 = await run_pipeline_example(
        user_query="What about the termination clause in that same contract?",
        filters=None,
        message_history=[
            {
                "role": "user",
                "content": "What are the payment terms in the hosting agreement?",
                "timestamp": "2024-10-23T10:00:00Z",
            },
            {
                "role": "assistant",
                "content": "The hosting agreement specifies net 30 payment terms with a 2% late fee.",
            },
        ],
        env_path=env_path,
    )

    # =========================================================================
    # Example 4: Ambiguous query that needs clarification
    # =========================================================================
    logger.info("\n\n" + "="*100)
    logger.info("EXAMPLE 4: Ambiguous Query (Should Request Clarification)")
    logger.info("="*100)

    result4 = await run_pipeline_example(
        user_query="What does it say about that clause?",
        filters=None,
        message_history=None,
        env_path=env_path,
    )

    # Print summary
    logger.info("\n\n" + "="*100)
    logger.info("SUMMARY OF ALL EXAMPLES")
    logger.info("="*100)
    logger.info(f"Example 1: {result1['status']}")
    logger.info(f"Example 2: {result2['status']}")
    logger.info(f"Example 3: {result3['status']}")
    logger.info(f"Example 4: {result4['status']}")


if __name__ == "__main__":
    # To toggle agents, add to your .envs/local.env:
    # AGENT_ENABLE_CLARIFIER_AGENT=true
    # AGENT_ENABLE_QUERY_REWRITER_AGENT=true
    # AGENT_ENABLE_ANSWER_CRITIQUE_AGENT=true

    asyncio.run(main())
