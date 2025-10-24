"""Chat controller for handling chat-related HTTP requests"""

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from contramate.api.interfaces.controllers.schemas import (
    TalkToContractRequest,
    TalkToContractResponse,
)
from contramate.services.talk_to_contract_vanilla_service import (
    TalkToContractVanillaService,
    TalkToContractVanillaServiceFactory,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])


# Dependency injection
def get_talk_to_contract_service() -> TalkToContractVanillaService:
    """Get TalkToContractVanillaService instance."""
    return TalkToContractVanillaServiceFactory.create_default()


# Endpoints
@router.post("/", response_model=TalkToContractResponse)
async def chat(
    request: TalkToContractRequest,
    service: TalkToContractVanillaService = Depends(get_talk_to_contract_service),
):
    """
    Chat with contracts using the Talk To Contract agent.

    This endpoint allows you to ask questions about contracts and get
    AI-generated answers with proper citations.

    Args:
        request: Query request with user question, optional filters, and message history
        service: TalkToContractService instance

    Returns:
        Answer with citations and metadata

    Example request:
        ```json
        {
            "query": "What are the payment terms?",
            "filters": {
                "documents": [
                    {
                        "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                        "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
                    }
                ]
            },
            "message_history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"}
            ]
        }
        ```
    """
    try:
        logger.info(f"Received chat query: {request.query[:100]}...")

        result = await service.query(
            user_query=request.query,
            filters=request.filters,
            message_history=request.message_history,
        )

        # Handle Result type from service
        if result.is_ok():
            return result.unwrap()
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error processing query"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}",
        )
