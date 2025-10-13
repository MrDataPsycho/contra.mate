"""
Example usage of the simplified EnrichmentService.

This example shows how to:
1. Create a ChunkedDocument from markdown
2. Enrich all chunks using the EnrichmentService
3. Save the enriched document
"""

from pathlib import Path

from contramate.models import DocumentInfo
from contramate.services.markdown_chunking_service import (
    MarkdownChunkingService,
    EncodingName
)
from contramate.services.enrich_content_service import EnrichmentService
from contramate.llm.litellm_client import LiteLLMChatClient
from contramate.utils.settings.factory import settings_factory


def main():
    """Main example function."""

    # 1. Setup: Initialize settings and client
    openai_settings = settings_factory.create_openai_settings()

    # Create LiteLLM client with GPT-4o mini
    client = LiteLLMChatClient(
        model="gpt-4o-mini",
        api_key=openai_settings.api_key
    )

    # 2. Sample markdown content
    sample_markdown = """# Employment Contract

## 1. Introduction
This Employment Agreement ("Agreement") is entered into between Company XYZ and Employee John Doe.

## 2. Position and Duties
The Employee shall serve as Senior Software Engineer and shall perform duties as assigned.

### 2.1 Responsibilities
- Develop and maintain software applications
- Participate in code reviews
- Mentor junior developers

## 3. Compensation
The Employee shall receive an annual salary of $120,000, payable bi-weekly.

### 3.1 Benefits
- Health insurance coverage
- 401(k) matching up to 5%
- 20 days PTO annually

## 4. Term
This agreement shall commence on January 1, 2024 and continue until terminated.
"""

    # 3. Create document info
    doc_info = DocumentInfo(
        project_id="proj_001",
        reference_doc_id="contract_001",
        contract_type="employment"
    )

    # 4. Chunk the document
    print("📄 Chunking markdown document...")
    chunking_service = MarkdownChunkingService(
        markdown_content=sample_markdown,
        doc_info=doc_info,
        encoding_name=EncodingName.O200K_BASE,
        token_limit=500,  # Small limit for demo
        min_chunk_size=50
    )

    result = chunking_service.execute()

    if result.is_err():
        print(f"❌ Chunking failed: {result.unwrap_err()}")
        return

    chunked_doc = result.unwrap()
    print(f"✅ Created {chunked_doc.total_chunks} chunks")

    # 5. Enrich the document
    print("\n🔄 Enriching chunks...")
    enrichment_service = EnrichmentService(client=client)

    # Option 1: Using execute() for Result type
    enrichment_result = enrichment_service.execute(chunked_doc)

    # Option 2: Using callable pattern (same as execute)
    # enrichment_result = enrichment_service(chunked_doc)

    if enrichment_result.is_err():
        print(f"❌ Enrichment failed: {enrichment_result.unwrap_err()}")
        return

    enriched_doc = enrichment_result.unwrap()
    print(f"✅ Enriched {len(enriched_doc.chunks)} chunks")

    # 6. Display results
    print("\n📊 Enrichment Results:")
    print("=" * 80)

    for i, chunk in enumerate(enriched_doc.chunks[:2]):  # Show first 2 chunks
        print(f"\n[Chunk {i}]")
        print(f"Original ({len(chunk.content)} chars):")
        print(f"  {chunk.content[:100]}...")
        print(f"\nEnriched ({len(chunk.enriched_content)} chars):")
        print(f"  {chunk.enriched_content[:150]}...")
        print("-" * 80)

    # 7. Save enriched document
    output_path = Path("data/enriched/contract_001_enriched.json")
    enriched_doc.save_json(output_path)
    print(f"\n💾 Saved enriched document to: {output_path}")

    # 8. Load it back (optional)
    loaded_doc = enriched_doc.load_json(output_path)
    print(f"✅ Successfully loaded enriched document with {loaded_doc.total_chunks} chunks")


if __name__ == "__main__":
    main()
