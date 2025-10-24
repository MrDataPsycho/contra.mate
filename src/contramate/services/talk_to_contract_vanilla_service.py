"""Service layer for vanilla OpenAI Talk To Contract agent."""

from typing import Any, Dict, Optional, List
from loguru import logger
from neopipe import Result, Ok, Err
from contramate.core.agents.talk_to_contract_vanilla import (
    TalkToContractVanillaAgent,
    TalkToContractVanillaAgentFactory,
    ResponseValidationError,
)


class TalkToContractVanillaService:
    """Service for managing vanilla Talk To Contract agent interactions."""

    def __init__(
        self,
        agent: Optional[TalkToContractVanillaAgent] = None,
    ):
        """
        Initialize TalkToContractVanillaService.

        Args:
            agent: Optional pre-configured agent. If None, creates default agent.
        """
        self.agent = agent or TalkToContractVanillaAgentFactory.create_default()

    async def query(
        self,
        user_query: str,
        filters: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None,
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Process a user query using the vanilla Talk To Contract agent.

        Args:
            user_query: The user's question about contracts
            filters: Optional filters to apply to searches (e.g., specific documents, contract types)
            message_history: Optional conversation history in OpenAI format
                [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

        Returns:
            Result[Ok, Err]: Ok with answer, citations, and metadata if successful, Err with error details if failed
        """
        try:
            logger.info(f"Processing query: {user_query[:100]}...")
            logger.info(f"Filters: {filters}")
            logger.info(f"Message history: {len(message_history) if message_history else 0} messages")

            # Run agent
            result = await self.agent.run(
                user_query=user_query,
                filters=filters,
                message_history=message_history,
            )

            # Check if agent succeeded
            if result.get("success"):
                logger.info("Query completed successfully")
                return Ok({
                    "success": True,
                    "answer": result["answer"],
                    "citations": result["citations"],
                    "metadata": {
                        "filters_applied": filters is not None,
                        "message_history_used": message_history is not None,
                    },
                })
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Agent failed: {error_msg}")
                return Err({
                    "success": False,
                    "error": error_msg,
                    "message": f"Failed to process query: {error_msg}",
                    "answer": result.get("answer", ""),
                    "citations": result.get("citations", {}),
                })

        except ResponseValidationError as e:
            logger.error(f"Response validation failed after retries: {e}")
            return Err({
                "success": False,
                "error": f"Validation error: {str(e)}",
                "message": f"Response validation failed: {str(e)}",
                "answer": "",
                "citations": {},
            })
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return Err({
                "success": False,
                "error": str(e),
                "message": f"Failed to process query: {str(e)}",
                "answer": "",
                "citations": {},
            })


class TalkToContractVanillaServiceFactory:
    """Factory for creating TalkToContractVanillaService instances."""

    @staticmethod
    def create_default() -> TalkToContractVanillaService:
        """
        Create a TalkToContractVanillaService with default settings.

        Returns:
            Configured TalkToContractVanillaService instance
        """
        return TalkToContractVanillaService()

    @staticmethod
    def from_env_file(env_path: str) -> TalkToContractVanillaService:
        """
        Create a TalkToContractVanillaService from environment file.

        Args:
            env_path: Path to environment file

        Returns:
            Configured TalkToContractVanillaService instance
        """
        agent = TalkToContractVanillaAgentFactory.from_env_file(env_path)
        return TalkToContractVanillaService(agent=agent)
