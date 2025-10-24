"""Direct test of guardrail logic without LLM intelligence.

This script directly tests the query validation guardrail by simulating
SQL queries without going through the LLM, to verify the guardrail
itself blocks unsafe queries.
"""

from loguru import logger


def validate_query(query: str) -> tuple[bool, str | None]:
    """
    Validate SQL query against guardrails.
    
    Returns:
        (is_valid, error_message)
    """
    query_upper = query.upper()
    
    # Check for SELECT only
    if not query_upper.strip().startswith("SELECT"):
        return False, "Only SELECT queries are allowed"
    
    # Check for dangerous keywords
    dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return False, f"Dangerous keyword '{keyword}' not allowed"
    
    # Check for WHERE or LIMIT
    has_where = "WHERE" in query_upper
    has_limit = "LIMIT" in query_upper
    
    if not has_where and not has_limit:
        return False, "REJECTED: All SELECT queries must include either a WHERE clause or a LIMIT clause (or both) to prevent pulling entire tables."
    
    return True, None


def test_query(description: str, query: str, should_pass: bool):
    """Test a single query."""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"TEST: {description}")
    logger.info(f"{'=' * 80}")
    logger.info(f"Query: {query}")
    
    is_valid, error = validate_query(query)
    
    if should_pass:
        if is_valid:
            logger.success("✅ Query passed as expected!")
        else:
            logger.error(f"❌ Query should have passed but was blocked: {error}")
    else:
        if not is_valid:
            logger.success(f"✅ Query blocked as expected: {error}")
        else:
            logger.error("❌ Query should have been blocked but passed!")
    
    return is_valid == should_pass


def main():
    """Run all direct guardrail tests."""
    logger.info("🚀 Starting Direct Guardrail Tests")
    logger.info("Testing the guardrail logic without LLM intelligence")
    
    results = []
    
    # Test 1: SELECT * without WHERE or LIMIT - SHOULD BLOCK
    results.append(test_query(
        "SELECT * without WHERE or LIMIT (Should BLOCK)",
        "SELECT * FROM contract_asmd",
        should_pass=False
    ))
    
    # Test 2: SELECT columns without WHERE or LIMIT - SHOULD BLOCK
    results.append(test_query(
        "SELECT columns without WHERE or LIMIT (Should BLOCK)",
        "SELECT contract_type, document_title FROM contract_asmd",
        should_pass=False
    ))
    
    # Test 3: SELECT with only LIMIT - SHOULD PASS
    results.append(test_query(
        "SELECT with LIMIT only (Should PASS)",
        "SELECT * FROM contract_asmd LIMIT 100",
        should_pass=True
    ))
    
    # Test 4: SELECT with only WHERE - SHOULD PASS
    results.append(test_query(
        "SELECT with WHERE only (Should PASS)",
        "SELECT * FROM contract_asmd WHERE contract_type = 'Service'",
        should_pass=True
    ))
    
    # Test 5: SELECT with both WHERE and LIMIT - SHOULD PASS
    results.append(test_query(
        "SELECT with WHERE and LIMIT (Should PASS - Best Practice)",
        "SELECT * FROM contract_asmd WHERE contract_type = 'Service' LIMIT 10",
        should_pass=True
    ))
    
    # Test 6: COUNT without WHERE or LIMIT - SHOULD BLOCK
    results.append(test_query(
        "COUNT without WHERE or LIMIT (Should BLOCK)",
        "SELECT COUNT(*) FROM contract_asmd",
        should_pass=False
    ))
    
    # Test 7: COUNT with LIMIT - SHOULD PASS
    results.append(test_query(
        "COUNT with LIMIT (Should PASS)",
        "SELECT COUNT(*) FROM contract_asmd LIMIT 1",
        should_pass=True
    ))
    
    # Test 8: JOIN without WHERE or LIMIT - SHOULD BLOCK
    results.append(test_query(
        "JOIN without WHERE or LIMIT (Should BLOCK)",
        "SELECT a.*, e.* FROM contract_asmd a LEFT JOIN contracting_esmd e ON a.project_id = e.project_id",
        should_pass=False
    ))
    
    # Test 9: JOIN with LIMIT - SHOULD PASS
    results.append(test_query(
        "JOIN with LIMIT (Should PASS)",
        "SELECT a.*, e.* FROM contract_asmd a LEFT JOIN contracting_esmd e ON a.project_id = e.project_id LIMIT 50",
        should_pass=True
    ))
    
    # Test 10: Dangerous query - DELETE - SHOULD BLOCK
    results.append(test_query(
        "DELETE query (Should BLOCK)",
        "DELETE FROM contract_asmd WHERE project_id = 'test'",
        should_pass=False
    ))
    
    logger.info(f"\n{'=' * 80}")
    logger.info("📊 TEST SUMMARY")
    logger.info(f"{'=' * 80}")
    passed = sum(results)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.success("🎉 All guardrail tests passed!")
    else:
        logger.error(f"❌ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
