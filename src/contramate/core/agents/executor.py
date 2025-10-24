"""
Executor Agent - Simple orchestration of sub-agents.

This will be built step by step to be simple and predictable.
"""
from loguru import logger
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pathlib import Path

from contramate.utils.settings.core import AgentToggleSettings
from contramate.core.agents import PyadanticAIModelUtilsFactory


@dataclass
class ExecutorDependencies:
    """Dependencies for the ExecutorAgent."""
    
    filters: Dict[str, Any] | None = None
    message_history: List[Dict[str, Any]] | None = None


class ExecutorResponse(BaseModel):
    """Response from the executor agent."""
    
    final_answer: str = Field(..., description="The final answer to the user's query")
    success: bool = Field(..., description="Whether execution was successful")


# We'll build this step by step
SYSTEM_PROMPT = """
You are a simple executor that will follow instructions.
"""


class ExecutorAgentFactory:
    """Factory for creating ExecutorAgent instances."""

    @staticmethod
    def create_default() -> Agent:
        """Create ExecutorAgent with default settings."""
        logger.info("🏭 Creating ExecutorAgent")

        settings = AgentToggleSettings()
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=ExecutorResponse,
            model_settings=model_settings,
            deps_type=ExecutorDependencies,
        )

        logger.info("✅ ExecutorAgent created")
        return agent

    @staticmethod
    def from_env_file(env_path: Path) -> Agent:
        """Create ExecutorAgent from environment file."""
        logger.info(f"🏭 Creating ExecutorAgent from {env_path}")

        settings = AgentToggleSettings.from_env_file(env_path)
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path)

        agent = Agent(
            model=model,
            system_prompt=SYSTEM_PROMPT,
            output_type=ExecutorResponse,
            model_settings=model_settings,
            deps_type=ExecutorDependencies,
        )

        logger.info("✅ ExecutorAgent created")
        return agent

    @staticmethod
    def create_dependencies(
        filters: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, Any]]] = None,
    ) -> ExecutorDependencies:
        """
        Create dependencies for the executor.
        
        Simple version - just holds filters and message history.
        """
        logger.info("🔧 Creating ExecutorDependencies")

        return ExecutorDependencies(
            filters=filters,
            message_history=message_history,
        )
