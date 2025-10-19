"""
Metadata Extraction Service for extracting structured contract metadata.

This service orchestrates the MetadataParserAgent to extract metadata from contract text
and returns ContractEsmd model ready for database insertion.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from neopipe import Result, Ok, Err
from loguru import logger

from contramate.llm.base import BaseChatClient
from contramate.llm.factory import create_default_chat_client
from contramate.utils.settings.factory import settings_factory
from contramate.core.agents import MetadataParserAgent
from contramate.dbs.models.contract import ContractEsmd


class MetadataExtractionService:
    """
    Service for extracting structured metadata from contract documents.

    This is a high-level service that:
    - Uses MetadataParserAgent for extraction
    - Adds project_id, reference_doc_id, and processed_at
    - Returns Result type for error handling
    - Returns ContractEsmd model ready for database insertion
    """

    def __init__(
        self,
        client: BaseChatClient,
        encoding_name: str = "o200k_base"
    ):
        """
        Initialize metadata extraction service.

        Args:
            client: Chat client implementing BaseChatClient interface
            encoding_name: Tiktoken encoding name for token counting
        """
        self.client = client
        self.agent = MetadataParserAgent(client=client, encoding_name=encoding_name)

    async def extract_metadata(
        self,
        text: str,
        project_id: str,
        reference_doc_id: str,
        file_name: Optional[str] = None
    ) -> Result[ContractEsmd, str]:
        """
        Extract metadata from contract text.

        Args:
            text: Full contract text to extract metadata from
            project_id: Project identifier (required for ContractEsmd)
            reference_doc_id: Reference document identifier (required for ContractEsmd)
            file_name: Optional filename to add to metadata

        Returns:
            Result[ContractEsmd, str]: Ok with ContractEsmd model or Err with error message

        Example:
            >>> service = MetadataExtractionService(client=my_client)
            >>> result = await service.extract_metadata(
            ...     text=contract_text,
            ...     project_id="proj_001",
            ...     reference_doc_id="contract_001",
            ...     file_name="service_agreement.pdf"
            ... )
            >>> if result.is_ok():
            ...     contract = result.ok()
            ...     # Save to database
        """
        logger.info(
            f"Starting metadata extraction for document: {reference_doc_id}"
        )

        try:
            # Use agent to extract metadata (low-level API)
            metadata_dict = await self.agent.extract_metadata(text=text)

            # Add service-level fields
            metadata_dict["project_id"] = project_id
            metadata_dict["reference_doc_id"] = reference_doc_id
            metadata_dict["processed_at"] = datetime.now(timezone.utc)

            # Add optional file_name if provided
            if file_name:
                metadata_dict["file_name"] = file_name

            # Create ContractEsmd model (validates against SQLModel schema)
            contract_metadata = ContractEsmd(**metadata_dict)

            logger.info(
                f"Successfully extracted metadata for {reference_doc_id}: "
                f"{len(metadata_dict)} fields populated"
            )

            return Ok(contract_metadata)

        except Exception as e:
            error_msg = f"Metadata extraction failed for {reference_doc_id}: {str(e)}"
            logger.error(error_msg)
            return Err(error_msg)

    def execute(
        self,
        text: str,
        project_id: str,
        reference_doc_id: str,
        file_name: Optional[str] = None
    ) -> Result[ContractEsmd, str]:
        """
        Execute metadata extraction (synchronous wrapper).

        Args:
            text: Full contract text to extract metadata from
            project_id: Project identifier
            reference_doc_id: Reference document identifier
            file_name: Optional filename

        Returns:
            Result[ContractEsmd, str]: Ok with ContractEsmd model or Err with error message
        """
        return asyncio.run(
            self.extract_metadata(
                text=text,
                project_id=project_id,
                reference_doc_id=reference_doc_id,
                file_name=file_name
            )
        )

    def __call__(
        self,
        text: str,
        project_id: str,
        reference_doc_id: str,
        file_name: Optional[str] = None
    ) -> Result[ContractEsmd, str]:
        """
        Make service callable.

        Args:
            text: Full contract text
            project_id: Project identifier
            reference_doc_id: Reference document identifier
            file_name: Optional filename

        Returns:
            Result[ContractEsmd, str]: Ok with ContractEsmd model or Err with error message
        """
        return self.execute(
            text=text,
            project_id=project_id,
            reference_doc_id=reference_doc_id,
            file_name=file_name
        )



class MetadataExtractionServiceFactory:
    """Factory for creating MetadataExtractionService with default configurations."""

    @staticmethod
    def create_default() -> MetadataExtractionService:
        """
        Auto-initialize the client with OpenAI and create the service class.

        Uses configuration from environment variables:
        - OPENAI_API_KEY: OpenAI API key
        - OPENAI_MODEL: Model to use (e.g., gpt-4o-mini, gpt-4.1-mini)

        Returns:
            MetadataExtractionService: Configured service instance

        Example:
            >>> service = MetadataExtractionServiceFactory.create_default()
            >>> result = await service.extract_metadata(
            ...     text=contract_text,
            ...     project_id="proj_001",
            ...     reference_doc_id="doc_001"
            ... )
        """
        # Create OpenAI client using factory (avoids LiteLLM HTTP calls)
        client = create_default_chat_client()

        # Create and return service with default encoding
        return MetadataExtractionService(
            client=client,
            encoding_name="o200k_base"
        )


if __name__ == "__main__":
    # Example usage

    async def test_service():
        """Test metadata extraction service."""
        # Setup
        openai_settings = settings_factory.create_openai_settings()
        client = LiteLLMChatClient(
            model="gpt-4o-mini",
            api_key=openai_settings.api_key
        )

        service = MetadataExtractionService(client=client)

        # Sample contract
        contract_text = """
SERVICE AGREEMENT

This Service Agreement is entered into on January 15, 2024
between Tech Solutions Inc. (Provider) and Global Corp (Client).

1. SCOPE OF SERVICES
The Provider shall deliver software development services.

2. FINANCIAL TERMS
Total Contract Value: $500,000
Payment Schedule: Monthly installments of $41,666.67

3. TERMINATION
Either party may terminate with 30 days written notice.
"""

        # Extract metadata
        result = await service.extract_metadata(
            text=contract_text,
            project_id="test_project",
            reference_doc_id="test_contract_001",
            file_name="service_agreement.pdf"
        )

        if result.is_ok():
            contract = result.ok()
            print(f"✅ Success! Extracted {len(contract.model_dump(exclude_none=True))} fields")
            print(f"Contract type: {contract.contract_type}")
            print(f"Total value: {contract.total_contract_value}")
        else:
            print(f"❌ Error: {result.err()}")

    asyncio.run(test_service())
