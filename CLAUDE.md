# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

### High Level Details
- The Application is A Chat Assistant for Contract Understanding using LLM Agents, VectorDB, and workflows.
- The main backend is a package is `contramate` located in `src/contramate`.
- Use uv package manager for python package management
- The DynamoDB used as main NoSQL database to store per user, per conversation/workspace puer messages (User and Assistant messages).
- The PostgreSQL is used to store the metadata related to CUAD dataset and any other relational data.
- The OpenSearch is used as the vector database to store the document embeddings and perform similarity search
- The OpenSearch Dashboards is used as the web interface to visualize and analyze the search data
- The Frontend is a Next.js application located in `frontend/` directory, TypeScript Next.js 15 starter template for AI-powered applications:


## Development Commands

- `pnpm dev` - Start development server with Turbopack
- `pnpm build` - Build production app with Turbopack
- `pnpm start` - Start production server
- `pnpm tsc --noEmit` - Run TypeScript compiler to check for type errors
- uv to install python packages
- `uv run <module>` - Run a Python module

## Code Quality

**IMPORTANT**: Always run `pnpm tsc --noEmit` after writing or modifying any code to ensure there are no TypeScript errors before considering the task complete.

## Package Manager

This project strictly uses **pnpm**. Do not use npm or yarn.

## Architecture

## Frontend Architecture

This is a TypeScript Next.js 15 starter template for AI-powered applications:

### Core Stack
- **Next.js 15** with App Router
- **AI SDK 5** with OpenAI GPT-5 integration
- **shadcn/ui** components (New York style, neutral base color)
- **Tailwind CSS v4** for styling

### Key Directories
- `app/` - Next.js App Router pages and API routes
- `app/api/chat/` - AI chat endpoint using non-streaming `generateText()`
- `components/ui/` - shadcn/ui components
- `lib/utils.ts` - Utility functions including `cn()` for className merging

### AI Integration
- Uses AI SDK 5's `generateText()` for non-streaming responses
- Configured for GPT-5 via OpenAI provider
- API route at `/api/chat` expects `{ message: string }` and returns `{ response: string }`
- Requires `OPENAI_API_KEY` in `.env.local`

### UI Components
- **shadcn/ui** configured with:
  - New York style
  - Neutral base color with CSS variables
  - Import aliases: `@/components`, `@/lib/utils`, `@/components/ui`
  - Lucide React for icons
- **AI Elements** from Vercel:
  - Pre-built components for AI applications
  - Located in `components/ai-elements/`
  - Key components: Conversation, Message, PromptInput
  - Uses `UIMessage` type from AI SDK

### Adding Components
- shadcn/ui: `pnpm dlx shadcn@latest add [component-name]`
- AI Elements: `pnpm dlx ai-elements@latest` (adds all components)

### Environment Setup
Create `.env.local` with:
```
OPENAI_API_KEY=your_openai_api_key_here
```

## Project Structure
```
contramate/
├── src/contramate/          # Main Python package
│   └── __init__.py         # Simple entry point with hello world function
├── frontend/               # Next.js frontend application
├── data/                   # Empty data directory (likely for CUAD dataset)
├── docker-compose.yml      # Multi-service Docker setup
├── Dockerfile.backend     # Backend service Docker configuration
├── pyproject.toml         # Python project configuration
├── README.md              # Project description
├── .python-version        # Python 3.12
└── .gitignore            # Standard Python gitignore
```



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

## AI Client System

### Client Architecture
**Location**: `src/contramate/utils/clients/ai/`

The project implements a comprehensive AI client system with support for multiple providers and both chat and embedding capabilities:

#### Available Clients
- **OpenAIChatClient**: Direct OpenAI API integration for chat completions
- **LiteLLMChatClient**: Multi-provider chat client supporting OpenAI and Azure OpenAI via LiteLLM
- **AzureOpenAIChatClient**: Native Azure OpenAI client with certificate-based authentication
- **OpenAIEmbeddingClient**: OpenAI embeddings for vector search
- **LiteLLMEmbeddingClient**: Multi-provider embeddings via LiteLLM
- **AzureOpenAIEmbeddingClient**: Azure OpenAI embeddings with certificate auth

#### Client Features
- **Unified Interface**: All clients inherit from `BaseChatClient` or `BaseEmbeddingClient`
- **Sync/Async Support**: Both synchronous and asynchronous operations
- **Tool Calling**: Function calling capabilities for agent interactions via `select_tool()` method
- **JSON Mode**: Structured response support via `config` parameter
- **Backward Compatibility**: Simplified `chat()` method for existing agent code

