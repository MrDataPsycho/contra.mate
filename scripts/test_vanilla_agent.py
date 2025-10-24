"""Test the vanilla OpenAI Talk To Contract agent."""

import asyncio
from loguru import logger
from contramate.core.agents.talk_to_contract_vanilla import TalkToContractVanillaAgentFactory


async def test_vanilla_agent():
    """Test vanilla agent with and without message history."""

    # Create agent
    agent = TalkToContractVanillaAgentFactory.create_default()

    # Test filters
    filters = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
            }
        ]
    }

    user_query = "What are the payment terms?"

    # Test 1: WITHOUT message history
    logger.info("=" * 60)
    logger.info("TEST 1: WITHOUT MESSAGE HISTORY")
    logger.info("=" * 60)

    result1 = await agent.run(
        user_query=user_query,
        filters=filters,
        message_history=None,
    )

    logger.info(f"\n✅ Result 1 - Success: {result1.get('success')}")
    logger.info(f"Answer snippet: {result1.get('answer', '')[:200]}...")
    logger.info(f"Citations: {result1.get('citations')}")

    # Check inline citations
    answer1 = result1.get('answer', '')
    has_citations1 = any(f"[doc{i}]" in answer1 for i in range(1, 10))
    logger.info(f"Has [docN] inline citations: {has_citations1}")

    # Test 2: WITH message history
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: WITH MESSAGE HISTORY")
    logger.info("=" * 60)

    message_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help you with your contract questions?"}
    ]

    result2 = await agent.run(
        user_query=user_query,
        filters=filters,
        message_history=message_history,
    )

    logger.info(f"\n✅ Result 2 - Success: {result2.get('success')}")
    logger.info(f"Answer snippet: {result2.get('answer', '')[:200]}...")
    logger.info(f"Citations: {result2.get('citations')}")

    # Check inline citations
    answer2 = result2.get('answer', '')
    has_citations2 = any(f"[doc{i}]" in answer2 for i in range(1, 10))
    logger.info(f"Has [docN] inline citations: {has_citations2}")

    # Validate citations format
    logger.info("\n" + "=" * 60)
    logger.info("CITATION VALIDATION")
    logger.info("=" * 60)

    for test_name, result in [("WITHOUT history", result1), ("WITH history", result2)]:
        logger.info(f"\n{test_name}:")
        citations = result.get('citations', {})

        if not citations:
            logger.warning(f"  ❌ No citations returned")
            continue

        for key, value in citations.items():
            key_valid = isinstance(key, str) and key.startswith('doc')
            value_valid = isinstance(value, str) and len(value) > 10 and not value.isdigit()

            status = "✅" if (key_valid and value_valid) else "❌"
            logger.info(f"  {status} {key} ({type(key).__name__}) -> {value[:50]}... ({type(value).__name__})")


if __name__ == "__main__":
    asyncio.run(test_vanilla_agent())
