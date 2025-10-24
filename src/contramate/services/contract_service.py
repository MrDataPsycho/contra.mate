"""
Service for contract-related database operations.

Provides methods to fetch contract documents from PostgreSQL.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
from sqlmodel import Session, create_engine, select
from neopipe import Result, Ok, Err

from contramate.dbs.models.contract import ContractAsmd
from contramate.utils.settings.core import PostgresSettings


class ContractService:
    """Service for contract database operations"""

    def __init__(self, postgres_settings: Optional[PostgresSettings] = None):
        """
        Initialize contract service.

        Args:
            postgres_settings: PostgreSQL settings. If None, uses default settings.
        """
        self.settings = postgres_settings or PostgresSettings()
        self.engine = create_engine(self.settings.connection_string)
        logger.info(f"Initialized ContractService with database: {self.settings.database}")

    def get_all_documents(
        self,
        limit: int = 1000,
        contract_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Result[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get all contract documents from contract_asmd table.

        Args:
            limit: Maximum number of documents to return
            contract_type: Optional filter by contract type
            project_id: Optional filter by project ID

        Returns:
            Result with list of documents or error
        """
        try:
            with Session(self.engine) as session:
                # Build query
                statement = select(ContractAsmd)

                # Apply filters
                if contract_type:
                    statement = statement.where(ContractAsmd.contract_type == contract_type)
                if project_id:
                    statement = statement.where(ContractAsmd.project_id == project_id)

                # Add limit
                statement = statement.limit(limit)

                # Execute query
                results = session.exec(statement).all()

                # Convert to dict format
                documents = [
                    {
                        "project_id": doc.project_id,
                        "reference_doc_id": doc.reference_doc_id,
                        "document_title": doc.document_title,
                        "contract_type": doc.contract_type,
                        "document_name": doc.document_name,
                        "parties": doc.parties_answer,
                        "agreement_date": doc.agreement_date_answer,
                        "effective_date": doc.effective_date_answer,
                    }
                    for doc in results
                ]

                logger.info(f"Retrieved {len(documents)} documents from database")
                return Ok(documents)

        except Exception as e:
            logger.error(f"Error fetching documents: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": "Failed to fetch documents from database"
            })

    def get_document_by_id(
        self,
        project_id: str,
        reference_doc_id: str
    ) -> Result[Dict[str, Any], Dict[str, Any]]:
        """
        Get a specific document by project_id and reference_doc_id.

        Args:
            project_id: Project identifier
            reference_doc_id: Reference document identifier

        Returns:
            Result with document data or error
        """
        try:
            with Session(self.engine) as session:
                statement = select(ContractAsmd).where(
                    ContractAsmd.project_id == project_id,
                    ContractAsmd.reference_doc_id == reference_doc_id
                )

                result = session.exec(statement).first()

                if not result:
                    return Err({
                        "error": "Document not found",
                        "message": f"No document found with project_id={project_id}, reference_doc_id={reference_doc_id}"
                    })

                document = {
                    "project_id": result.project_id,
                    "reference_doc_id": result.reference_doc_id,
                    "document_title": result.document_title,
                    "contract_type": result.contract_type,
                    "document_name": result.document_name,
                    "parties": result.parties_answer,
                    "agreement_date": result.agreement_date_answer,
                    "effective_date": result.effective_date_answer,
                }

                logger.info(f"Retrieved document: {result.document_title}")
                return Ok(document)

        except Exception as e:
            logger.error(f"Error fetching document: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": "Failed to fetch document from database"
            })

    def get_contract_types(self) -> Result[List[str], Dict[str, Any]]:
        """
        Get all unique contract types from the database.

        Returns:
            Result with list of contract types or error
        """
        try:
            with Session(self.engine) as session:
                statement = select(ContractAsmd.contract_type).distinct()
                results = session.exec(statement).all()

                # Filter out None values
                contract_types = [ct for ct in results if ct is not None]

                logger.info(f"Retrieved {len(contract_types)} contract types")
                return Ok(contract_types)

        except Exception as e:
            logger.error(f"Error fetching contract types: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": "Failed to fetch contract types from database"
            })

    def get_project_ids(self) -> Result[List[str], Dict[str, Any]]:
        """
        Get all unique project IDs from the database.

        Returns:
            Result with list of project IDs or error
        """
        try:
            with Session(self.engine) as session:
                statement = select(ContractAsmd.project_id).distinct()
                results = session.exec(statement).all()

                logger.info(f"Retrieved {len(results)} project IDs")
                return Ok(list(results))

        except Exception as e:
            logger.error(f"Error fetching project IDs: {e}", exc_info=True)
            return Err({
                "error": str(e),
                "message": "Failed to fetch project IDs from database"
            })


class ContractServiceFactory:
    """Factory for creating ContractService instances"""

    @staticmethod
    def create_default() -> ContractService:
        """Create ContractService with default PostgreSQL settings"""
        return ContractService()

    @staticmethod
    def create_with_settings(postgres_settings: PostgresSettings) -> ContractService:
        """Create ContractService with custom PostgreSQL settings"""
        return ContractService(postgres_settings=postgres_settings)
