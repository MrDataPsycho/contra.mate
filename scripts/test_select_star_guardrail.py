"""Test query guardrails in ContractMetadataInsightAgent.

This script tests that the agent properly blocks queries without WHERE or LIMIT clauses
to prevent pulling entire tables.
"""

import asyncio
from loguru import logger

from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory,
)


async def test_blocked_no_where_no_limit():
    """Test that queries without WHERE or LIMIT are blocked."""
    logger.info("=" * 80)
    logger.info("TEST 1: SELECT Without WHERE or LIMIT (Should be BLOCKED)")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    # Make the query very explicit - asking for ALL records with no filtering
    query = "Execute a simple SELECT query to retrieve ALL contract types without any filtering or limits. Just SELECT contract_type FROM contract_asmd and nothing else."
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if not result["success"]:
        logger.success(f"✅ Query properly blocked!")
        print(f"Error: {result.get('answer', result.get('error'))}\n")
    else:
        logger.error("❌ Query should have been blocked but succeeded!")
        print(f"\nAnswer:\n{result}\n")
    
    return result


async def test_allowed_with_limit():
    """Test that queries with LIMIT are allowed."""
    logger.info("=" * 80)
    logger.info("TEST 2: SELECT With LIMIT (Should be ALLOWED)")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "Show me 10 contracts from the database"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query with LIMIT allowed successfully!")
        print(f"\nAnswer:\n{result['answer']}\n")
    else:
        logger.error(f"❌ Query should have been allowed: {result.get('answer', result.get('error'))}")
    
    return result


async def test_allowed_with_where():
    """Test that queries with WHERE clause are allowed."""
    logger.info("=" * 80)
    logger.info("TEST 3: SELECT With WHERE Clause (Should be ALLOWED)")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "Count all Service Agreement contracts"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query with WHERE clause worked as expected!")
        print(f"\nAnswer:\n{result['answer']}\n")
    else:
        logger.error(f"❌ Query failed: {result.get('answer', result.get('error'))}")
    
    return result


async def test_allowed_with_both():
    """Test that queries with both WHERE and LIMIT work (best practice)."""
    logger.info("=" * 80)
    logger.info("TEST 4: SELECT With WHERE + LIMIT (Should be ALLOWED - Best Practice)")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "Show me 5 contracts with non-compete clauses"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query with WHERE + LIMIT worked perfectly!")
        print(f"\nAnswer:\n{result}\n")
    else:
        logger.error(f"❌ Query failed: {result.get('answer', result.get('error'))}")
    
    return result


async def main():
    """Run all guardrail tests."""
    logger.info("🚀 Starting Query Guardrail Tests")
    logger.info("=" * 80)
    
    try:
        # Test 1: Block queries without WHERE or LIMIT
        # await test_blocked_no_where_no_limit()
        # print("\n" + "=" * 80 + "\n")
        
        # # Test 2: Allow queries with LIMIT
        # await test_allowed_with_limit()
        # print("\n" + "=" * 80 + "\n")
        
        # # Test 3: Allow queries with WHERE
        # await test_allowed_with_where()
        # print("\n" + "=" * 80 + "\n")
        
        # # Test 4: Allow queries with both (best practice)
        await test_allowed_with_both()
        
        logger.success("🎉 All guardrail tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
