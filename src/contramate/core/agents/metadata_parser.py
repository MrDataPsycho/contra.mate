"""
Metadata Parser Agent for extracting structured contract metadata.

This agent uses LLM to extract structured metadata from contract text,
with support for large documents through batching.
"""

import asyncio
import json
import tiktoken
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from loguru import logger
from contramate.llm.base import BaseChatClient


class ContractMetadata(BaseModel):
    """
    Pydantic model for contract metadata extraction.

    Matches ContractEsmd SQLModel schema for direct database insertion.
    All fields are optional as not all contracts contain all information.
    Note: project_id, reference_doc_id, and processed_at are added at service level.
    """

    title: Optional[str] = Field(
        None, description="Title of the Agreement extracted from the contract"
    )
    contract_type: Optional[str] = Field(
        None, description="Classifies contract type or marks as 'Others'."
    )
    doc_type: Optional[str] = Field(
        None, description="Identifies Contract as Original, Amendment, or Unknown."
    )
    doc_description: Optional[str] = Field(
        None, description="Brief summary the document's intent."
    )

    # Scope and deliverables
    scope: Optional[str] = Field(
        None, description="Description of services or work covered."
    )
    signatures: Optional[str] = Field(
        None, description="Extract of signatories, roles, and timestamps."
    )
    deliverables_activities: Optional[str] = Field(
        None,
        description="Deliverables and activities - List of agreed outputs or tasks.",
    )
    milestones: Optional[str] = Field(None, description="Key project checkpoints.")

    # Financial terms
    reward_recourse_terms: Optional[str] = Field(
        None, description="Capture of reward and penalty terms."
    )
    inflation_terms: Optional[str] = Field(
        None, description="Description of inflation handling."
    )
    payment_schedule: Optional[str] = Field(
        None, description="Outline of payment timing and frequency."
    )
    cost_drivers: Optional[str] = Field(
        None, description="Identification of cost-influencing factors"
    )
    total_contract_value: Optional[str] = Field(
        None, description="Extract of total financial commitment."
    )
    total_pass_through: Optional[str] = Field(
        None, description="Capture of pass-through costs."
    )
    total_direct_fees: Optional[str] = Field(
        None, description="Extract of direct project fees."
    )
    annualized_cost: Optional[str] = Field(
        None, description="Provision of yearly cost estimate."
    )
    subcontractors: Optional[str] = Field(
        None, description="List of subcontractors mentioned"
    )
    discounts: Optional[str] = Field(
        None, description="Identification of cost reductions."
    )
    penalty: Optional[str] = Field(None, description="Extract of financial penalties.")
    service_location: Optional[str] = Field(
        None, description="Identification of service delivery location."
    )

    # Legal terms
    termination_clauses: Optional[str] = Field(
        None, description="Capture of termination conditions."
    )
    confidentiality_clauses: Optional[str] = Field(
        None, description="Extract of confidentiality provisions."
    )
    termination_notice: Optional[str] = Field(
        None, description="Description of termination notice terms."
    )

    # Pricing structures (Lists stored as JSON in DB)
    rate_card: Optional[List] = Field(
        None, description="Reference or extract of pricing guide."
    )
    rebate_structure: Optional[str] = Field(
        None, description="Capture of rebate conditions."
    )
    discount_structure: Optional[List] = Field(
        None, description="Detail discount types and terms."
    )
    pricing_structure: Optional[str] = Field(
        None, description="Explanation of pricing calculation method."
    )

    # Amendment and review
    review_periods: Optional[str] = Field(
        None, description="Identification of contract review intervals."
    )
    amendment_procedures: Optional[str] = Field(
        None, description="Description of change process."
    )
    reason_for_amendment: Optional[str] = Field(
        None, description="Classifies reason for amendment."
    )
    changes_made: Optional[str] = Field(None, description="List of specific changes.")
    impact_on_original: Optional[str] = Field(
        None, description="Description of effect on original terms."
    )
    relevant_sop: Optional[str] = Field(
        None, description="Identifies selected SOP or mark as N/A."
    )

    # Additional costs
    monthly_cost: Optional[str] = Field(
        None, description="Extract of recurring monthly expense."
    )
    other_charges: Optional[str] = Field(
        None, description="Capture of additional costs."
    )
    amendment_num: Optional[str] = Field(
        None, description="Extract of amendment number or marks as N/A if not relevant."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "additionalProperties": False,
        }
    )


