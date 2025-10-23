"""
Example: Using Talk To Contract Agent with Filters

This example demonstrates how to use the Talk To Contract agent with different
filter configurations to limit search scope.
"""

import asyncio
from loguru import logger
from contramate.core.agents import TalkToContractAgentFactory, TalkToContractDependencies
from contramate.services.opensearch_vector_search_service import OpenSearchVectorSearchServiceFactory


async def example_no_filter():
    """Example 1: Search without any filters (search all documents)"""
    print("\n" + "="*80)
    print("Example 1: Search Without Filters (All Documents)")
    print("="*80)

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Create dependencies without filters
    deps = TalkToContractDependencies(search_service=search_service)

    # Run query
    user_query = "What are common termination clauses in contracts?"
    result = await agent.run(user_query, deps=deps)

    # Display results
    print(f"\nQuery: {user_query}")
    print(f"Answer: {result.output.answer}")
    print(f"\nCitations:")
    for key, value in result.output.citations.items():
        print(f"  {key}: {value}")


async def example_single_document():
    """Example 2: Search within a single document"""
    print("\n" + "="*80)
    print("Example 2: Search Within Single Document")
    print("="*80)

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define filter for single document
    filter_config = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
            }
        ]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(
        search_service=search_service,
        filters=filter_config
    )

    # Run query
    user_query = "What are the payment terms in this contract?"
    result = await agent.run(user_query, deps=deps)

    # Display results
    print(f"\nQuery: {user_query}")
    print(f"Filter: Single document")
    print(f"Answer: {result.output.answer}")
    print(f"\nCitations:")
    for key, value in result.output.citations.items():
        print(f"  {key}: {value}")


async def example_multiple_documents():
    """Example 3: Compare information across multiple documents"""
    print("\n" + "="*80)
    print("Example 3: Search Across Multiple Documents")
    print("="*80)

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define filter for multiple documents
    filter_config = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
            },
            {
                "project_id": "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
                "reference_doc_id": "aa1a0c65-8016-5d11-bbde-22055140660b"
            },
            {
                "project_id": "0096b72f-1c0d-4724-924f-011f87d3591a",
                "reference_doc_id": "16b6078b-248c-5ed9-83ef-20ee0af49396"
            }
        ]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(
        search_service=search_service,
        filters=filter_config
    )

    # Run query
    user_query = "Compare the liability limitations across these contracts"
    result = await agent.run(user_query, deps=deps)

    # Display results
    print(f"\nQuery: {user_query}")
    print(f"Filter: {len(filter_config['documents'])} documents")
    print(f"Answer: {result.output.answer}")
    print(f"\nCitations:")
    for key, value in result.output.citations.items():
        print(f"  {key}: {value}")


async def example_project_filter():
    """Example 4: Search within a specific project"""
    print("\n" + "="*80)
    print("Example 4: Search Within Specific Project")
    print("="*80)

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define filter for project
    filter_config = {
        "project_id": ["00149794-2432-4c18-b491-73d0fafd3efd"]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(
        search_service=search_service,
        filters=filter_config
    )

    # Run query
    user_query = "What are the key obligations in project contracts?"
    result = await agent.run(user_query, deps=deps)

    # Display results
    print(f"\nQuery: {user_query}")
    print(f"Filter: Project scope")
    print(f"Answer: {result.output.answer}")
    print(f"\nCitations:")
    for key, value in result.output.citations.items():
        print(f"  {key}: {value}")


async def example_combined_filters():
    """Example 5: Use combined filters"""
    print("\n" + "="*80)
    print("Example 5: Search With Combined Filters")
    print("="*80)

    # Create agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define combined filters
    filter_config = {
        "project_id": ["00149794-2432-4c18-b491-73d0fafd3efd"],
        "doc_source": "system",
        "contract_type": ["Service Agreement", "License Agreement"]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(
        search_service=search_service,
        filters=filter_config
    )

    # Run query
    user_query = "What are the warranty clauses?"
    result = await agent.run(user_query, deps=deps)

    # Display results
    print(f"\nQuery: {user_query}")
    print(f"Filter: Project + Source + Contract Type")
    print(f"Answer: {result.output.answer}")
    print(f"\nCitations:")
    for key, value in result.output.citations.items():
        print(f"  {key}: {value}")


async def main():
    """Run all examples"""
    logger.info("Starting Talk To Contract Agent Filter Examples")

    try:
        # Run examples
        await example_no_filter()
        await example_single_document()
        await example_multiple_documents()
        await example_project_filter()
        await example_combined_filters()

        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80)

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
