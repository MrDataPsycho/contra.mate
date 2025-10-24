"""Status controller for service health checks."""

from fastapi import APIRouter, Depends


from contramate.services.postgres_status_service import PostgresService
from contramate.services.dynamodb_status_service import DynamoDBStatusService
from contramate.services.opensearch_status_service import OpenSearchStatusService
from contramate.services.openai_status_service import OpenAIStatusService
from contramate.llm import OpenAIChatClient


router = APIRouter(prefix="/api", tags=["status"])


# Dependency injection
def get_postgres_service() -> PostgresService:
    """Get PostgreSQL status service instance."""
    return PostgresService()


def get_dynamodb_service() -> DynamoDBStatusService:
    """Get DynamoDB status service instance."""
    return DynamoDBStatusService()


def get_opensearch_service() -> OpenSearchStatusService:
    """Get OpenSearch status service instance."""
    return OpenSearchStatusService()


def get_openai_service() -> OpenAIStatusService:
    """Get OpenAI status service instance."""
    openai_client = OpenAIChatClient()
    return OpenAIStatusService(client=openai_client)


# Endpoints
@router.get("/opensearch/status")
async def opensearch_status(
    service: OpenSearchStatusService = Depends(get_opensearch_service),
):
    """Check OpenSearch connection status."""
    return await service.check_status()


@router.get("/postgres/status")
async def postgres_status(
    service: PostgresService = Depends(get_postgres_service),
):
    """Check PostgreSQL connection status."""
    return await service.check_status()


@router.get("/dynamodb/status")
async def dynamodb_status(
    service: DynamoDBStatusService = Depends(get_dynamodb_service),
):
    """Check DynamoDB connection status."""
    return await service.check_status()


@router.get("/openai/status")
async def openai_status(
    service: OpenAIStatusService = Depends(get_openai_service),
):
    """Check OpenAI API connection status."""
    return await service.check_status()
