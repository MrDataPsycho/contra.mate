from pathlib import Path
from contramate.llm import LLMVanillaClientFactory
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from contramate.utils.settings.factory import settings_factory
from contramate.utils.settings.core import AppSettings, OpenAISettings, AOAICertSettings

class PyadanticAIModelUtilsFactory:
    """Factory utility to create pydantic model class to be used with pydantic-ai agents"""

    @staticmethod
    def create_default() -> tuple[OpenAIChatModel, ModelSettings]:
        """
        Create default pydantic model class for agent usage.

        Returns:
            Tuple of (OpenAIChatModel, ModelSettings) with temperature and seed from settings
        """
        app_settings = settings_factory.create_app_settings()

        # Get model name and settings based on LLM provider
        if app_settings.llm_provider == "azure_openai":
            llm_settings = settings_factory.create_azure_openai_settings()
        else:
            llm_settings = settings_factory.create_openai_settings()

        factory = LLMVanillaClientFactory()
        client = factory.get_default_client(async_mode=True)

        # Configure provider
        provider = OpenAIProvider(openai_client=client)

        model = OpenAIChatModel(
                llm_settings.model,
                provider=provider,
            )

        # Create ModelSettings from llm_settings with retry configuration
        # The OpenAI client handles retries automatically with exponential backoff
        model_settings = ModelSettings(
            temperature=llm_settings.temperature,
            max_tokens=llm_settings.max_tokens,
            seed=llm_settings.seed,
            max_retries=3,  # Retry up to 3 times on rate limit errors (429) and server errors (5xx)
        )

        return model, model_settings

    @staticmethod
    def from_env_file(env_path: str | Path) -> tuple[OpenAIChatModel, ModelSettings]:
        """
        Create pydantic model class for agent usage from environment variables.

        Args:
            env_path: Path to environment file

        Returns:
            Tuple of (OpenAIChatModel, ModelSettings) with temperature and seed from settings
        """
        app_settings = AppSettings.from_env_file(env_path)

        # Get model name and settings based on LLM provider
        if app_settings.llm_provider == "azure_openai":
            llm_settings = AOAICertSettings.from_env_file(env_path)
        else:
            llm_settings = OpenAISettings.from_env_file(env_path)

        factory = LLMVanillaClientFactory.from_env_file(env_path=env_path)
        client = factory.get_default_client(async_mode=True)

        # Configure provider
        provider = OpenAIProvider(openai_client=client)

        model = OpenAIChatModel(
                llm_settings.model,
                provider=provider,
            )

        # Create ModelSettings from llm_settings with retry configuration
        # The OpenAI client handles retries automatically with exponential backoff
        model_settings = ModelSettings(
            temperature=llm_settings.temperature,
            max_tokens=llm_settings.max_tokens,
            seed=llm_settings.seed,
            max_retries=3,  # Retry up to 3 times on rate limit errors (429) and server errors (5xx)
        )

        return model, model_settings
    

if __name__ == "__main__":
    env_path = Path(".envs").joinpath("local.env")

    model_1, settings_1 = PyadanticAIModelUtilsFactory.create_default()
    print("Model Type: ", type(model_1))
    print("Settings Type: ", type(settings_1))
    print("Settings: ", settings_1)

    model_2, settings_2 = PyadanticAIModelUtilsFactory.from_env_file(env_path=env_path)
    print("\nModel Type: ", type(model_2))
    print("Settings Type: ", type(settings_2))
    print("Settings: ", settings_2)

