from pydantic import Field
from .base import ABCBaseSettings


class PostgresSettings(ABCBaseSettings):
    """PostgreSQL database settings"""
    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    database: str = Field(default="cuad", description="PostgreSQL database name")
    user: str = Field(default="cuad_user", description="PostgreSQL username")
    password: str = Field(default="cuad_password", description="PostgreSQL password")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "POSTGRES_"

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DynamoDBSettings(ABCBaseSettings):
    """DynamoDB settings"""
    endpoint_url: str = Field(default="http://localhost:8001", description="DynamoDB endpoint URL")
    region: str = Field(default="us-east-1", description="AWS region")
    access_key_id: str = Field(default="dummy", description="AWS access key ID")
    secret_access_key: str = Field(default="dummy", description="AWS secret access key")
    table_name: str = Field(default="ConversationTable", description="DynamoDB table name for conversations")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "DYNAMODB_"


class OpenSearchSettings(ABCBaseSettings):
    """OpenSearch settings"""
    host: str = Field(default="localhost", description="OpenSearch host")
    port: int = Field(default=9200, description="OpenSearch port")
    use_ssl: bool = Field(default=False, description="Use SSL for OpenSearch connection")
    verify_certs: bool = Field(default=False, description="Verify SSL certificates")
    username: str | None = Field(default=None, description="OpenSearch username")
    password: str | None = Field(default=None, description="OpenSearch password")
    index_name: str | None = Field(default=None, description="OpenSearch index name")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "OPENSEARCH_"

    @property
    def endpoint_url(self) -> str:
        """Get OpenSearch endpoint URL"""
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}"

    def get_index_name(self) -> str:
        """Get index name from environment or fallback to app settings default"""
        if self.index_name:
            return self.index_name

        # Fallback to default
        return "contracts-test"


class OpenAISettings(ABCBaseSettings):
    """OpenAI API settings"""
    api_key: str | None = Field(default=None, description="OpenAI API key")
    model: str = Field(default="gpt-5-mini", description="Default OpenAI model")
    embedding_model: str = Field(..., description="OpenAI embedding model (required, must be set in env)")
    temperature: float = Field(default=0.7, description="Default temperature for completions")
    max_tokens: int = Field(default=1000, description="Default max tokens for completions")
    base_url: str | None = Field(default=None, description="Custom OpenAI API base URL")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "OPENAI_"


class AOAICertSettings(ABCBaseSettings):
    """Azure OpenAI Certificate-based authentication settings"""
    tenant_id: str = Field(description="Azure tenant ID")
    client_id: str = Field(description="Azure client ID")
    resource: str = Field(default="https://cognitiveservices.azure.com", description="Azure cognitive services resource")
    public_cert_key: str = Field(description="Public certificate key content")
    private_cert_key: str = Field(description="Private certificate key content")
    azure_endpoint: str = Field(description="Azure OpenAI endpoint URL")
    api_version: str = Field(default="2023-05-15", description="Azure OpenAI API version")
    model: str = Field(default="gpt-4", description="Default Azure OpenAI model")
    embedding_model: str = Field(..., description="Azure OpenAI embedding model (required, must be set in env)")
    temperature: float = Field(default=0.7, description="Default temperature for completions")
    max_tokens: int = Field(default=1000, description="Default max tokens for completions")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "AZURE_OPENAI_"

    @property
    def certificate_string(self) -> str:
        """Get certificate string combining public and private keys"""
        return self.private_cert_key.encode() + b"\n" + self.public_cert_key.encode()


class AppSettings(ABCBaseSettings):
    """Application settings"""
    app_name: str = Field(default="Contramate", description="Application name")
    environment: str = Field(default="local", description="Environment (local, dev, prod)")
    debug: bool = Field(default=True, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Application host")
    port: int = Field(default=8000, description="Application port")
    vector_dimension: int = Field(description="Vector dimension for embeddings (e.g., 1536 for text-embedding-3-small, 3072 for text-embedding-3-large)")
    default_index_name: str = Field(default="contracts-test", description="Default OpenSearch index name")
    llm_provider: str = Field(default="openai", description="Default LLM provider: 'openai' or 'azure_openai'")

    model_config = ABCBaseSettings.model_config.copy()
    model_config["env_prefix"] = "APP_"


if __name__ == "__main__":
    from loguru import logger
    logger.info("setting")