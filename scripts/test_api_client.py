"""Test client to verify API endpoints are working."""

import httpx
import asyncio
from loguru import logger


BASE_URL = "http://localhost:8000"


async def test_endpoint(client: httpx.AsyncClient, method: str, endpoint: str, json_data: dict = None):
    """Test a single endpoint and return the result."""
    try:
        if method.upper() == "GET":
            response = await client.get(f"{BASE_URL}{endpoint}")
        elif method.upper() == "POST":
            response = await client.post(f"{BASE_URL}{endpoint}", json=json_data, timeout=30.0)
        else:
            return {"error": f"Unsupported method: {method}"}

        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "error": str(e),
            "success": False
        }


async def main():
    """Test all API endpoints."""
    logger.info("Starting API endpoint tests...")

    async with httpx.AsyncClient() as client:
        # Test root endpoints
        logger.info("\n=== Testing Root Endpoints ===")

        tests = [
            ("GET", "/", None),
            ("GET", "/health", None),
        ]

        # Test status endpoints
        logger.info("\n=== Testing Status Endpoints ===")
        tests.extend([
            ("GET", "/api/opensearch/status", None),
            ("GET", "/api/postgres/status", None),
            ("GET", "/api/dynamodb/status", None),
            ("GET", "/api/openai/status", None),
        ])

        # Test contracts endpoints
        logger.info("\n=== Testing Contracts Endpoints ===")
        tests.extend([
            ("GET", "/api/contracts/", None),
            ("POST", "/api/contracts/search", {"query": "test"}),
        ])

        # Test chat endpoint
        logger.info("\n=== Testing Chat Endpoint ===")
        chat_request = {
            "query": "What is a contract?",
            "filters": None,
            "message_history": None
        }
        tests.append(("POST", "/api/chat/", chat_request))

        # Run all tests
        results = []
        for method, endpoint, data in tests:
            logger.info(f"Testing {method} {endpoint}...")
            result = await test_endpoint(client, method, endpoint, data)
            results.append(result)

            if result.get("success"):
                logger.success(f"✓ {method} {endpoint} - Status: {result['status_code']}")
            else:
                logger.error(f"✗ {method} {endpoint} - Error: {result.get('error', result.get('response'))}")

        # Summary
        logger.info("\n=== Test Summary ===")
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        logger.info(f"Passed: {successful}/{total}")

        # Show detailed results
        logger.info("\n=== Detailed Results ===")
        for result in results:
            endpoint = result.get("endpoint", "unknown")
            method = result.get("method", "unknown")
            if result.get("success"):
                logger.info(f"✓ {method} {endpoint}")
                # For chat endpoint, show a snippet of the response
                if endpoint == "/api/chat/":
                    response = result.get("response", {})
                    if isinstance(response, dict) and "answer" in response:
                        logger.info(f"  Answer snippet: {response['answer'][:100]}...")
            else:
                logger.error(f"✗ {method} {endpoint}")
                logger.error(f"  Error: {result.get('error', result.get('response'))}")


if __name__ == "__main__":
    asyncio.run(main())
