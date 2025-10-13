"""
Example usage of MetadataExtractionService.

This example demonstrates the high-level service interface for extracting
contract metadata and creating ContractEsmd models ready for database insertion.
"""

import asyncio
from contramate.llm.litellm_client import LiteLLMChatClient
from contramate.services import MetadataExtractionService
from contramate.utils.settings.factory import settings_factory


async def main():
    """Main example function."""

    # 1. Setup: Initialize settings and client
    openai_settings = settings_factory.create_openai_settings()

    # Create any client that implements BaseChatClient
    client = LiteLLMChatClient(
        model="gpt-4o-mini",
        api_key=openai_settings.api_key
    )

    # 2. Initialize MetadataExtractionService
    print("📋 Initializing MetadataExtractionService...")
    service = MetadataExtractionService(client=client)

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

    # 4. Extract metadata using the service
    print("\n🔄 Extracting contract metadata...")
    print(f"   Contract length: {len(contract_text)} characters")

    result = await service.extract_mectadata(
        text=contract_text,
        project_id="demo_project",
        reference_doc_id="contract_001",
        file_name="service_agreement.pdf"
    )

    # 5. Handle result
    if result.is_ok():
        contract = result.ok()
        print("✅ Successfully extracted metadata!")
        print(f"   Extracted {len(contract.model_dump(exclude_none=True))} fields")

        # Display key metadata
        print("\n📊 Extracted Contract Metadata:")
        print("=" * 80)

        if contract.contract_type:
            print(f"\n📄 Contract Type: {contract.contract_type}")
        if contract.doc_type:
            print(f"📋 Document Type: {contract.doc_type}")
        if contract.title:
            print(f"📝 Title: {contract.title}")

        # Financial info
        print("\n💰 Financial Terms:")
        if contract.total_contract_value:
            print(f"   Total Value: {contract.total_contract_value}")
        if contract.monthly_cost:
            print(f"   Monthly Cost: {contract.monthly_cost}")
        if contract.annualized_cost:
            print(f"   Annualized: {contract.annualized_cost}")

        # Legal terms
        print("\n⚖️ Legal Terms:")
        if contract.termination_clauses:
            print(f"   Termination: {contract.termination_clauses[:100]}...")
        if contract.confidentiality_clauses:
            print(f"   Confidentiality: {contract.confidentiality_clauses[:100]}...")

        # Service details
        if contract.service_location:
            print(f"\n📍 Service Location: {contract.service_location}")
        if contract.subcontractors:
            print(f"👥 Subcontractors: {contract.subcontractors}")

        # IDs and timestamps (added by service)
        print("\n🔑 Service-Level Fields:")
        print(f"   Project ID: {contract.project_id}")
        print(f"   Reference Doc ID: {contract.reference_doc_id}")
        print(f"   File Name: {contract.file_name}")
        print(f"   Processed At: {contract.processed_at}")

        # Ready for database insertion
        print("\n💾 Ready for Database Insertion:")
        print(f"   Model Type: {type(contract).__name__}")
        print(f"   Table: {contract.__tablename__}")

    else:
        error = result.err()
        print(f"❌ Extraction failed: {error}")
        return

    # 6. Demo: Multiple documents processing
    print("\n" + "=" * 80)
    print("📚 BATCH PROCESSING DEMO: Multiple documents")
    print("=" * 80)

    documents = [
        {
            "text": contract_text,
            "project_id": "demo_project",
            "reference_doc_id": "contract_001",
            "file_name": "service_agreement_1.pdf"
        },
        {
            "text": contract_text,
            "project_id": "demo_project",
            "reference_doc_id": "contract_002",
            "file_name": "service_agreement_2.pdf"
        },
    ]

    print(f"\nProcessing {len(documents)} documents...")

    # Process multiple documents concurrently
    tasks = [
        service.extract_metadata(
            text=doc["text"],
            project_id=doc["project_id"],
            reference_doc_id=doc["reference_doc_id"],
            file_name=doc["file_name"]
        )
        for doc in documents
    ]

    results = await asyncio.gather(*tasks)

    # Count successes and failures
    successes = sum(1 for r in results if r.is_ok())
    failures = sum(1 for r in results if r.is_err())

    print(f"✅ Successfully processed: {successes}/{len(documents)}")
    if failures > 0:
        print(f"❌ Failed: {failures}/{len(documents)}")

    # Display results
    for i, result in enumerate(results, 1):
        if result.is_ok():
            contract = result.ok()
            print(f"   Document {i}: {contract.reference_doc_id} - "
                  f"{len(contract.model_dump(exclude_none=True))} fields")
        else:
            print(f"   Document {i}: FAILED - {result.err()}")


if __name__ == "__main__":
    asyncio.run(main())
