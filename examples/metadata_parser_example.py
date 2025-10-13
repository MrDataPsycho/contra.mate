"""
Example usage of MetadataParserAgent for extracting contract metadata.

This example shows how to:
1. Initialize the agent with any BaseChatClient implementation
2. Extract structured metadata from contract text (returns dict)
3. Create ContractEsmd model with project_id and reference_doc_id
4. Handle batching for large documents automatically
5. Handle exceptions from the agent
"""

import asyncio
from contramate.llm.litellm_client import LiteLLMChatClient
from contramate.core.agents import MetadataParserAgent
from contramate.dbs.models.contract import ContractEsmd
from contramate.utils.settings.factory import settings_factory


async def main():
    """Main example function."""

    # 1. Setup: Initialize settings and client
    openai_settings = settings_factory.create_openai_settings()

    # Create any client that implements BaseChatClient
    # Here we use LiteLLM with GPT-4o-mini for cost efficiency and higher rate limits
    client = LiteLLMChatClient(
        model="gpt-4.1-mini",
        api_key=openai_settings.api_key
    )

    # 2. Initialize MetadataParserAgent
    print("📋 Initializing MetadataParserAgent...")
    parser = MetadataParserAgent(client=client)

    # 3. Sample contract text
    contract_text = """
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into on January 15, 2024 ("Effective Date")
between Tech Solutions Inc. ("Provider") and Global Corp ("Client").

1. SCOPE OF SERVICES
The Provider shall deliver software development services including:
- Custom web application development
- Mobile app development for iOS and Android
- API integration and maintenance

2. DELIVERABLES AND MILESTONES
Phase 1 (Months 1-3): Requirements gathering and design
Phase 2 (Months 4-8): Development and testing
Phase 3 (Months 9-12): Deployment and training

3. FINANCIAL TERMS
Total Contract Value: $500,000
Payment Schedule: Monthly installments of $41,666.67
Annualized Cost: $500,000 (12-month contract)
Monthly Cost: $41,666.67

Rate Card:
- Senior Developer: $200/hour
- Junior Developer: $120/hour
- Project Manager: $180/hour

4. TERMINATION
Either party may terminate this agreement with 30 days written notice.
Termination for convenience is allowed with payment for work completed.

5. CONFIDENTIALITY
Both parties agree to maintain confidentiality of proprietary information
for a period of 3 years following contract termination.

6. AMENDMENTS
This is the original contract (Amendment Number: N/A).
Any amendments require written consent from both parties.
Contract review periods: Quarterly

7. LOCATION
Services will be provided remotely with on-site visits as needed.
Primary service location: Client's headquarters in San Francisco, CA

8. SUBCONTRACTORS
Provider may engage the following approved subcontractors:
- DataSystems LLC for database optimization
- UX Design Studio for interface design

Signatures:
John Smith, CEO - Tech Solutions Inc. - January 15, 2024
Jane Doe, CTO - Global Corp - January 15, 2024
"""

    # 4. Extract metadata using the agent (returns dict)
    print("\n🔄 Extracting contract metadata...")
    print(f"   Contract length: {len(contract_text)} characters")

    try:
        # Agent uses ContractMetadata schema for structured output and validation
        # Returns validated dict or raises ValidationError/Exception
        metadata_dict = await parser.extract_metadata(text=contract_text)

        # Create ContractEsmd model with project_id and reference_doc_id
        # These IDs are added at service level, not extracted by agent
        metadata_dict["project_id"] = "demo_project"
        metadata_dict["reference_doc_id"] = "contract_001"
        metadata = ContractEsmd(**metadata_dict)

        print(f"✅ Successfully extracted metadata!")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    # 5. Display extracted metadata
    print("\n📊 Extracted Contract Metadata:")
    print("=" * 80)

    # Core info
    if metadata.contract_type:
        print(f"\n📄 Contract Type: {metadata.contract_type}")
    if metadata.doc_type:
        print(f"📋 Document Type: {metadata.doc_type}")
    if metadata.doc_description:
        print(f"📝 Description: {metadata.doc_description}")

    # Financial info
    print("\n💰 Financial Terms:")
    if metadata.total_contract_value:
        print(f"   Total Value: {metadata.total_contract_value}")
    if metadata.monthly_cost:
        print(f"   Monthly Cost: {metadata.monthly_cost}")
    if metadata.annualized_cost:
        print(f"   Annualized: {metadata.annualized_cost}")
    if metadata.payment_schedule:
        print(f"   Schedule: {metadata.payment_schedule}")

    # Deliverables
    if metadata.deliverables_activities:
        print(f"\n📦 Deliverables: {metadata.deliverables_activities}")
    if metadata.milestones:
        print(f"🎯 Milestones: {metadata.milestones}")

    # Legal terms
    print("\n⚖️ Legal Terms:")
    if metadata.termination_clauses:
        print(f"   Termination: {metadata.termination_clauses}")
    if metadata.confidentiality_clauses:
        print(f"   Confidentiality: {metadata.confidentiality_clauses}")

    # Parties
    if metadata.subcontractors:
        print(f"\n👥 Subcontractors: {metadata.subcontractors}")
    if metadata.signatures:
        print(f"✍️  Signatures: {metadata.signatures}")

    # Location
    if metadata.service_location:
        print(f"\n📍 Service Location: {metadata.service_location}")

    # 7. Export as JSON
    print("\n💾 Metadata as JSON:")
    print(metadata.model_dump_json(indent=2, exclude_none=True))

    # 8. Demo: Large document batching
    print("\n" + "=" * 80)
    print("📚 BATCHING DEMO: Simulating large document")
    print("=" * 80)

    # Create a large document by repeating the contract
    large_contract = contract_text * 100  # Much larger document
    print(f"\nLarge document size: {len(large_contract)} characters")

    # The agent will automatically batch this
    try:
        large_metadata_dict = await parser.extract_metadata(text=large_contract)

        # Create model with IDs (added at service level)
        large_metadata_dict["project_id"] = "demo_project"
        large_metadata_dict["reference_doc_id"] = "large_contract_001"
        large_metadata = ContractEsmd(**large_metadata_dict)

        print("✅ Successfully processed large document with automatic batching!")
        print(f"   Extracted fields: {sum(1 for v in large_metadata.model_dump(exclude_none=True).values() if v)}")
    except Exception as e:
        print(f"❌ Large document processing failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
