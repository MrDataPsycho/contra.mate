# Installation Guide

This guide will walk you through setting up Contramate on your local machine or server.

## Prerequisites

Before installing Contramate, ensure you have the following:

- **Python 3.12+** installed
- **Docker** and **Docker Compose** (for infrastructure services)
- **Git** for cloning the repository
- **uv** package manager (recommended) or pip
- **OpenAI API Key** (for LLM functionality)

## Step 1: Clone the Repository

```bash
git clone https://github.com/MrDataPsycho/contra.mate.git
cd contra.mate
```

## Step 2: Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Step 3: Install Python Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Step 4: Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .envs/local.env.example .envs/local.env
```

Edit `.envs/local.env` with your configuration:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_TEMPERATURE=0.0
OPENAI_MAX_TOKENS=4096
OPENAI_SEED=42

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=cuad
POSTGRES_USER=cuad_user
POSTGRES_PASSWORD=cuad_password

# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
OPENSEARCH_INDEX_NAME=contracts-test

# DynamoDB Configuration
DYNAMODB_ENDPOINT_URL=http://localhost:8001
DYNAMODB_REGION=us-east-1
DYNAMODB_ACCESS_KEY_ID=dummy
DYNAMODB_SECRET_ACCESS_KEY=dummy
DYNAMODB_TABLE_NAME=ConversationTable

# Application Configuration
APP_NAME=Contramate
APP_ENVIRONMENT=local
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
APP_VECTOR_DIMENSION=1536
APP_DEFAULT_INDEX_NAME=contracts-test
APP_LLM_PROVIDER=openai

# Agent Toggle Settings
AGENT_ENABLE_CLARIFIER_AGENT=true
AGENT_ENABLE_QUERY_REWRITER_AGENT=true
AGENT_ENABLE_ANSWER_CRITIQUE_AGENT=true
```

## Step 5: Start Infrastructure Services

Start PostgreSQL, OpenSearch, and DynamoDB using Docker Compose:

```bash
docker compose up -d
```

Verify services are running:

```bash
docker compose ps
```

You should see:
- PostgreSQL on port 5432
- OpenSearch on port 9200
- DynamoDB on port 8001

## Step 6: Initialize Database

Run database migrations and create tables:

```bash
# Create DynamoDB table
uv run python scripts/create_dynamodb_table.py

# PostgreSQL tables are automatically created by SQLModel
```

## Step 7: Load Sample Data (Optional)

If you have the CUAD dataset, load it into the database:

```bash
# Extract contracts to bronze layer
# (Place your contract files in data/bronze/)

# Run data pipeline
# (Custom pipeline scripts based on your data format)
```

## Step 8: Verify Installation

Test that everything is working:

```bash
# Run basic tests
uv run python scripts/test_metadata_insight_agent.py

# Start the API server
uv run uvicorn contramate.api.main:app --reload
```

Visit `http://localhost:8000/docs` to see the API documentation.

## Optional: Frontend Setup

If you want to run the Next.js frontend:

```bash
cd frontend

# Install dependencies
pnpm install

# Start development server
pnpm dev
```

Visit `http://localhost:3000` to access the web interface.

## Troubleshooting

### Docker Services Not Starting

```bash
# Check logs
docker compose logs

# Restart services
docker compose down
docker compose up -d
```

### PostgreSQL Connection Issues

Ensure PostgreSQL is accessible:

```bash
# Test connection
psql -h localhost -p 5432 -U cuad_user -d cuad
```

### OpenSearch Not Responding

```bash
# Check OpenSearch health
curl http://localhost:9200/_cluster/health

# View logs
docker compose logs opensearch
```

### Import Errors

```bash
# Reinstall dependencies
uv sync --force

# Verify Python version
python --version  # Should be 3.12+
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Learn basic usage

## Development Installation

For development with additional tools:

```bash
# Install with development dependencies
uv sync --all-extras

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

## Docker-Only Installation

To run everything in Docker:

```bash
# Build and start all services
docker compose up -d --build

# Access the API
curl http://localhost:8000/health
```

This will start:
- Backend API (port 8000)
- Frontend UI (port 3000)
- PostgreSQL (port 5432)
- OpenSearch (port 9200)
- DynamoDB (port 8001)