SYSTEM_PROMPT = """You are an expert contract metadata extraction specialist.

Your task: Extract structured metadata from contract documents with high accuracy.

Guidelines:
- Extract ALL relevant information from the provided contract text
- Use exact text from the contract when possible (e.g., dates, amounts, names)
- If information is not present, omit the field - do NOT invent information
- Pay special attention to financial terms, dates, legal clauses, and amendments
- Be precise with amounts, dates, and named entities
- Classify contract type and document type (Original/Amendment/Unknown)

IMPORTANT - Data Types:
- rate_card: Extract as JSON array of objects (e.g., [{"Senior Developer": "$200/hour"}])
- discount_structure: Extract as JSON array of objects
- ALL OTHER FIELDS: Extract as strings (even if multiple items, use comma-separated or newline-separated strings)

Output format: Return a valid JSON object with these fields (all optional):

Document Identification:
- file_name, title, contract_type, doc_type, doc_description

Scope and Deliverables:
- scope, signatures, deliverables_activities, milestones

Financial Terms:
- reward_recourse_terms, inflation_terms, payment_schedule, cost_drivers
- total_contract_value, total_pass_through, total_direct_fees, annualized_cost
- subcontractors, discounts, penalty, service_location

Legal Terms:
- termination_clauses, confidentiality_clauses, termination_notice

Pricing Structures:
- rate_card (JSON array of objects)
- rebate_structure (string)
- discount_structure (JSON array of objects)
- pricing_structure (string)

Amendment and Review:
- review_periods, amendment_procedures, reason_for_amendment, changes_made
- impact_on_original, relevant_sop

Additional Costs:
- monthly_cost, other_charges, amendment_num

Note: Only rate_card and discount_structure should be arrays. All other fields are strings."""

BATCH_SYSTEM_PROMPT = """You are an expert contract metadata extraction specialist working on a BATCH of a larger contract.

IMPORTANT CONTEXT:
- You are processing BATCH {batch_num} of {total_batches} from a larger contract
- Previous batches have already extracted some metadata (provided below)
- Your task: Extract NEW information from this batch and UPDATE existing fields if you find more accurate/complete information

Guidelines:
- PRESERVE all information from previous batches unless you find contradictory or more complete information
- ADD new information found in this batch
- UPDATE existing fields ONLY if this batch contains more accurate or complete information
- Do NOT remove information from previous batches
- If a field was already filled and this batch has no new info, keep the previous value
- Focus on extracting information specific to THIS batch while maintaining consistency

Previous metadata from earlier batches:
{previous_metadata}

Output format: Return a valid JSON object with MERGED metadata (previous + current batch)."""


