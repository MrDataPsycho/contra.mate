"""Contracts controller for contract-related endpoints."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from loguru import logger
from pydantic import BaseModel, Field

from contramate.services.contract_service import ContractService, ContractServiceFactory


router = APIRouter(prefix="/api/contracts", tags=["contracts"])


# Schemas
class DocumentResponse(BaseModel):
    """Response model for a contract document"""
    project_id: str
    reference_doc_id: str
    document_title: str
    contract_type: Optional[str] = None
    document_name: Optional[str] = None
    parties: Optional[str] = None
    agreement_date: Optional[str] = None
    effective_date: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response model for list of documents"""
    documents: List[DocumentResponse]
    count: int


class ContractTypesResponse(BaseModel):
    """Response model for contract types"""
    contract_types: List[str]
    count: int


class ProjectIdsResponse(BaseModel):
    """Response model for project IDs"""
    project_ids: List[str]
    count: int


# Dependency injection
def get_contract_service() -> ContractService:
    """Get ContractService instance"""
    return ContractServiceFactory.create_default()


# Endpoints
@router.get("/documents", response_model=DocumentListResponse)
async def get_documents(
    limit: int = Query(1000, description="Maximum number of documents to return"),
    contract_type: Optional[str] = Query(None, description="Filter by contract type"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    service: ContractService = Depends(get_contract_service)
):
    """
    Get all contract documents from the database.

    This endpoint returns a list of contract documents with their metadata.
    You can filter by contract type and/or project ID.

    Args:
        limit: Maximum number of documents to return (default: 1000)
        contract_type: Optional filter by contract type
        project_id: Optional filter by project ID
        service: ContractService instance

    Returns:
        List of documents with metadata

    Example:
        GET /api/contracts/documents?limit=10&contract_type=Affiliate_Agreements
    """
    try:
        logger.info(f"Fetching documents (limit={limit}, contract_type={contract_type}, project_id={project_id})")

        result = service.get_all_documents(
            limit=limit,
            contract_type=contract_type,
            project_id=project_id
        )

        if result.is_ok():
            documents = result.unwrap()
            return DocumentListResponse(
                documents=documents,
                count=len(documents)
            )
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error fetching documents")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching documents: {str(e)}"
        )


@router.get("/documents/{project_id}/{reference_doc_id}", response_model=DocumentResponse)
async def get_document_by_id(
    project_id: str,
    reference_doc_id: str,
    service: ContractService = Depends(get_contract_service)
):
    """
    Get a specific document by project_id and reference_doc_id.

    Args:
        project_id: Project identifier
        reference_doc_id: Reference document identifier
        service: ContractService instance

    Returns:
        Document with metadata

    Example:
        GET /api/contracts/documents/00149794-2432-4c18-b491-73d0fafd3efd/577ff0a3-a032-5e23-bde3-0b6179e97949
    """
    try:
        logger.info(f"Fetching document: project_id={project_id}, reference_doc_id={reference_doc_id}")

        result = service.get_document_by_id(
            project_id=project_id,
            reference_doc_id=reference_doc_id
        )

        if result.is_ok():
            return result.unwrap()
        else:
            error_details = result.unwrap_err()
            if "not found" in error_details.get("error", "").lower():
                raise HTTPException(status_code=404, detail=error_details.get("message"))
            else:
                raise HTTPException(status_code=500, detail=error_details.get("message"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching document: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching document: {str(e)}"
        )


@router.get("/contract-types", response_model=ContractTypesResponse)
async def get_contract_types(
    service: ContractService = Depends(get_contract_service)
):
    """
    Get all unique contract types from the database.

    Returns:
        List of contract types

    Example:
        GET /api/contracts/contract-types
    """
    try:
        logger.info("Fetching contract types")

        result = service.get_contract_types()

        if result.is_ok():
            contract_types = result.unwrap()
            return ContractTypesResponse(
                contract_types=contract_types,
                count=len(contract_types)
            )
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error fetching contract types")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contract types: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching contract types: {str(e)}"
        )


@router.get("/project-ids", response_model=ProjectIdsResponse)
async def get_project_ids(
    service: ContractService = Depends(get_contract_service)
):
    """
    Get all unique project IDs from the database.

    Returns:
        List of project IDs

    Example:
        GET /api/contracts/project-ids
    """
    try:
        logger.info("Fetching project IDs")

        result = service.get_project_ids()

        if result.is_ok():
            project_ids = result.unwrap()
            return ProjectIdsResponse(
                project_ids=project_ids,
                count=len(project_ids)
            )
        else:
            error_details = result.unwrap_err()
            logger.error(f"Service returned error: {error_details}")
            raise HTTPException(
                status_code=500,
                detail=error_details.get("message", "Error fetching project IDs")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching project IDs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching project IDs: {str(e)}"
        )
