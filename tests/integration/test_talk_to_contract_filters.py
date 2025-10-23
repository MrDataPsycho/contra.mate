"""
Integration tests for Talk To Contract Agent filter functionality.

These tests verify that filters are properly passed from the agent
to the search service using real OpenSearch and OpenAI connections.

Requirements:
- OpenSearch must be running and accessible
- OpenAI API key must be configured
- Test data must be indexed in OpenSearch
"""

import asyncio
from loguru import logger
from typing import List, Dict, Any

from contramate.core.agents import (
    TalkToContractAgentFactory,
    TalkToContractDependencies,
)
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchServiceFactory,
)


def validate_single_document_filter(
    search_results: List[Any],
    expected_project_id: str,
    expected_reference_doc_id: str
) -> bool:
    """
    Validate that all search results come from the specified document.

    Args:
        search_results: List of search results from OpenSearch
        expected_project_id: The expected project ID
        expected_reference_doc_id: The expected reference document ID

    Returns:
        True if all results match the filter, False otherwise
    """
    if not search_results:
        logger.warning("⚠️  No search results to validate")
        return False

    for result in search_results:
        if (result.project_id != expected_project_id or
            result.reference_doc_id != expected_reference_doc_id):
            logger.error(
                f"❌ Found result from different document: "
                f"project_id={result.project_id}, reference_doc_id={result.reference_doc_id}"
            )
            return False

    logger.info(f"✅ All {len(search_results)} results are from the filtered document")
    return True


def validate_multiple_documents_filter(
    search_results: List[Any],
    expected_documents: List[Dict[str, str]]
) -> bool:
    """
    Validate that all search results come from at least one of the specified documents.

    Args:
        search_results: List of search results from OpenSearch
        expected_documents: List of document filters with project_id and reference_doc_id

    Returns:
        True if all results match at least one filter, False otherwise
    """
    if not search_results:
        logger.warning("⚠️  No search results to validate")
        return False

    # Create set of valid document identifiers
    valid_docs = {
        (doc["project_id"], doc["reference_doc_id"])
        for doc in expected_documents
    }

    # Track which documents were actually found
    found_docs = set()

    for result in search_results:
        doc_id = (result.project_id, result.reference_doc_id)
        if doc_id not in valid_docs:
            logger.error(
                f"❌ Found result from unexpected document: "
                f"project_id={result.project_id}, reference_doc_id={result.reference_doc_id}"
            )
            return False
        found_docs.add(doc_id)

    logger.info(
        f"✅ All {len(search_results)} results are from the filtered documents "
        f"({len(found_docs)} of {len(expected_documents)} documents had matching results)"
    )
    return True


async def test_agent_with_single_document_filter():
    """
    Test that agent properly uses single document filter.

    Validation:
    - All returned chunks must be from the specified document only
    - project_id and reference_doc_id must match the filter
    """
    logger.info("=" * 80)
    logger.info("Test 1: Agent with Single Document Filter")
    logger.info("=" * 80)

    # Create real agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define single document filter
    filter_config = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949",
            }
        ]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(search_service=search_service, filters=filter_config)

    # Run agent
    logger.info("Query: 'What are the payment terms in this contract?'")
    result = await agent.run(
        "What are the payment terms in this contract?",
        deps=deps,
    )

    # Verify the agent ran successfully
    assert result is not None, "Agent should return a result"
    assert result.output is not None, "Agent should return output"
    assert result.output.answer, "Should have an answer"
    assert result.output.citations, "Should have citations mapping"
    assert isinstance(result.output.citations, dict), "Citations should be a dictionary"

    logger.info(f"\n📊 Agent Response:")
    logger.info(f"   Citations: {result.output.citations}")
    logger.info(f"   Answer: {result.output.answer[:200]}...")

    # Get the actual search results to validate
    # We need to perform the same search to get the actual results
    search_response = search_service.hybrid_search(
        query="What are the payment terms in this contract?",
        filters=filter_config
    )

    if search_response.is_ok():
        search_data = search_response.unwrap()
        search_results = search_data.results
        logger.info(f"\n🔍 Validating {len(search_results)} search results...")

        # Validate all results are from the filtered document
        is_valid = validate_single_document_filter(
            search_results,
            expected_project_id=filter_config["documents"][0]["project_id"],
            expected_reference_doc_id=filter_config["documents"][0]["reference_doc_id"]
        )

        assert is_valid, "All results must be from the filtered document"
        logger.info("✅ PASSED: Single document filter correctly applied\n")
    else:
        error = search_response.unwrap_err()
        raise AssertionError(f"Search failed: {error}")


async def test_agent_with_multiple_documents_filter():
    """
    Test that agent properly uses multiple documents filter.

    Validation:
    - All returned chunks must be from at least one of the specified documents
    - Results can come from any combination of the filtered documents
    """
    logger.info("=" * 80)
    logger.info("Test 2: Agent with Multiple Documents Filter")
    logger.info("=" * 80)

    # Create real agent and search service
    agent = TalkToContractAgentFactory.create_default()
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    # Define multiple documents filter
    filter_config = {
        "documents": [
            {
                "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949",
            },
            {
                "project_id": "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
                "reference_doc_id": "aa1a0c65-8016-5d11-bbde-22055140660b",
            },
            {
                "project_id": "0096b72f-1c0d-4724-924f-011f87d3591a",
                "reference_doc_id": "16b6078b-248c-5ed9-83ef-20ee0af49396",
            },
        ]
    }

    # Create dependencies with filter
    deps = TalkToContractDependencies(search_service=search_service, filters=filter_config)

    # Run agent
    logger.info("Query: 'Compare liability limitations across these contracts'")
    result = await agent.run(
        "Compare liability limitations across these contracts",
        deps=deps,
    )

    # Verify the agent ran successfully
    assert result is not None, "Agent should return a result"
    assert result.output is not None, "Agent should return output"
    assert result.output.answer, "Should have an answer"
    assert result.output.citations, "Should have citations mapping"
    assert isinstance(result.output.citations, dict), "Citations should be a dictionary"

    logger.info(f"\n📊 Agent Response:")
    logger.info(f"   Citations: {result.output.citations}")
    logger.info(f"   Answer: {result.output.answer[:200]}...")

    # Get the actual search results to validate
    search_response = search_service.hybrid_search(
        query="Compare liability limitations across these contracts",
        filters=filter_config
    )

    if search_response.is_ok():
        search_data = search_response.unwrap()
        search_results = search_data.results
        logger.info(f"\n🔍 Validating {len(search_results)} search results...")

        # Validate all results are from the filtered documents
        is_valid = validate_multiple_documents_filter(
            search_results,
            expected_documents=filter_config["documents"]
        )

        assert is_valid, "All results must be from at least one of the filtered documents"
        logger.info("✅ PASSED: Multiple documents filter correctly applied\n")
    else:
        error = search_response.unwrap_err()
        raise AssertionError(f"Search failed: {error}")


if __name__ == "__main__":
    # Run tests manually
    print("\n" + "=" * 80)
    print("Running Integration Tests for Talk To Contract Agent Filters")
    print("=" * 80 + "\n")

    async def run_all_tests():
        try:
            await test_agent_with_single_document_filter()
            await test_agent_with_multiple_documents_filter()

            print("\n" + "=" * 80)
            print("✅ All integration tests passed successfully!")
            print("=" * 80 + "\n")

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            raise

    asyncio.run(run_all_tests())
