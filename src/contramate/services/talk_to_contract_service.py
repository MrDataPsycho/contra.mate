"""Service layer for Talk To Contract agent interactions."""

from typing import Any, Dict, Optional, List
from loguru import logger
from neopipe import Result, Ok, Err
from pydantic_ai import Agent
from contramate.core.agents.talk_to_contract import (
    TalkToContractAgentFactory,
    TalkToContractDependencies,
    TalkToContractResponse,
)
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchServiceFactory,
)
from contramate.models import MessageHistory


class TalkToContractService:
    """Service for managing Talk To Contract agent interactions."""

    def __init__(
        self,
        agent: Optional[Agent[TalkToContractResponse, TalkToContractDependencies]] = None,
    ):
        """
        Initialize TalkToContractService.

        Args:
            agent: Optional pre-configured agent. If None, creates default agent.
        """
        self.agent = agent or TalkToContractAgentFactory.create_default()
        self.search_service = OpenSearchVectorSearchServiceFactory.create_default()

    async def query(
        self,
        user_query: str,
        filters: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Process a user query using the Talk To Contract agent.

        Args:
            user_query: The user's question about contracts
            filters: Optional filters to apply to searches (e.g., specific documents, contract types)
            message_history: Optional conversation history for context

        Returns:
            Result[Ok, Err]: Ok with answer, citations, and metadata if successful, Err with error details if failed
        """
        try:
            logger.info(f"Processing query: {user_query[:100]}...")
            logger.info(f"Filters: {filters}")

            # Create dependencies with search service and filters
            deps = TalkToContractDependencies(
                search_service=self.search_service,
                filters=filters,
            )

            # Convert message history if provided
            pydantic_messages = None
            if message_history:
                try:
                    msg_history = MessageHistory.model_validate(
                        {"messages": message_history}
                    )
                    pydantic_messages = msg_history.to_pydantic_ai_messages()
                    logger.info(f"Using conversation history with {len(message_history)} messages")
                    logger.debug(f"Converted message types: {[type(msg).__name__ for msg in pydantic_messages]}")
                except Exception as e:
                    logger.warning(f"Failed to convert message history: {e}")
                    logger.exception("Message history conversion error:")

            # Run agent
            try:
                result = await self.agent.run(
                    user_query,
                    deps=deps,
                    message_history=pydantic_messages,
                )

                # Extract response
                response = result.output
                usage = result.usage()

                logger.info(f"Query completed. Tokens used: {usage.total_tokens}")

                return Ok({
                    "success": True,
                    "answer": response.answer,
                    "citations": response.citations,
                    "metadata": {
                        "tokens_used": usage.total_tokens,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "filters_applied": filters is not None,
                    },
                })
            except Exception as agent_error:
                # Log the detailed error for validation failures
                logger.error(f"Agent execution failed: {agent_error}")
                if hasattr(agent_error, '__cause__'):
                    logger.error(f"Caused by: {agent_error.__cause__}")
                raise

        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return Err({
                "success": False,
                "error": str(e),
                "message": f"Failed to process query: {str(e)}",
                "answer": "",
                "citations": {},
            })


class TalkToContractServiceFactory:
    """Factory for creating TalkToContractService instances."""

    @staticmethod
    def create_default() -> TalkToContractService:
        """
        Create a TalkToContractService with default settings.

        Returns:
            Configured TalkToContractService instance
        """
        return TalkToContractService()

    @staticmethod
    def from_env_file(env_path: str) -> TalkToContractService:
        """
        Create a TalkToContractService from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured TalkToContractService instance
        """
        agent = TalkToContractAgentFactory.from_env_file(env_path)
        return TalkToContractService(agent=agent)
