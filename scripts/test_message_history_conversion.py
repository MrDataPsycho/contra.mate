"""Test message history conversion to debug the issue."""

from contramate.models import MessageHistory
from loguru import logger

# Test data matching the user's request
message_history_data = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]

logger.info("Testing message history conversion...")
logger.info(f"Input: {message_history_data}")

# Convert
msg_history = MessageHistory.model_validate({"messages": message_history_data})
logger.info(f"MessageHistory object: {msg_history}")

pydantic_messages = msg_history.to_pydantic_ai_messages()
logger.info(f"Converted messages count: {len(pydantic_messages)}")

for i, msg in enumerate(pydantic_messages):
    logger.info(f"Message {i}: {type(msg).__name__}")
    logger.info(f"  Parts: {msg.parts}")
    logger.info(f"  Full message: {msg}")
