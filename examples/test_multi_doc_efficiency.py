"""
Test script to verify the efficiency improvement of hybrid_search_multi_document.

This script compares:
1. OLD WAY: Calling hybrid_search N times (creates N embeddings)
2. NEW WAY: Calling hybrid_search_multi_document once (creates 1 embedding)
"""
import asyncio
import time
from pathlib import Path
from contramate.services.opensearch_vector_search_service import OpenSearchVectorSearchServiceFactory


async def test_old_way(search_service, query: str, documents: list) -> float:
    """Test the old approach: N separate hybrid_search calls (N embeddings)."""
    print("\n" + "="*80)
    print("OLD WAY: Calling hybrid_search N times (creates N embeddings)")
    print("="*80)

    start_time = time.time()

    results = []
    for idx, doc in enumerate(documents, 1):
        result = search_service.hybrid_search(
            query=query,
            filters={"documents": [doc]},
            size=5
        )
        if result.is_ok():
            response = result.unwrap()
            results.append(response)
            print(f"  Document {idx}: {len(response.results)} results")
        else:
            print(f"  Document {idx}: Error - {result.unwrap_err()}")

    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.2f}s")
    print(f"📊 Embeddings created: {len(documents)} (one per document)")

    return elapsed


async def test_new_way(search_service, query: str, documents: list) -> float:
    """Test the new optimized approach: 1 call to hybrid_search_multi_document (1 embedding)."""
    print("\n" + "="*80)
    print("NEW WAY: Calling hybrid_search_multi_document once (creates 1 embedding)")
    print("="*80)

    start_time = time.time()

    # Use the global filter structure: {"documents": [...]}
    filters = {"documents": documents}

    result = await search_service.hybrid_search_multi_document(
        query=query,
        filters=filters,
        size=5
    )

    if result.is_ok():
        responses = result.unwrap()
        for idx, response in enumerate(responses, 1):
            print(f"  Document {idx}: {len(response.results)} results")
    else:
        print(f"  Error: {result.unwrap_err()}")

    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.2f}s")
    print(f"📊 Embeddings created: 1 (reused across all documents)")

    return elapsed


async def main():
    """Run the efficiency comparison test."""

    # Setup
    env_file = Path(".envs/local.env")
    search_service = OpenSearchVectorSearchServiceFactory.from_env_file(env_path=env_file)

    # Test documents
    documents = [
        {
            "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
            "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949",
        },
        {
            "project_id": "008a9fd2-9a4a-4c3f-ad5c-d33eca94af3b",
            "reference_doc_id": "aa1a0c65-8016-5d11-bbde-22055140660b",
        },
        {
            "project_id": "0096b72f-1c0d-4724-924f-011f87d3591a",
            "reference_doc_id": "16b6078b-248c-5ed9-83ef-20ee0af49396",
        },
    ]

    query = "Compare the liability limitations across these contracts"

    print("="*80)
    print("EFFICIENCY TEST: Multi-Document Search")
    print("="*80)
    print(f"Query: {query}")
    print(f"Documents: {len(documents)}")
    print("="*80)

    # Test old way (creates N embeddings)
    old_time = await test_old_way(search_service, query, documents)

    # Test new way (creates 1 embedding)
    new_time = await test_new_way(search_service, query, documents)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Old way (N embeddings): {old_time:.2f}s")
    print(f"New way (1 embedding):  {new_time:.2f}s")

    if old_time > new_time:
        speedup = old_time / new_time
        time_saved = old_time - new_time
        print(f"\n🚀 SPEEDUP: {speedup:.2f}x faster")
        print(f"⏱️  TIME SAVED: {time_saved:.2f}s ({time_saved/old_time*100:.1f}% reduction)")
    else:
        print(f"\n⚠️  Old way was faster (possibly due to caching or network variance)")

    # Cost analysis
    embedding_cost_per_1k_tokens = 0.00002  # Approximate OpenAI embedding cost
    avg_query_tokens = 20  # Rough estimate

    old_cost = (avg_query_tokens / 1000) * embedding_cost_per_1k_tokens * len(documents)
    new_cost = (avg_query_tokens / 1000) * embedding_cost_per_1k_tokens * 1

    print(f"\n💰 COST SAVINGS (estimated):")
    print(f"   Old way: ${old_cost:.6f} ({len(documents)} embeddings)")
    print(f"   New way: ${new_cost:.6f} (1 embedding)")
    print(f"   Savings: ${old_cost - new_cost:.6f} per query ({(old_cost-new_cost)/old_cost*100:.1f}% reduction)")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
