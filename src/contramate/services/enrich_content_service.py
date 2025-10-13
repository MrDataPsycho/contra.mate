"""
Simplified Contextual Enrichment Service for RAG Applications.

Takes ChunkedDocument and enriches each chunk with contextual information
from the full document.
"""

import asyncio
from loguru import logger
from neopipe import Result, Ok, Err

from contramate.models import Chunk, ChunkedDocument, EnrichedChunk, EnrichedDocument
from contramate.llm.base import BaseChatClient


class EnrichmentService:
    """
    Simplified enrichment service that processes chunks asynchronously.

    Takes a ChunkedDocument and enriches all chunks in parallel using async.
    Uses LiteLLM with GPT-4o mini for enrichment.
    """

    SYSTEM_PROMPT = """You are a professional content analyzer specializing in contextual enrichment for RAG systems.

Your task: Create an enriched summary of the given chunk that preserves all critical details while making it more retrievable and understandable for semantic search and question answering.

CRITICAL PRESERVATION RULES - These details MUST be retained exactly as they appear:
1. ALL NUMBERS: dates, deadlines, timeframes (e.g., "30 days", "within 60 days"), amounts, percentages, quantities, counts
2. ALL MONETARY VALUES: prices, fees, costs, payment amounts, currency values, financial terms
3. ALL PARTIES/ENTITIES: company names, person names, roles, departments, organizations
4. ALL CONDITIONS: "within X days", "minimum of Y", "up to Z", "not less than", "at least", thresholds
5. ALL LEGAL/CONTRACTUAL TERMS: specific obligations, warranties, definitions, rights, limitations, requirements
6. ALL KEY DATES: effective dates, expiration dates, notice periods, term lengths

Your enriched summary should:
- Start with document context: type of document, parties involved, and what section/topic this covers
- Preserve ALL critical details listed above in a well-structured format
- Add contextual information about relationships between parties, terms, and conditions
- Make implicit information explicit (e.g., "the Licensor must notify the Licensee within 30 days" instead of just "notify within 30 days")
- Highlight key obligations, rights, and conditions
- Be comprehensive and retrieval-friendly while more concise than the original

Example structure:
This chunk is from a [Document Type] between [Party A] and [Party B], covering [Section/Topic]. Key entities: [list]. This section details [main purpose] including [critical details with all numbers/conditions preserved].

[Well-structured summary with all critical details preserved and contextualized]"""

    def __init__(self, client: BaseChatClient):
        """
        Initialize enrichment service.

        Args:
            client: Chat client implementing BaseChatClient interface
        """
        self.client = client
        self.logger = logger

    async def enrich_chunk(self, doc_content: str, chunk: Chunk) -> Result[EnrichedChunk, str]:
        """
        Enrich a single chunk asynchronously.

        Args:
            doc_content: Full document content for context
            chunk: Chunk object to enrich

        Returns:
            Result[EnrichedChunk, str]: Ok with enriched chunk or Err with error message
        """
        try:
            # Create enrichment prompt
            user_prompt = f"""<document>
{doc_content}
</document>

<chunk_to_enrich>
{chunk.content}
</chunk_to_enrich>

TASK: Create an enriched summary of this chunk that preserves ALL critical details (numbers, dates, monetary values, conditions, parties, legal terms) while adding contextual information. Make it comprehensive and retrieval-friendly. CRITICAL: Do not omit any specific numbers, conditions, or key terms from the original chunk."""

            # Call LLM asynchronously
            response = await self.client.async_chat_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            # Extract enriched text (ChatResponse has content field directly)
            enriched_text = response.content.strip()

            # Create and return enriched chunk
            enriched_chunk = EnrichedChunk.from_chunk(chunk, enriched_text)

            self.logger.debug(
                f"Enriched chunk {chunk.chunk_index}: "
                f"{len(chunk.content)} -> {len(enriched_text)} chars"
            )

            return Ok(enriched_chunk)

        except Exception as e:
            error_msg = f"Error enriching chunk {chunk.chunk_index}: {str(e)}"
            self.logger.error(error_msg)
            return Err(error_msg)

    async def enrich_document(self, chunked_doc: ChunkedDocument) -> Result[EnrichedDocument, str]:
        """
        Enrich all chunks in a document asynchronously.

        Processes all chunks in parallel using asyncio.gather for maximum efficiency.

        Args:
            chunked_doc: ChunkedDocument with chunks to enrich

        Returns:
            Result[EnrichedDocument, str]: Ok with enriched document or Err with error message
        """
        try:
            if not chunked_doc.chunks:
                logger.warning("No chunks to enrich in document")
                return Ok(EnrichedDocument.from_chunked_document(chunked_doc, []))

            # Reconstruct full document content (approximate)
            # Note: This is a simplified approach. In production, you might want
            # to pass the original markdown content separately
            doc_content = "\n\n".join([chunk.content for chunk in chunked_doc.chunks])

            logger.info(f"Enriching {len(chunked_doc.chunks)} chunks for document {chunked_doc.reference_doc_id}")

            # Enrich all chunks in parallel
            tasks = [
                self.enrich_chunk(doc_content, chunk)
                for chunk in chunked_doc.chunks
            ]

            results = await asyncio.gather(*tasks)

            # Collect successful enrichments and track failures
            enriched_chunks = []
            failed_chunks = []

            for result in results:
                if result.is_ok():
                    enriched_chunks.append(result.unwrap())
                else:
                    failed_chunks.append(result.unwrap_err())

            # If any chunks failed, log warnings but continue with successful ones
            if failed_chunks:
                logger.warning(f"{len(failed_chunks)} chunks failed to enrich: {failed_chunks[:3]}")

            # Create enriched document
            enriched_doc = EnrichedDocument.from_chunked_document(
                chunked_doc,
                enriched_chunks
            )

            logger.info(
                f"Successfully enriched {len(enriched_chunks)} chunks for "
                f"document {chunked_doc.reference_doc_id}"
            )

            return Ok(enriched_doc)

        except Exception as e:
            error_msg = f"Error enriching document {chunked_doc.reference_doc_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def execute(self, chunked_doc: ChunkedDocument) -> Result[EnrichedDocument, str]:
        """
        Execute the enrichment service and return Result type.

        Args:
            chunked_doc: ChunkedDocument with chunks to enrich

        Returns:
            Result[EnrichedDocument, str]: Ok with enriched document or Err with error message
        """
        try:
            enriched_doc_result = asyncio.run(self.enrich_document(chunked_doc))
            return enriched_doc_result

        except Exception as e:
            error_msg = f"Error executing enrichment service: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Err(error_msg)

    def __call__(self, chunked_doc: ChunkedDocument) -> Result[EnrichedDocument, str]:
        """
        Make the service callable like a function.

        Args:
            chunked_doc: ChunkedDocument with chunks to enrich

        Returns:
            Result[EnrichedDocument, str]: Ok with enriched document or Err with error message
        """
        return self.execute(chunked_doc)