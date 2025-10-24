"""Service layer for Contract Metadata Insight agent."""

from typing import Any, Dict, Optional, List
from loguru import logger
from neopipe import Result, Ok, Err

from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgent,
    ContractMetadataInsightAgentFactory,
    ResponseValidationError,
)


class ContractMetadataInsightService:
    """Service for managing Contract Metadata Insight agent interactions."""

    def __init__(
        self,
        agent: Optional[ContractMetadataInsightAgent] = None,
    ):
        """
        Initialize ContractMetadataInsightService.

        Args:
            agent: Optional pre-configured agent. If None, creates default agent.
        """
        self.agent = agent or ContractMetadataInsightAgentFactory.create_default()

    async def query(
        self,
        user_query: str,
        filters: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None,
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Process a user query about contract metadata using SQL generation.

        Args:
            user_query: The user's analytical question
            filters: Optional filters to apply to queries (e.g., specific projects, contract types)
            message_history: Optional conversation history in OpenAI format
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Returns:
            Result[Ok, Err]: Ok with answer and citations if successful,
                           Err with error details if failed

        Example:
            >>> service = ContractMetadataInsightService()
            >>> result = await service.query(
            ...     "How many contracts have non-compete clauses?",
            ...     filters={"contract_type": ["Service Agreement"]}
            ... )
            >>> if result.is_ok():
            ...     data = result.unwrap()
            ...     print(data["answer"])
            ...     print(data["citations"])
        """
        try:
            logger.info(f"Processing metadata query: {user_query[:100]}...")
            logger.info(f"Filters: {filters}")
            logger.info(
                f"Message history: {len(message_history) if message_history else 0} messages"
            )

            # Run agent
            result = await self.agent.run(
                user_query=user_query,
                filters=filters,
                message_history=message_history,
            )

            # Check if agent succeeded
            if result.get("success"):
                logger.info("Query completed successfully")
                return Ok(
                    {
                        "success": True,
                        "answer": result["answer"],
                        "citations": result["citations"],
                        "metadata": {
                            "filters_applied": filters is not None,
                            "message_history_used": message_history is not None,
                        },
                    }
                )
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Agent failed: {error_msg}")
                return Err(
                    {
                        "success": False,
                        "error": error_msg,
                        "message": f"Failed to process query: {error_msg}",
                        "answer": result.get("answer", ""),
                        "citations": result.get("citations", {}),
                    }
                )

        except ResponseValidationError as e:
            logger.error(f"Response validation failed after retries: {e}")
            return Err(
                {
                    "success": False,
                    "error": f"Validation error: {str(e)}",
                    "message": f"Response validation failed: {str(e)}",
                    "answer": "",
                    "citations": {},
                }
            )
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return Err(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to process query: {str(e)}",
                    "answer": "",
                    "citations": {},
                }
            )


class ContractMetadataInsightServiceFactory:
    """Factory for creating ContractMetadataInsightService instances."""

    @staticmethod
    def create_default() -> ContractMetadataInsightService:
        """
        Create a ContractMetadataInsightService with default settings.

        Returns:
            Configured ContractMetadataInsightService instance

        Example:
            >>> service = ContractMetadataInsightServiceFactory.create_default()
            >>> result = await service.query("What are the top contract types?")
        """
        return ContractMetadataInsightService()

    @staticmethod
    def from_env_file(env_path: str) -> ContractMetadataInsightService:
        """
        Create a ContractMetadataInsightService from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured ContractMetadataInsightService instance

        Example:
            >>> service = ContractMetadataInsightServiceFactory.from_env_file(".env")
            >>> result = await service.query("Count contracts by governing law")
        """
        agent = ContractMetadataInsightAgentFactory.from_env_file(env_path)
        return ContractMetadataInsightService(agent=agent)
