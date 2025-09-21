from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from contramate.services.postgres_status_service import PostgresService
from contramate.services.dynamodb_status_service import DynamoDBStatusService
from contramate.services.opensearch_status_service import OpenSearchStatusService
from contramate.services.openai_status_service import OpenAIStatusService
from contramate.services.litellm_status_service import LiteLLMStatusService
from contramate.utils.clients.ai import OpenAIChatClient, LiteLLMChatClient

app = FastAPI(
    title="Contramate API",
    description="A Conversational AI Agent Application for Contract Understanding using CUAD Dataset",
    version="0.1.0"
)

# Initialize clients and services with dependency injection
openai_client = OpenAIChatClient()
litellm_client = LiteLLMChatClient()

# Initialize services with injected dependencies
postgres_service = PostgresService()
dynamodb_service = DynamoDBStatusService()
opensearch_service = OpenSearchStatusService()
openai_service = OpenAIStatusService(client=openai_client)
litellm_service = LiteLLMStatusService(client=litellm_client)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Contramate API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": os.getenv("RUNTIME_ENV", "unknown"),
        "host_system": os.getenv("HOST_SYSTEM", "unknown")
    }

@app.get("/api/contracts")
async def get_contracts():
    """Get contracts from CUAD dataset"""
    return {
        "message": "Contracts endpoint - to be implemented",
        "contracts": []
    }

@app.post("/api/search")
async def search_contracts(query: dict):
    """Search contracts using vector search"""
    return {
        "message": "Search endpoint - to be implemented",
        "query": query.get("query", ""),
        "results": []
    }

@app.get("/api/opensearch/status")
async def opensearch_status():
    """Check OpenSearch connection status"""
    return await opensearch_service.check_status()

@app.get("/api/postgres/status")
async def postgres_status():
    """Check PostgreSQL connection status"""
    return await postgres_service.check_status()

@app.get("/api/dynamodb/status")
async def dynamodb_status():
    """Check DynamoDB connection status"""
    return await dynamodb_service.check_status()

@app.get("/api/openai/status")
async def openai_status():
    """Check OpenAI API connection status"""
    return await openai_service.check_status()

@app.get("/api/litellm/status")
async def litellm_status():
    """Check LiteLLM API connection status"""
    return await litellm_service.check_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)