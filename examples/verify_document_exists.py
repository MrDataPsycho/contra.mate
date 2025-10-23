"""
Script to verify if specific documents exist in the vector store.
"""
import asyncio
from pathlib import Path
from contramate.services.opensearch_vector_search_service import OpenSearchVectorSearchServiceFactory

async def verify_documents():
    """Verify if documents exist in vector store."""

    # Documents to check
    documents_to_check = [
        {
            "name": "Document 1",
            "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
            "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949",
        },
        {
            "name": "Document 2",
            "project_id": "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
            "reference_doc_id": "aa1a0c65-8016-5d11-bbde-22055140660b",
        },
        {
            "name": "Document 3",
            "project_id": "0096b72f-1c0d-4724-924f-011f87d3591a",
            "reference_doc_id": "16b6078b-248c-5ed9-83ef-20ee0af49396",
        },
    ]

    # Create search service
    env_file = Path(".envs/local.env")
    search_service = OpenSearchVectorSearchServiceFactory.from_env_file(env_path=env_file)

    print("=" * 80)
    print("Verifying Document Existence in Vector Store")
    print("=" * 80)

    for doc in documents_to_check:
        print(f"\n{doc['name']}:")
        print(f"  Project ID: {doc['project_id']}")
        print(f"  Reference Doc ID: {doc['reference_doc_id']}")

        # Try to retrieve the document
        result = search_service.search_by_document(
            project_id=doc['project_id'],
            reference_doc_id=doc['reference_doc_id'],
            size=1  # Just get 1 chunk to verify existence
        )

        if result.is_ok():
            response = result.unwrap()
            if response.total_results > 0:
                print(f"  ✅ EXISTS - {response.total_results} chunks found")
                print(f"  Document Title: {response.results[0].document_title}")
                print(f"  Display Name: {response.results[0].display_name}")
            else:
                print(f"  ❌ NOT FOUND - 0 chunks")
        else:
            error = result.unwrap_err()
            print(f"  ❌ ERROR: {error}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(verify_documents())
