"""Test retry logic by simulating validation errors."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from loguru import logger
from contramate.core.agents.talk_to_contract_vanilla import (
    TalkToContractVanillaAgent,
    ResponseValidationError,
)


async def test_retry_on_validation_error():
    """Test that retry logic works when validation fails."""
    logger.info("=" * 60)
    logger.info("Testing Retry Logic with Simulated Validation Errors")
    logger.info("=" * 60)

    # Create a mock agent
    agent = MagicMock(spec=TalkToContractVanillaAgent)

    # Mock the client to return bad responses first, then good
    mock_client = AsyncMock()

    # First attempt: Missing citations field
    attempt_1 = MagicMock()
    attempt_1.choices = [MagicMock()]
    attempt_1.choices[0].message = MagicMock()
    attempt_1.choices[0].message.content = '{"answer": "Some answer [doc1]"}'
    attempt_1.choices[0].message.tool_calls = None

    # Second attempt: Invalid placeholder value
    attempt_2 = MagicMock()
    attempt_2.choices = [MagicMock()]
    attempt_2.choices[0].message = MagicMock()
    attempt_2.choices[0].message.content = '{"answer": "Some answer [doc1]", "citations": {"doc1": "source"}}'
    attempt_2.choices[0].message.tool_calls = None

    # Third attempt: Valid response
    attempt_3 = MagicMock()
    attempt_3.choices = [MagicMock()]
    attempt_3.choices[0].message = MagicMock()
    attempt_3.choices[0].message.content = '{"answer": "Some answer [doc1]", "citations": {"doc1": "VALID_DOCUMENT_NAME.pdf.md-1"}}'
    attempt_3.choices[0].message.tool_calls = None

    mock_client.chat.completions.create = AsyncMock(
        side_effect=[attempt_1, attempt_2, attempt_3]
    )

    # Create agent instance with mocked client
    from contramate.services.opensearch_vector_search_service import OpenSearchVectorSearchServiceFactory
    search_service = OpenSearchVectorSearchServiceFactory.create_default()

    agent = TalkToContractVanillaAgent(
        client=mock_client,
        search_service=search_service,
        model="gpt-4",
    )

    try:
        result = await agent.run(
            user_query="Test query",
            filters=None,
            message_history=None,
        )

        logger.info(f"✅ Final result after retries: {result}")
        logger.info(f"Success: {result.get('success')}")
        logger.info(f"Citations: {result.get('citations')}")

        # Verify we made 3 attempts
        assert mock_client.chat.completions.create.call_count == 3, \
            f"Expected 3 calls, got {mock_client.chat.completions.create.call_count}"

        logger.info(f"✅ Retry logic worked! Made {mock_client.chat.completions.create.call_count} attempts before success")

    except ResponseValidationError as e:
        logger.error(f"❌ Validation failed after max retries: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_retry_on_validation_error())
