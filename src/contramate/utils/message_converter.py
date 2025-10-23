"""
Utility functions to convert OpenAI-compatible message history to Pydantic AI format.
"""

from pydantic_ai.messages import ModelMessage
from loguru import logger
from contramate.models.messages import OpenAIMessage, MessageHistory


def convert_openai_to_pydantic_messages(
    openai_messages: list[OpenAIMessage]
) -> list[ModelMessage]:
    """
    Convert a list of OpenAIMessage objects to Pydantic AI ModelMessage format.

    This is a convenience function that wraps the MessageHistory.to_pydantic_ai_messages() method.

    Args:
        openai_messages: List of OpenAIMessage objects (Pydantic validated)

    Returns:
        List of ModelMessage objects (ModelRequest or ModelResponse)

    Example:
        >>> messages = [
        ...     OpenAIMessage(role="user", content="Hello"),
        ...     OpenAIMessage(role="assistant", content="Hi there!")
        ... ]
        >>> pydantic_messages = convert_openai_to_pydantic_messages(messages)
    """
    history = MessageHistory(messages=openai_messages)
    return history.to_pydantic_ai_messages()

    


if __name__ == "__main__":
    from datetime import datetime, timezone

    # Example 1: Using the convenience function with auto-generated timestamps
    logger.info("=== Example 1: Auto-generated timestamps ===")
    messages_auto = [
        OpenAIMessage(role="user", content="What are the key details of this contract?"),
        OpenAIMessage(role="assistant", content="The contract is between Acme Corp and Beta LLC, signed on January 1, 2023."),
        OpenAIMessage(role="user", content="What is the termination clause?")
    ]

    pydantic_messages_auto = convert_openai_to_pydantic_messages(messages_auto)

    logger.info(f"Converted {len(messages_auto)} OpenAI messages to {len(pydantic_messages_auto)} Pydantic AI messages")

    for idx, msg in enumerate(pydantic_messages_auto):
        logger.info(f"Message {idx + 1}: {type(msg).__name__} with {len(msg.parts)} part(s)")
        if msg.parts and hasattr(msg.parts[0], 'timestamp'):
            logger.info(f"  Timestamp: {msg.parts[0].timestamp}")

    # Example 2: Using MessageHistory directly with custom timestamps
    logger.info("\n=== Example 2: Custom timestamps via MessageHistory ===")
    custom_time_1 = datetime(2024, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    custom_time_3 = datetime(2024, 10, 1, 12, 5, 0, tzinfo=timezone.utc)

    openai_history_dict = [
        {"role": "user", "content": "What are the key details of this contract?", "timestamp": custom_time_1.isoformat()},
        {"role": "assistant", "content": "The contract is between Acme Corp and Beta LLC, signed on January 1, 2023."},
        {"role": "user", "content": "What is the termination clause?", "timestamp": custom_time_3.isoformat()}
    ]

    message_history_custom = MessageHistory.model_validate({"messages": openai_history_dict})
    pydantic_messages_custom = message_history_custom.to_pydantic_ai_messages()

    logger.info(f"Converted {len(openai_history_dict)} OpenAI messages to {len(pydantic_messages_custom)} Pydantic AI messages")

    for idx, msg in enumerate(pydantic_messages_custom):
        logger.info(f"Message {idx + 1}: {type(msg).__name__} with {len(msg.parts)} part(s)")
        if msg.parts and hasattr(msg.parts[0], 'timestamp'):
            logger.info(f"  Timestamp: {msg.parts[0].timestamp}")
