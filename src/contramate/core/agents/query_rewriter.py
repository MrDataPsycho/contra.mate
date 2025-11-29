from loguru import logger
from pydantic import BaseModel
from pydantic_ai import Agent
from contramate.core.agents import PyadanticAIModelUtilsFactory


SYSTEM_PROMPT = """
You are an expert at updating questions to make them ask for one thing only, more atomic, specific and easier to find the answer for.
You do this by filling in missing information in the question, with the extra information provided to you in previous answers. 

You respond with the updated question that has all information in it.
Only edit the question if needed. If the original question already is atomic, specific and easy to answer, you keep the original.
Do not ask for more information than the original question. Only rephrase the question to make it more complete.
You can also convert any known abbreviations to their full forms but also keep the abbreviations in parentheses next to the full form.
"""

class QueryRewriteResponse(BaseModel):
    updated: bool
    rewritten_query: str


class QueryRewriterAgentFactory:
    """Factory to create Query Rewriter Agent with model settings from environment."""

    @staticmethod
    def create_default() -> Agent[QueryRewriteResponse]:
        """
        Create a Query Rewriter Agent instance with settings from environment.

        Returns:
            Agent[QueryRewriteResponse] ready to process queries with .run()
        """
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        return Agent(
            model=model,
            instructions=SYSTEM_PROMPT,
            output_type=QueryRewriteResponse,
            model_settings=model_settings,
        )

    @staticmethod
    def from_env_file(env_path: str) -> Agent[QueryRewriteResponse]:
        """
        Create a Query Rewriter Agent instance from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Agent[QueryRewriteResponse] ready to process queries with .run()
        """
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path=env_path)

        return Agent(
            model=model,
            instructions=SYSTEM_PROMPT,
            output_type=QueryRewriteResponse,
            model_settings=model_settings,
        )


if __name__ == "__main__":
    import asyncio
    from contramate.models import MessageHistory

    async def test_agent():
        # Create agent once - reusable for multiple queries
        logger.info("=== Creating Query Rewriter Agent ===")
        agent = QueryRewriterAgentFactory.create_default()

        previous_answer = "The contract is between Acme Corp and Beta LLC, signed on January 1, 2023, for software development services. The termination clause states that either party may terminate the contract with a 30-day written notice."

        # Test 1: Query rewriting with conversation history
        logger.info("\n=== Test 1: Query Rewriting with History ===")
        user_query_1 = "What is the termination term found in the contract?"

        # Build conversation history
        message_dicts_1 = [
            {
                "role": "user",
                "content": "What are the key details of this contract?",
                "timestamp": "2024-10-01T12:00:00Z"
            },
            {
                "role": "assistant",
                "content": previous_answer
            },
        ]
        message_history_1 = MessageHistory.model_validate({"messages": message_dicts_1})
        pydantic_messages_1 = message_history_1.to_pydantic_ai_messages()

        logger.info("Original Query: {}", user_query_1)
        result_1 = await agent.run(user_query_1, pydantic_messages_1)

        print("\n--- Query Rewrite Result (Test 1) ---")
        print(f"Updated: {result_1.output.updated}")
        print(f"Rewritten Query: {result_1.output.rewritten_query}")

        # Test 2: Query rewriting without history (reusing same agent)
        logger.info("\n=== Test 2: Query Rewriting without History (Reusing Agent) ===")
        user_query_2 = "What are the payment terms?"

        logger.info("Original Query: {}", user_query_2)
        result_2 = await agent.run(user_query_2)

        print("\n--- Query Rewrite Result (Test 2) ---")
        print(f"Updated: {result_2.output.updated}")
        print(f"Rewritten Query: {result_2.output.rewritten_query}")

        # Show usage
        print("\n--- Total Usage Information ---")
        usage_1 = result_1.usage()
        usage_2 = result_2.usage()
        print(f"Test 1 - Tokens: {usage_1.total_tokens}")
        print(f"Test 2 - Tokens: {usage_2.total_tokens}")
        print(f"Total Tokens Used: {usage_1.total_tokens + usage_2.total_tokens}")

    asyncio.run(test_agent())