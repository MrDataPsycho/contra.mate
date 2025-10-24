# Quick Start Guide

Get started with Contramate in minutes! This guide will walk you through your first queries and demonstrate the core functionality.

## Prerequisites

Make sure you've completed the [Installation Guide](installation.md) and have:

- ✅ Infrastructure services running (Docker Compose)
- ✅ Environment variables configured
- ✅ Dependencies installed

## Your First Query

Let's start with a simple metadata query using the Contract Metadata Insight Agent.

### 1. Create the Agent

```python
import asyncio
from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory
)

# Create agent with default settings
agent = ContractMetadataInsightAgentFactory.create_default()
```

### 2. Run a Basic Query

```python
async def run_query():
    # Ask a question about contracts
    result = await agent.run("How many contracts are in the database?")
    
    # Print the answer
    print("Answer:", result["answer"])
    print("\nCitations:", result["citations"])
    
    return result

# Run the query
result = asyncio.run(run_query())
```

**Expected Output:**
```
Answer: There are a total of 510 contracts in the database [doc1].

Citations: {'doc1': 'Database: contract_asmd table (Application Structured Metadata)'}
```

## Common Query Patterns

### Contract Type Analysis

```python
async def analyze_contract_types():
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    result = await agent.run(
        "What are the different types of contracts and how many of each?"
    )
    
    print(result["answer"])

asyncio.run(analyze_contract_types())
```

### Clause Analysis

```python
async def analyze_clauses():
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    result = await agent.run(
        "How many contracts have non-compete clauses? "
        "Show me the breakdown by contract type."
    )
    
    print(result["answer"])

asyncio.run(analyze_clauses())
```

### Financial Analysis (with ESMD)

```python
async def analyze_financials():
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    result = await agent.run(
        "Show me contracts with non-compete clauses that also have "
        "total contract values. What's the average value?"
    )
    
    print(result["answer"])

asyncio.run(analyze_financials())
```

## Using Filters

You can pass filters to narrow down queries:

```python
async def query_with_filters():
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    # Filter by contract type
    filters = {"contract_type": "Service Agreement"}
    
    result = await agent.run(
        "How many contracts are there?",
        filters=filters
    )
    
    print(result["answer"])

asyncio.run(query_with_filters())
```

## Semantic Search with Talk to Contract

For document content analysis, use the Talk to Contract agent:

```python
from contramate.core.agents.talk_to_contract import TalkToContractAgent

async def semantic_search():
    # This requires OpenSearch with indexed contracts
    agent = TalkToContractAgent.create_default()
    
    result = await agent.run(
        "What are the termination conditions in Service Agreements?"
    )
    
    print(result["answer"])
    print("\nSources:")
    for key, source in result["citations"].items():
        print(f"  {key}: {source}")

asyncio.run(semantic_search())
```

## Complete Example Script

Save this as `quickstart_example.py`:

```python
"""
Contramate Quick Start Example
Demonstrates basic usage of the Contract Metadata Insight Agent
"""

import asyncio
from loguru import logger
from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory
)


async def run_examples():
    """Run a series of example queries."""
    
    # Create agent
    logger.info("Creating Contract Metadata Insight Agent...")
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    # Example 1: Basic count
    logger.info("\n" + "="*80)
    logger.info("Example 1: Basic Contract Count")
    logger.info("="*80)
    result = await agent.run("How many contracts are in the database?")
    print(f"\n{result['answer']}\n")
    
    # Example 2: Contract types
    logger.info("\n" + "="*80)
    logger.info("Example 2: Contract Type Distribution")
    logger.info("="*80)
    result = await agent.run(
        "What are the top 5 most common contract types?"
    )
    print(f"\n{result['answer']}\n")
    
    # Example 3: Clause analysis
    logger.info("\n" + "="*80)
    logger.info("Example 3: Non-Compete Clause Analysis")
    logger.info("="*80)
    result = await agent.run(
        "How many contracts have non-compete clauses? "
        "Show the top 3 contract types."
    )
    print(f"\n{result['answer']}\n")
    
    # Example 4: Join query
    logger.info("\n" + "="*80)
    logger.info("Example 4: ASMD + ESMD Join")
    logger.info("="*80)
    result = await agent.run(
        "How many contracts have both clause data and financial data?"
    )
    print(f"\n{result['answer']}\n")
    
    logger.success("✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(run_examples())
```

Run it:

```bash
uv run python quickstart_example.py
```

## Understanding the Response

Every agent response includes:

### 1. Success Status

```python
result["success"]  # True or False
```

### 2. Answer with Citations

```python
result["answer"]  # Natural language answer with [doc1], [doc2] markers
```

### 3. Citation Sources

```python
result["citations"]  # Dictionary mapping doc1, doc2, etc. to sources
```

Example:
```json
{
  "success": true,
  "answer": "Found 45 contracts with non-compete clauses [doc1].",
  "citations": {
    "doc1": "Database: contract_asmd table (Application Structured Metadata)"
  }
}
```

## Query Safety and Guardrails

The system enforces strict safety rules:

### ✅ Allowed Queries

```python
# Queries with LIMIT
"SELECT * FROM contract_asmd LIMIT 100"

# Queries with WHERE
"SELECT * FROM contract_asmd WHERE contract_type = 'Service'"

# Queries with both (best practice)
"SELECT * FROM contract_asmd WHERE contract_type = 'Service' LIMIT 10"
```

### ❌ Blocked Queries

The LLM will automatically add WHERE or LIMIT clauses, but if it doesn't:

```python
# No WHERE or LIMIT - will be rejected
"SELECT * FROM contract_asmd"

# Dangerous operations - not possible
"DELETE FROM contract_asmd"
"UPDATE contract_asmd SET ..."
"DROP TABLE contract_asmd"
```

## Tips for Effective Queries

### 1. Be Specific

❌ "Tell me about contracts"  
✅ "How many Service Agreements have termination clauses?"

### 2. Use Natural Language

The agent understands context:

```python
"Show me contracts from Microsoft with IP ownership clauses"
"What's the average contract value for Distributor agreements?"
"Find contracts signed in 2023 with non-compete provisions"
```

### 3. Ask for Breakdowns

```python
"Show me the breakdown by contract type"
"Group by year and show trends"
"What percentage have this clause?"
```

### 4. Combine Filters

```python
"Find Service Agreements with both termination AND arbitration clauses"
"Show contracts with IP ownership OR licensing provisions"
```

## Next Steps

Now that you understand the basics, explore more:

- [Installation Guide](installation.md) - Full installation details
- [Contract Metadata Insight Agent](../components/agents/contract-metadata-insight.md) - Deep dive into the agent

## Troubleshooting

### "No module named 'contramate'"

```bash
# Reinstall in development mode
uv sync
```

### "Connection refused" errors

```bash
# Ensure Docker services are running
docker compose ps
docker compose up -d
```

### "Query blocked" errors

Check that your query includes WHERE or LIMIT:

```python
# This will be blocked
result = await agent.run("SELECT everything from contracts")

# This will work
result = await agent.run("Show me 10 contracts")
```

## Getting Help

- 📖 [Full Documentation](../index.md)
- 🐛 [Report Issues](https://github.com/MrDataPsycho/contra.mate/issues)
- 💬 [Ask Questions](https://github.com/MrDataPsycho/contra.mate/discussions)
