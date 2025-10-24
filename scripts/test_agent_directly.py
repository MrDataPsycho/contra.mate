"""Test the Talk To Contract agent directly to debug citation issues."""

import asyncio
from loguru import logger
from contramate.core.agents.talk_to_contract import (
    TalkToContractAgentFactory,
    TalkToContractDependencies,
)
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchServiceFactory,
)


async def test_agent_direct():
    """Test agent directly without service layer."""
    logger.info("=== Testing Agent Directly ===")

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Create dependencies with filters
    filters = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
            }
        ]
    }

    deps = TalkToContractDependencies(
        search_service=search_service,
        filters=filters,
    )

    # Run agent
    user_query = "What are the payment terms?"
    logger.info(f"Query: {user_query}")

    try:
        result = await agent.run(user_query, deps=deps)

        logger.info("\n=== Agent Response ===")
        logger.info(f"Answer: {result.output.answer[:200]}...")
        logger.info(f"\nCitations: {result.output.citations}")
        logger.info(f"\nCitation keys type: {type(list(result.output.citations.keys())[0]) if result.output.citations else 'empty'}")
        logger.info(f"Citation values type: {type(list(result.output.citations.values())[0]) if result.output.citations else 'empty'}")

        # Check if citations are in the answer
        answer_has_citations = any(f"[doc{i}]" in result.output.answer for i in range(1, 10))
        logger.info(f"\nAnswer contains [docN] citations: {answer_has_citations}")

        # Show usage
        usage = result.usage()
        logger.info(f"\nTokens used: {usage.total_tokens}")

        return result

    except Exception as e:
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")
        raise


async def test_service_layer():
    """Test through service layer."""
    logger.info("\n\n=== Testing Service Layer ===")

    from contramate.services.talk_to_contract_service import TalkToContractServiceFactory

    service = TalkToContractServiceFactory.create_default()

    filters = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
            }
        ]
    }

    message_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ]

    logger.info("Testing WITHOUT message history first...")
    result_no_history = await service.query(
        user_query="What are the payment terms?",
        filters=filters,
        message_history=None,
    )

    if result_no_history.is_ok():
        data = result_no_history.unwrap()
        logger.info(f"✅ WITHOUT history - Success: {data['success']}")
        logger.info(f"Citations: {data['citations']}")
    else:
        logger.error(f"❌ WITHOUT history - Error: {result_no_history.unwrap_err()}")

    logger.info("\n\nTesting WITH message history...")
    result = await service.query(
        user_query="What are the payment terms?",
        filters=filters,
        message_history=message_history,
    )

    if result.is_ok():
        data = result.unwrap()
        logger.info(f"✅ WITH history - Success: {data['success']}")
        logger.info(f"Citations: {data['citations']}")
        # Check if answer has [docN] citations
        has_citations = any(f"[doc{i}]" in data['answer'] for i in range(1, 10))
        logger.info(f"Answer has [docN] inline citations: {has_citations}")
        logger.info(f"Answer snippet: {data['answer'][:300]}...")
    else:
        error = result.unwrap_err()
        logger.error(f"❌ WITH history - Error: {error}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "service":
        asyncio.run(test_service_layer())
    else:
        asyncio.run(test_agent_direct())
