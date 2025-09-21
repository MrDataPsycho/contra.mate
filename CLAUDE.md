# Contramate - AI Agent Context

## Project Overview
Contramate is a Conversational AI Agent Application designed to interact with CUAD (Contract Understanding Atticus Dataset) using LLM Agents, VectorDB, and workflows. This is an early-stage project with minimal implementation currently in place.

## Project Structure
```
contramate/
├── src/contramate/          # Main Python package
│   └── __init__.py         # Simple entry point with hello world function
├── data/                   # Empty data directory (likely for CUAD dataset)
├── docker-compose.yml      # Multi-service Docker setup
├── Dockerfile.backend     # Backend service Docker configuration
├── pyproject.toml         # Python project configuration
├── README.md              # Project description
├── .python-version        # Python 3.12
└── .gitignore            # Standard Python gitignore
```

### High Level Details
- The Application is A Chat Assistant for Contract Understanding using LLM Agents, VectorDB, and workflows.
- The main backend is a package is `contramate` located in `src/contramate`.
- The DynamoDB used as main NoSQL database to store per user, per conversation/workspace puer messages (User and Assistant messages).
- The PostgreSQL is used to store the metadata related to CUAD dataset and any other relational data.
- The OpenSearch is used as the vector database to store the document embeddings and perform similarity search
- The OpenSearch Dashboards is used as the web interface to visualize and analyze the search data
- The Frontend is a Next.js application located in `frontend/` directory
- Use uv package manager for python package management

## Instruction from Principal Developer
- Do not use relative imports in python always use contramate as the root package.
- Use pydantic settings for all configuration and environment variables.
- Always create a services module for any business logic or external service interaction.
- Use FastAPI for any API endpoints.

- Use SQLModel for any database interaction when connecting to PostgreSQL where there will be metadata tables

## Technology Stack

### Current Implementation
- **Python 3.12**: Main programming language
- **Package Management**: Uses pyproject.toml with hatchling build system
- **Containerization**: Docker with multi-service setup

### Current Architecture (based on docker-compose.yml)
- **Backend**: FastAPI/Uvicorn service (port 8000) - `src/contramate/api/main.py`
- **Frontend**: Next.js application (port 3000) with TypeScript and Tailwind CSS
- **Database**: PostgreSQL (port 5432) for CUAD dataset
- **NoSQL**: DynamoDB Local (port 8001) for additional data storage
- **Vector Search**: OpenSearch (port 9200) for document embeddings and similarity search
- **Search Dashboard**: OpenSearch Dashboards (port 5601) for search analytics and visualization

## Services Configuration

### Backend Service
- Container: `rag-backend`
- Port: 8000
- Entry point: `uvicorn src.services.main:app`
- Environment variables:
  - `RUNTIME_ENV=local`
  - `HOST_SYSTEM=container`
  - `VECTOR_INDEX=contracts_oai`

### Frontend Service
- Container: `rag-frontend`
- Port: 3000 (Next.js default)
- Framework: Next.js with TypeScript, Tailwind CSS, ESLint
- Depends on backend service
- Environment: `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Build: Standalone output for Docker optimization

### Database Services
- **PostgreSQL**: Database name `cuad`, user `cuad_user`
- **DynamoDB Local**: For local development
- **OpenSearch**: Vector search engine with disabled security for local development
- **OpenSearch Dashboards**: Web interface for search analytics

## Development Notes

### Current State
- **Backend**: FastAPI application with functional status services and centralized configuration
- **Frontend**: Production-optimized Next.js application with TypeScript, Tailwind CSS, and API client
- **Infrastructure**: Complete Docker setup with uv-optimized builds and all required services
- **Settings Management**: Pydantic-based settings with automatic environment loading from `.envs/local.env`
- **Database Services**: Working connection status checks for PostgreSQL, OpenSearch, and DynamoDB
- **Dependencies**: Complete stack with FastAPI, OpenSearch, PostgreSQL, DynamoDB, SQLModel, and Pydantic Settings

### Current Implementation Status
- **FastAPI Backend**: Complete API structure with CORS, health endpoints, and working status services
- **Next.js Frontend**: Production-ready with TypeScript, Tailwind CSS, and API client
- **Docker Configuration**: Multi-service setup with OpenSearch, PostgreSQL, DynamoDB (uv-optimized backend)
- **Centralized Settings**: Pydantic-based configuration with environment groups
- **Status Services**: Real connection testing for all databases and search services
- **API Endpoints**: Health check, contracts, search, and functional database status endpoints

### Next Development Areas
1. **Database Connections**: Implement actual connections to PostgreSQL, OpenSearch, and DynamoDB
2. **CUAD Dataset Integration**: Loading and processing contract data
3. **OpenSearch Integration**: Document indexing, vector embeddings, and similarity search
4. **LLM Agent Implementation**: Conversational AI for contract understanding
5. **Frontend UI**: Build contract search and analysis interface
6. **Workflow Management**: Processing pipelines for contract analysis
7. **Search Analytics**: Utilizing OpenSearch Dashboards for query insights

### Build and Run Commands
```bash
# Install backend package
pip install .

# Run backend locally (development)
uvicorn src.contramate.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run frontend locally (development)
cd frontend && npm run dev

# Run full stack with Docker Compose
docker-compose up
```

### All access points:
  - Frontend (Next.js): http://localhost:3000
  - Backend API: http://localhost:8000
  - OpenSearch Dashboards: http://localhost:5601
  - OpenSearch API: http://localhost:9200

### Environment Requirements
- Python >= 3.12 with uv package manager
- Node.js 20+ for Next.js frontend
- Docker and Docker Compose for full stack deployment
- OpenAI API key for LLM services (configured in `.envs/local.env`)

## Notes for AI Agents
- **Architecture**: Next.js frontend + FastAPI backend + OpenSearch + PostgreSQL + DynamoDB
- **Settings Management**: Centralized Pydantic settings in `src/contramate/utils/settings/core.py`
- **Configuration Groups**:
  - `settings.postgres` - PostgreSQL database settings
  - `settings.dynamodb` - DynamoDB settings
  - `settings.opensearch` - OpenSearch configuration
  - `settings.openai` - OpenAI API settings (GPT-5-mini)
  - `settings.app` - Application configuration
- **Environment Loading**: Automatic loading from `.envs/local.env` or system environment
- **Status Services**: Working connection checks for all databases accessible via API endpoints
- **Entry Points**:
  - Backend: `src/contramate/api/main.py`
  - Settings: `src/contramate/utils/settings/core.py`
  - Frontend: Next.js app in `frontend/` directory
  - Environment: `.envs/local.env`
- **Development**: All services containerized with uv-optimized builds, security disabled for local development
- **API Endpoints**:
  - `/api/postgres/status` - PostgreSQL connection status
  - `/api/opensearch/status` - OpenSearch cluster health
  - `/api/dynamodb/status` - DynamoDB connection status
- **Next Steps**: Implement CUAD dataset processing and LLM agent workflows
- **Testing**: Use OpenSearch Dashboards (port 5601) for search visualization and debugging


### CLI Status Checker

  Location: src/tools/status_checker.py
  Features:

  Service Mappings:
  - ✅ Short Names: postgres, dynamodb, opensearch, openai, litellm
  - ✅ Dependency Injection: Proper client injection for AI services
  - ✅ Service Types: Database/Search services and AI services

  Commands:
  - ✅ Single Service: python src/tools/status_checker.py check postgres
  - ✅ All Services: python src/tools/status_checker.py check all
  - ✅ List Services: python src/tools/status_checker.py list-services
  - ✅ Verbose Mode: --verbose flag for detailed output