"""
Settings Factory

Factory to create settings instances without using singleton pattern.
Provides methods to create individual setting objects as needed.
"""

from contramate.utils.settings.core import (
    PostgresSettings,
    DynamoDBSettings,
    OpenSearchSettings,
    OpenAISettings,
    AOAICertSettings,
    AppSettings
)


class SettingsFactory:
    """Factory for creating settings instances"""
    
    @staticmethod
    def create_postgres_settings() -> PostgresSettings:
        """Create PostgreSQL settings instance"""
        return PostgresSettings()
    
    @staticmethod
    def create_dynamodb_settings() -> DynamoDBSettings:
        """Create DynamoDB settings instance"""
        return DynamoDBSettings()
    
    @staticmethod
    def create_opensearch_settings() -> OpenSearchSettings:
        """Create OpenSearch settings instance"""
        return OpenSearchSettings()
    
    @staticmethod
    def create_openai_settings() -> OpenAISettings:
        """Create OpenAI settings instance"""
        return OpenAISettings()
    
    @staticmethod
    def create_azure_openai_settings() -> AOAICertSettings:
        """Create Azure OpenAI settings instance"""
        return AOAICertSettings()
    
    @staticmethod
    def create_app_settings() -> AppSettings:
        """Create app settings instance"""
        return AppSettings()


# Convenience factory instance for easy importing
settings_factory = SettingsFactory()