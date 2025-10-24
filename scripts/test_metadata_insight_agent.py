"""Test script for ContractMetadataInsightAgent.

This script tests the SQL-based metadata insight agent with various queries.
"""

import asyncio
from loguru import logger

from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory,
)


async def test_basic_query():
    """Test basic contract count query."""
    logger.info("=" * 80)
    logger.info("TEST 1: Basic Contract Count")
    logger.info("=" * 80)
    
    # Create agent (uses model from .envs/local.env)
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "How many contracts are in the database?"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query succeeded!")
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Citations:")
        for key, value in result.get("citations", {}).items():
            print(f"  {key}: {value}")
    else:
        logger.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    return result


async def test_contract_types():
    """Test contract type distribution query."""
    logger.info("=" * 80)
    logger.info("TEST 2: Contract Type Distribution")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "What are the different types of contracts and how many of each type do we have?"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query succeeded!")
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Citations:")
        for key, value in result.get("citations", {}).items():
            print(f"  {key}: {value}")
    else:
        logger.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    return result


async def test_clause_analysis():
    """Test clause-specific query."""
    logger.info("=" * 80)
    logger.info("TEST 3: Non-Compete Clause Analysis")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "How many contracts have non-compete clauses? Show me the breakdown by contract type."
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query succeeded!")
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Citations:")
        for key, value in result.get("citations", {}).items():
            print(f"  {key}: {value}")
    else:
        logger.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    return result


async def test_esmd_join():
    """Test query involving both ASMD and ESMD tables."""
    logger.info("=" * 80)
    logger.info("TEST 4: ASMD + ESMD Join Query (Financial Data)")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "Show me contracts with non-compete clauses that also have financial information available. How many have total contract values?"
    
    logger.info(f"Query: {query}")
    result = await agent.run(query)
    
    if result["success"]:
        logger.success("✅ Query succeeded!")
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Citations:")
        for key, value in result.get("citations", {}).items():
            print(f"  {key}: {value}")
    else:
        logger.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    return result


async def test_with_filters():
    """Test query with global filters."""
    logger.info("=" * 80)
    logger.info("TEST 5: Query with Project Filter")
    logger.info("=" * 80)
    
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    query = "How many Service Agreements are there?"
    filters = {"contract_type": "Service Agreement"}
    
    logger.info(f"Query: {query}")
    logger.info(f"Filters: {filters}")
    result = await agent.run(query, filters=filters)
    
    if result["success"]:
        logger.success("✅ Query succeeded!")
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Citations:")
        for key, value in result.get("citations", {}).items():
            print(f"  {key}: {value}")
    else:
        logger.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
    
    return result


async def main():
    """Run all tests."""
    logger.info("🚀 Starting ContractMetadataInsightAgent Tests")
    logger.info("=" * 80)
    
    try:
        # Test 1: Basic count
        await test_basic_query()
        print("\n" + "=" * 80 + "\n")
        
        # Test 2: Contract types
        await test_contract_types()
        print("\n" + "=" * 80 + "\n")
        
        # Test 3: Clause analysis
        await test_clause_analysis()
        print("\n" + "=" * 80 + "\n")
        
        # Test 4: ESMD join
        await test_esmd_join()
        print("\n" + "=" * 80 + "\n")
        
        # Test 5: With filters
        await test_with_filters()
        
        logger.success("🎉 All tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