#### Authentication Methods
- **OpenAI**: API key-based authentication
- **Azure OpenAI**: Certificate-based authentication using `azure-identity`
- **LiteLLM**: Supports both OpenAI API keys and Azure certificate tokens

### Multi-Agent System

**Location**: `src/contramate/core/agents/`

#### Agent Components
- **OrchrastratorAgent** (`orchrastrator.py`): Main coordinator managing conversation flow
- **QueryRewriterAgent** (`query_rewriter.py`): Contextualizes and refines user queries
- **ToolExecutorAgent** (`tool_executor.py`): Selects and executes appropriate tools via LLM function calling
- **AnswerCritiqueAgent** (`answer_critique.py`): Evaluates responses and suggests improvements

#### Available Tools (`tools.py`)
- **vector_db_retriver_tool**: Semantic search via OpenSearch (implementation pending)
- **summery_retriver_tool**: Contract summary retrieval by CWID (implementation pending)
- **compare_contract_tool**: Contract comparison functionality (implementation pending)

### Settings & Configuration

**Configuration Groups**:
- `settings.postgres` - PostgreSQL database settings
- `settings.dynamodb` - DynamoDB settings
- `settings.opensearch` - OpenSearch configuration
- `settings.openai` - OpenAI API settings
- `settings.azure_openai` - Azure OpenAI certificate-based authentication settings
- `settings.app` - Application configuration

**Azure OpenAI Configuration**:
- Certificate-based authentication via `azure-identity`
- Configurable via `AZURE_OPENAI_*` environment variables
- Token provider utility in `contramate.utils.auth.certificate_provider`

### Current Implementation Status

#### ✅ Completed Components
- **AI Client System**: Full implementation with OpenAI, LiteLLM, and Azure OpenAI support
- **Agent Framework**: All four agents implemented with tool calling capabilities
- **Settings System**: Complete configuration management with Azure support
- **Tool Infrastructure**: Function calling framework ready for tool execution
- **Docker & Dependencies**: LiteLLM version constrained to `1.40.0-1.50.0` to avoid build issues

#### 🚧 In Progress / Pending
- **Database Models**: Contract metadata and summary models need implementation
- **Vector Store Integration**: OpenSearch connection and embedding storage
- **Tool Implementations**: Actual database queries and vector search functionality
- **Frontend Integration**: Agent system integration with Next.js interface

#### 📋 Dependencies
- **Python**: 3.12 with `uv` package manager
- **LLM Dependencies**: `openai>=1.108.1`, `litellm>=1.40.0,<1.50.0`, `azure-identity>=1.25.0`
- **Database**: `psycopg2-binary`, `boto3`, `opensearch-py`, `sqlmodel`
- **Framework**: `fastapi`, `pydantic-settings`, `loguru`

#### 🔧 Agent Tool Requirements
**Current Status**: Tools have placeholder implementations that return informative messages
**Next Steps**:
1. Implement database models for contracts and summaries
2. Create vector store utilities for OpenSearch integration
3. Connect tools to actual data sources
4. Add proper error handling and validation

## Notes for AI Agents
- **Architecture**: Next.js frontend + FastAPI backend + OpenSearch + PostgreSQL + DynamoDB
- **Settings Management**: Centralized Pydantic settings in `src/contramate/utils/settings/core.py`
- **Environment Loading**: Automatic loading from `.envs/local.env` or system environment
- **Status Services**: Working connection checks for all databases accessible via API endpoints
- **Entry Points**:
  - Backend: `src/contramate/api/main.py`
  - Settings: `src/contramate/utils/settings/core.py`
  - AI Clients: `src/contramate/utils/clients/ai/`
  - Agents: `src/contramate/core/agents/`
  - Frontend: Next.js app in `frontend/` directory
  - Environment: `.envs/local.env`
- **Development**: All services containerized with uv-optimized builds, security disabled for local development
- **API Endpoints**:
  - `/api/postgres/status` - PostgreSQL connection status
  - `/api/opensearch/status` - OpenSearch cluster health
  - `/api/dynamodb/status` - DynamoDB connection status
- **AI Client Usage**: Import from `contramate.utils.clients.ai` - all clients support both OpenAI and Azure OpenAI
- **Agent Integration**: Agents work with any chat client via unified interface
- **Tool System**: LLM-powered tool selection and execution for contract understanding
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