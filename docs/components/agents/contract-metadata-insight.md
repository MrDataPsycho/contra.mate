# Contract Metadata Insight Agent

The Contract Metadata Insight Agent is a SQL-based agent that transforms natural language questions into SQL queries and executes them against structured contract metadata tables.

## Overview

This agent provides fast, accurate answers to questions about contract metadata by:

1. Converting natural language queries to SQL
2. Executing queries against PostgreSQL tables
3. Formatting results with citations
4. Enforcing safety guardrails

## Key Features

- ✅ **Natural Language to SQL**: Automatically generates SQL from questions
- ✅ **Dual Table Support**: Queries both ASMD (clause data) and ESMD (financial data)
- ✅ **Smart Joins**: Handles LEFT JOIN for missing ESMD data
- ✅ **Query Guardrails**: Enforces WHERE/LIMIT requirements
- ✅ **Citation Tracking**: Every answer includes source references
- ✅ **Token Management**: Tracks usage across iterations

## Database Schema

### Contract ASMD (Application Structured Metadata)

60+ fields including:

- `project_id`, `reference_doc_id`: Composite primary key
- `document_title`, `contract_type`: Basic metadata
- `parties_answer`: Contract parties
- `agreement_date_answer`: Effective date
- `non_compete_answer`: Yes/No for non-compete clauses
- `ip_ownership_assignment_answer`: IP ownership provisions
- `termination_for_convenience_answer`: Termination clauses
- And 50+ more clause-level fields...

### Contract ESMD (Extracted Structured Metadata)

30+ fields including:

- `project_id`, `reference_doc_id`: Foreign key to ASMD
- `total_contract_value`: Financial value
- `payment_schedule`: Payment terms
- `deliverables_activities`: Work description
- `effective_date`, `termination_date`: Contract timeline
- And 25+ more financial/operational fields...

## Usage

### Basic Usage

```python
import asyncio
from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory
)

async def main():
    # Create agent with default settings
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    # Run query
    result = await agent.run("How many contracts have non-compete clauses?")
    
    print(result["answer"])
    print(result["citations"])

asyncio.run(main())
```

### With Custom Model

```python
# Use a different model
agent = ContractMetadataInsightAgentFactory.create_default(
    model="gpt-4",
    max_iterations=10
)

result = await agent.run("Complex query requiring more tokens...")
```

### With Filters

```python
# Apply filters for scoped queries
filters = {
    "project_id": "abc-123",
    "contract_type": "Service Agreement"
}

result = await agent.run(
    "How many contracts are there?",
    filters=filters
)
```

## Query Examples

### Counting and Aggregation

```python
# Basic count
"How many contracts are in the database?"

# Count by type
"How many Service Agreements do we have?"

# Group by
"Show me contract counts by type"

# Aggregation
"What's the average number of clauses per contract?"
```

### Clause Analysis

```python
# Single clause
"How many contracts have non-compete clauses?"

# Multiple clauses
"Find contracts with both IP ownership and termination clauses"

# Clause breakdown
"Show me non-compete clauses grouped by contract type"

# Percentage analysis
"What percentage of contracts have arbitration clauses?"
```

### Financial Queries (ESMD)

```python
# Value analysis
"What's the total value of all Service Agreements?"

# Average values
"What's the average contract value by type?"

# Payment terms
"Show me contracts with milestone-based payment schedules"

# Date analysis
"How many contracts were signed in 2023?"
```

### Join Queries (ASMD + ESMD)

```python
# Combined analysis
"Show me contracts with non-compete clauses and contract values over $1M"

# Missing data
"How many contracts have clause data but no financial data?"

# Comprehensive view
"Give me a summary of Development Agreements with all available data"
```

## Response Format

Every response includes:

```python
{
    "success": True,
    "answer": "Found 45 contracts with non-compete clauses [doc1]...",
    "citations": {
        "doc1": "Database: contract_asmd table (Application Structured Metadata)"
    }
}
```

### Citation Formats

**ASMD Only:**
```python
"doc1": "Database: contract_asmd table (Application Structured Metadata - clause analysis)"
```

**ESMD Only:**
```python
"doc1": "Database: contracting_esmd table (Extracted Structured Metadata - financial analysis)"
```

**Join Query:**
```python
"doc1": "Database: contract_asmd and contracting_esmd tables (combined clause and financial analysis)"
```

## Query Guardrails

### Required Rules

All queries MUST include either:

- `WHERE` clause (to filter results)
- `LIMIT` clause (to cap results)
- Both (recommended best practice)

### Enforced Restrictions

❌ **Blocked:**
```sql
-- No WHERE or LIMIT
SELECT * FROM contract_asmd

-- Dangerous operations
DELETE FROM contract_asmd
UPDATE contract_asmd SET ...
DROP TABLE contract_asmd
```

✅ **Allowed:**
```sql
-- With LIMIT
SELECT * FROM contract_asmd LIMIT 100

-- With WHERE
SELECT * FROM contract_asmd WHERE contract_type = 'Service'

-- With both (best practice)
SELECT * FROM contract_asmd 
WHERE contract_type = 'Service' 
LIMIT 10
```

### Maximum Limits

- `LIMIT` must be ≤ 1000 rows
- Queries returning >1000 rows will be capped

## Configuration

### Model Settings

Configured via environment variables in `.envs/local.env`:

```bash
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TEMPERATURE=0.0
OPENAI_SEED=42
OPENAI_MAX_TOKENS=4096
```

### Database Settings

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=cuad
POSTGRES_USER=cuad_user
POSTGRES_PASSWORD=cuad_password
```

## Advanced Features

### Token Tracking

The agent tracks token usage across iterations:

```python
result = await agent.run("Complex query...")

# Token info is logged automatically
# Prompt tokens: 4729
# Completion tokens: 48
# Total tokens: 4777
```

### Retry Logic

Built-in retry with exponential backoff for resilience.

### Error Handling

Comprehensive error handling:

- SQL syntax errors
- Connection failures
- Query timeout
- Response validation errors

## Best Practices

### 1. Always Use WHERE + LIMIT

```python
# Good
"Show me 10 Service Agreements with non-compete clauses"

# Better - more specific
"Show me Service Agreements signed in 2023 with non-compete clauses, limit 10"
```

### 2. Be Specific About Time Ranges

```python
# Vague
"Show me recent contracts"

# Specific
"Show me contracts signed in the last 6 months"
```

### 3. Request Aggregates for Large Datasets

```python
# Instead of listing all
"Show me all contracts with IP clauses"

# Use aggregation
"How many contracts have IP clauses, grouped by type"
```

### 4. Use JOIN Queries Carefully

```python
# Check if ESMD data exists first
"How many contracts have both clause and financial data?"

# Then query specifics
"Show me those contracts with values over $500K"
```

## Troubleshooting

### Query Blocked Errors

If you see "Query blocked" errors:

```python
# Problem
result = await agent.run("Show me all contracts")

# Solution
result = await agent.run("Show me 100 contracts")
# or
result = await agent.run("Show me contracts of type Service")
```

### No Results

Check your filters:

```python
# Wrong contract type name
filters = {"contract_type": "Service Agreement"}  # Doesn't exist

# Correct
filters = {"contract_type": "Service"}  # Exists in DB
```

### Timeout Errors

For complex queries:

```python
# Increase max iterations
agent = ContractMetadataInsightAgentFactory.create_default(
    max_iterations=10  # Default is 5
)
```
