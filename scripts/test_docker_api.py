"""Test the Docker API endpoint directly to check citation format."""

import httpx
import json
from loguru import logger

async def test_docker_api():
    """Test Docker API endpoint."""
    logger.info("=== Testing Docker API Endpoint ===")

    url = "http://localhost:8000/api/chat/"

    payload = {
        "query": "What are the payment terms?",
        "filters": {
            "documents": [
                {
                    "project_id": "00149794-2432-4c18-b491-73d0fafd3efd",
                    "reference_doc_id": "577ff0a3-a032-5e23-bde3-0b6179e97949"
                }
            ]
        },
        "message_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ]
    }

    logger.info(f"Sending request to: {url}")
    logger.info(f"Payload: {json.dumps(payload, indent=2)}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)

            logger.info(f"\nStatus Code: {response.status_code}")
            logger.info(f"\nResponse Headers: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"\n=== Response Data ===")
                logger.info(f"Success: {data.get('success')}")
                logger.info(f"\nAnswer snippet: {data.get('answer', '')[:200]}...")
                logger.info(f"\nCitations: {data.get('citations')}")
                logger.info(f"\nCitation type: {type(data.get('citations'))}")

                # Check citation format
                citations = data.get('citations', {})
                if citations:
                    first_key = list(citations.keys())[0]
                    first_value = list(citations.values())[0]
                    logger.info(f"\nFirst citation key: {first_key} (type: {type(first_key).__name__})")
                    logger.info(f"First citation value: {first_value} (type: {type(first_value).__name__})")

                # Check if answer has inline citations
                answer = data.get('answer', '')
                has_doc_citations = any(f"[doc{i}]" in answer for i in range(1, 10))
                logger.info(f"\nAnswer contains [docN] citations: {has_doc_citations}")

                logger.info(f"\nMetadata: {data.get('metadata')}")
            else:
                logger.error(f"\nError Response: {response.text}")

        except Exception as e:
            logger.error(f"Error: {e}")
            logger.exception("Full traceback:")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_docker_api())
