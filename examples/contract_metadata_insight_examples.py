"""
Example: Using Contract Metadata Insight Agent with SQL Queries

This example demonstrates how to use the Contract Metadata Insight agent
to generate and execute SQL queries for contract analytics.
"""

import asyncio
from loguru import logger
from contramate.core.agents import (
    ContractMetadataInsightAgentFactory,
    ContractMetadataInsightDependencies,
)
from contramate.services.contract_metadata_insight_service import (
    ContractMetadataInsightService,
)


async def example_basic_count():
    """Example 1: Simple contract count"""
    print("\n" + "=" * 80)
    print("Example 1: Basic Contract Count")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = "How many contracts are in the database?"
    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_contract_types():
    """Example 2: Analyze contract type distribution"""
    print("\n" + "=" * 80)
    print("Example 2: Contract Type Distribution")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = "What are the most common contract types and their counts?"
    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_clause_analysis():
    """Example 3: Analyze specific contract clauses"""
    print("\n" + "=" * 80)
    print("Example 3: Non-Compete Clause Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = "How many contracts have non-compete clauses? Break it down by contract type."
    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_with_filters():
    """Example 4: Query with project filters"""
    print("\n" + "=" * 80)
    print("Example 4: Query With Project Filter")
    print("=" * 80)

    service = ContractMetadataInsightService()

    # Define filter for specific project
    filter_config = {"project_id": ["00149794-2432-4c18-b491-73d0fafd3efd"]}

    user_query = "What types of contracts are in this project?"
    result = await service.query(user_query, filters=filter_config)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Filter: Project-specific")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_contract_type_filter():
    """Example 5: Query with contract type filter"""
    print("\n" + "=" * 80)
    print("Example 5: Analyze Service Agreements Only")
    print("=" * 80)

    service = ContractMetadataInsightService()

    # Define filter for specific contract type
    filter_config = {"contract_type": ["Service Agreement"]}

    user_query = "What percentage of service agreements have termination for convenience clauses?"
    result = await service.query(user_query, filters=filter_config)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Filter: Service Agreements only")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_combined_filters():
    """Example 6: Query with multiple filters"""
    print("\n" + "=" * 80)
    print("Example 6: Combined Filters")
    print("=" * 80)

    service = ContractMetadataInsightService()

    # Define combined filters
    filter_config = {
        "project_id": ["00149794-2432-4c18-b491-73d0fafd3efd"],
        "contract_type": ["Service Agreement", "License Agreement"],
    }

    user_query = "Show me the distribution of liability clauses in these contracts."
    result = await service.query(user_query, filters=filter_config)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Filter: Project + Contract Types")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_comparative_analysis():
    """Example 7: Compare contract characteristics"""
    print("\n" + "=" * 80)
    print("Example 7: Comparative Clause Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = """
    Compare the prevalence of exclusivity clauses, non-compete clauses,
    and non-disparagement clauses across all contracts. Which is most common?
    """

    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query.strip()}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_date_analysis():
    """Example 8: Analyze contract dates"""
    print("\n" + "=" * 80)
    print("Example 8: Contract Date Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = "How many contracts have expiration dates? Group by contract type."
    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_license_analysis():
    """Example 9: Analyze licensing terms"""
    print("\n" + "=" * 80)
    print("Example 9: License Terms Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = """
    For contracts with license grants, what percentage have:
    1. Non-transferable licenses
    2. Irrevocable/perpetual licenses
    3. Unlimited licenses
    """

    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query.strip()}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_financial_terms():
    """Example 10: Analyze financial provisions"""
    print("\n" + "=" * 80)
    print("Example 10: Financial Terms Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = """
    Analyze the financial terms across contracts:
    - How many have revenue/profit sharing?
    - How many have price restrictions?
    - How many have minimum commitments?
    Group by contract type if possible.
    """

    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query.strip()}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_liability_caps():
    """Example 11: Analyze liability provisions"""
    print("\n" + "=" * 80)
    print("Example 11: Liability Provisions Analysis")
    print("=" * 80)

    service = ContractMetadataInsightService()

    user_query = """
    Compare contracts with capped liability vs uncapped liability.
    What's the distribution across contract types?
    """

    result = await service.query(user_query)

    if result.is_ok():
        data = result.unwrap()
        print(f"\nQuery: {user_query.strip()}")
        print(f"Answer: {data['answer']}")
        print(f"\nCitations:")
        for key, value in data.get('citations', {}).items():
            print(f"  {key}: {value}")
    else:
        error = result.unwrap_err()
        print(f"Error: {error['message']}")


async def example_custom_sql():
    """Example 12: Using conversation for complex analysis"""
    print("\n" + "=" * 80)
    print("Example 12: Multi-turn Conversation")
    print("=" * 80)

    service = ContractMetadataInsightService()

    # First query
    query1 = "Which contracts have both non-compete and exclusivity clauses?"
    result1 = await service.query(query1)

    if result1.is_ok():
        data1 = result1.unwrap()
        print(f"\nQuery 1: {query1}")
        print(f"Answer: {data1['answer']}")

        # Build conversation history
        message_history = [
            {"role": "user", "content": query1},
            {"role": "assistant", "content": data1["answer"]},
        ]

        # Follow-up query using history
        query2 = "Of those contracts, how many are service agreements?"
        result2 = await service.query(query2, message_history=message_history)

        if result2.is_ok():
            data2 = result2.unwrap()
            print(f"\nQuery 2: {query2}")
            print(f"Answer: {data2['answer']}")
            print(f"\nSQL Executed: {data2.get('sql_query', 'N/A')}")
        else:
            error = result2.unwrap_err()
            print(f"Error: {error['message']}")
    else:
        error = result1.unwrap_err()
        print(f"Error: {error['message']}")


async def main():
    """Run all examples"""
    logger.info("Starting Contract Metadata Insight Agent Examples")

    try:
        # Run examples
        await example_basic_count()
        await example_contract_types()
        await example_clause_analysis()
        await example_with_filters()
        await example_contract_type_filter()
        await example_combined_filters()
        await example_comparative_analysis()
        await example_date_analysis()
        await example_license_analysis()
        await example_financial_terms()
        await example_liability_caps()
        await example_custom_sql()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