class MetadataParserAgent:
    # Token limit for batching (1 million tokens)
    MAX_TOKENS_PER_BATCH = 1_000_000

    """
    Agent for parsing structured contract metadata from text.

    Features:
    - Extracts metadata using ContractMetadata Pydantic schema for validation
    - Handles large documents with automatic batching (>1M tokens)
    - Incremental parsing: updates previous results in subsequent batches
    - Returns validated dict or raises exceptions for errors
    - Low-level API: caller responsible for adding project_id/doc_id
    """

    def __init__(
        self,
        client: BaseChatClient,
        system_prompt: str | None = None,
        batch_system_prompt: str | None = None,
        encoding_name: str = "o200k_base",
    ):
        """
        Initialize metadata parser agent.

        Args:
            client: Chat client implementing BaseChatClient interface
            system_prompt: System prompt for extraction (uses default if None)
            batch_system_prompt: Batch system prompt for large documents (uses default if None)
            encoding_name: Tiktoken encoding name for token counting
        """
        self.client = client
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.batch_system_prompt = batch_system_prompt or BATCH_SYSTEM_PROMPT
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))

    def split_into_batches(self, text: str) -> list[str]:
        """
        Split text into batches if it exceeds token limit.

        Args:
            text: Full contract text

        Returns:
            List of text batches
        """
        total_tokens = self.count_tokens(text)

        if total_tokens <= self.MAX_TOKENS_PER_BATCH:
            logger.info(f"Document has {total_tokens} tokens - no batching needed")
            return [text]

        # Calculate number of batches needed
        num_batches = (total_tokens // self.MAX_TOKENS_PER_BATCH) + 1
        logger.info(
            f"Document has {total_tokens} tokens - splitting into {num_batches} batches"
        )

        # Split text into approximately equal batches
        # Simple approach: split by characters (rough approximation)
        # For production, consider splitting by paragraphs or sections
        chars_per_batch = len(text) // num_batches
        batches = []

        for i in range(num_batches):
            start = i * chars_per_batch
            end = (i + 1) * chars_per_batch if i < num_batches - 1 else len(text)
            batch_text = text[start:end]
            batches.append(batch_text)

            batch_tokens = self.count_tokens(batch_text)
            logger.debug(f"Batch {i + 1}: {batch_tokens} tokens")

        return batches

    async def extract_metadata_single(
        self,
        text: str,
        previous_metadata: Optional[dict] = None,
        batch_num: Optional[int] = None,
        total_batches: Optional[int] = None,
    ) -> dict:
        """
        Extract metadata from a single text chunk using ContractMetadata schema.

        Args:
            text: Contract text to parse
            previous_metadata: Metadata dict from previous batches (for incremental parsing)
            batch_num: Current batch number (for batched processing)
            total_batches: Total number of batches (for batched processing)

        Returns:
            dict: Extracted and validated metadata as dictionary (validated against ContractMetadata schema)

        Raises:
            ValidationError: If LLM response doesn't match ContractMetadata schema
            Exception: If extraction fails
        """
        # Choose system prompt based on whether this is a batch
        if batch_num is not None and total_batches is not None:
            # Format previous metadata as JSON for context
            prev_json = (
                "No previous metadata"
                if previous_metadata is None
                else json.dumps(previous_metadata, indent=2)
            )

            system_prompt = self.batch_system_prompt.format(
                batch_num=batch_num,
                total_batches=total_batches,
                previous_metadata=prev_json,
            )
        else:
            system_prompt = self.system_prompt

        user_prompt = f"""<contract>\n{text}\n</contract>
            Extract all contract metadata from the above text and return as JSON.
        """

        # Call LLM with structured output using ContractMetadata schema
        # Pass schema as structured format for better LLM compatibility
        # Note: strict=False allows optional fields (since not all contracts have all metadata)
        response = await self.client.async_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for factual extraction
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ContractMetadata",
                    "schema": ContractMetadata.model_json_schema(),
                    "strict": False,
                },
            },
        )

        # Parse and validate response against ContractMetadata schema
        try:
            metadata_dict = json.loads(response.content)
        except json.JSONDecodeError as e:
            # Log the error with details for debugging
            logger.error(f"JSON parsing failed: {e}")
            logger.error(f"Response length: {len(response.content)} chars")
            logger.error(f"First 300 chars: {response.content[:300]}")
            logger.error(f"Last 300 chars: {response.content[-300:]}")
            logger.error(f"Error at position {e.pos}: {response.content[max(0, e.pos-50):min(len(response.content), e.pos+50)]}")
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")

        # Validate against schema (this will raise ValidationError if invalid)
        validated_metadata = ContractMetadata(**metadata_dict)

        # Return as dict
        metadata_dict = validated_metadata.model_dump(exclude_none=True)

        logger.info(
            f"Successfully extracted metadata"
            + (f" (batch {batch_num}/{total_batches})" if batch_num else "")
        )

        return metadata_dict

    async def extract_metadata(self, text: str) -> dict:
        """
        Extract metadata from contract text with automatic batching.

        Uses ContractMetadata Pydantic schema for structured output validation.

        Args:
            text: Full contract text

        Returns:
            dict: Extracted and validated metadata as dictionary

        Raises:
            ValidationError: If LLM response doesn't match ContractMetadata schema
            Exception: If extraction fails
        """
        # Split into batches if needed
        batches = self.split_into_batches(text)
        total_batches = len(batches)

        # Process batches sequentially, updating metadata incrementally
        current_metadata: Optional[dict] = None

        for batch_num, batch_text in enumerate(batches, start=1):
            logger.info(f"Processing batch {batch_num}/{total_batches}")

            current_metadata = await self.extract_metadata_single(
                text=batch_text,
                previous_metadata=current_metadata,
                batch_num=batch_num if total_batches > 1 else None,
                total_batches=total_batches if total_batches > 1 else None,
            )

        logger.info(
            f"Successfully extracted metadata from {total_batches} batch(es)"
        )

        return current_metadata

    def execute(self, text: str) -> dict:
        """
        Execute metadata extraction (synchronous wrapper).

        Args:
            text: Full contract text

        Returns:
            dict: Extracted and validated metadata as dictionary

        Raises:
            ValidationError: If LLM response doesn't match ContractMetadata schema
            Exception: If extraction fails
        """
        return asyncio.run(self.extract_metadata(text))

    def __call__(self, text: str) -> dict:
        """
        Make agent callable.

        Args:
            text: Full contract text

        Returns:
            dict: Extracted and validated metadata as dictionary

        Raises:
            ValidationError: If LLM response doesn't match ContractMetadata schema
            Exception: If extraction fails
        """
        return self.execute(text)
