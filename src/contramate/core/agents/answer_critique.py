from loguru import logger
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from contramate.core.agents import PyadanticAIModelUtilsFactory
from pydantic_ai.run import AgentRunResult


SYSTEM_PROMPT = """
You are an expert at identifying if questions have been fully answered or if there is an opportunity to enrich the answer.
The user will provide a question, and you will scan through the provided information to see if the question is answered.
If anything is missing from the answer, you will provide a set of new questions that can be asked to gather the missing information.
All new questions must be complete, atomic and specific.

Special cases:
- If user asks for summary of a certain contract, as the summary is pulled by the tool, you will respond with an empty list.
- If user asks to compare contracts, as the comparison is done by the tool, you will respond with an empty list.

However, if the provided information is enough to answer the original question, you will respond with an empty list.
"""

USER_PROMPT_TEMPLATE = """User Question: {user_question}

Answer: {provided_answer}

Please analyze if the answer fully addresses the user's question. If information is missing, provide specific follow-up questions.
"""

class AnswerCritiqueResponse(BaseModel):
    """Response model for answer critique containing follow-up questions."""
    questions: list[str] = Field(
        default_factory=list,
        description="List of follow-up questions to gather missing information. Empty if answer is complete."
    )


class AnswerCritiqueAgent:
    """
    Answer Critique Agent - stateless and reusable.

    This agent evaluates if a provided answer fully addresses a user's question.
    It can be instantiated once and used multiple times with different queries.
    """

    def __init__(self, agent: Agent[AnswerCritiqueResponse]) -> None:
        """
        Initialize with a pydantic-ai agent.

        Args:
            agent: Configured Pydantic AI agent
        """
        self.agent = agent

    async def run(
        self,
        user_query: str,
        provided_answer: str
    ) -> AgentRunResult[AnswerCritiqueResponse]:
        """
        Evaluate if the provided answer fully addresses the user's question.

        Args:
            user_query: The user's original question
            provided_answer: The answer to evaluate

        Returns:
            AgentRunResult with follow-up questions if answer is incomplete
        """
        # Create user prompt with question and answer for evaluation
        user_prompt = USER_PROMPT_TEMPLATE.format(
            user_question=user_query,
            provided_answer=provided_answer
        )

        return await self.agent.run(user_prompt=user_prompt)

    @classmethod
    def create_default(cls) -> "AnswerCritiqueAgent":
        """
        Create a reusable Answer Critique Agent instance with settings from environment.

        Returns:
            AnswerCritiqueAgent instance ready to process multiple queries
        """
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=AnswerCritiqueResponse,
            model_settings=model_settings,
        )
        return cls(agent=agent)

    @classmethod
    def from_env_file(cls, env_path: str) -> "AnswerCritiqueAgent":
        """
        Create a reusable Answer Critique Agent instance from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            AnswerCritiqueAgent instance ready to process multiple queries
        """
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path=env_path)

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=AnswerCritiqueResponse,
            model_settings=model_settings,
        )
        return cls(agent=agent)


if __name__ == "__main__":
    import asyncio

    async def test_agent():
        # Create agent once - reusable for multiple queries
        logger.info("=== Creating Answer Critique Agent ===")
        agent = AnswerCritiqueAgent.create_default()

        # Test 1: Incomplete answer
        logger.info("\n=== Test 1: Incomplete Answer ===")
        user_question_1 = "What are the payment terms and penalties in the contract?"
        provided_answer_1 = "The contract specifies payment terms of Net 30 days. Payment should be made within 30 days of invoice receipt."

        logger.info("User Question: {}", user_question_1)
        logger.info("Provided Answer: {}", provided_answer_1)

        result_1 = await agent.run(user_question_1, provided_answer_1)

        print("\n--- Answer Critique Result (Test 1) ---")
        print(f"Follow-up Questions Needed: {len(result_1.output.questions)}")

        if result_1.output.questions:
            print("\nMissing Information - Suggested Questions:")
            for idx, question in enumerate(result_1.output.questions, 1):
                print(f"  {idx}. {question}")
        else:
            print("✓ Answer is complete")

        # Test 2: Complete answer (reusing same agent instance)
        logger.info("\n=== Test 2: Complete Answer (Reusing Agent) ===")
        user_question_2 = "What are the payment terms in the contract?"
        provided_answer_2 = "The contract specifies payment terms of Net 30 days with a 2% late fee for overdue payments and a 2% early payment discount if paid within 10 days."

        logger.info("User Question: {}", user_question_2)
        logger.info("Provided Answer: {}", provided_answer_2)

        result_2 = await agent.run(user_question_2, provided_answer_2)

        print("\n--- Answer Critique Result (Test 2) ---")
        print(f"Follow-up Questions Needed: {len(result_2.output.questions)}")

        if result_2.output.questions:
            print("\nMissing Information - Suggested Questions:")
            for idx, question in enumerate(result_2.output.questions, 1):
                print(f"  {idx}. {question}")
        else:
            print("✓ Answer is complete")

        print("\n--- Total Usage Information ---")
        usage_1 = result_1.usage()
        usage_2 = result_2.usage()
        print(f"Test 1 - Tokens: {usage_1.total_tokens}")
        print(f"Test 2 - Tokens: {usage_2.total_tokens}")
        print(f"Total Tokens Used: {usage_1.total_tokens + usage_2.total_tokens}")

    asyncio.run(test_agent())