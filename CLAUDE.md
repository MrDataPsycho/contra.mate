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
- The Frontend is a Next.js application located in `frontend/` directory, TypeScript Next.js 15 starter template for AI-powered 


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

- This project strictly uses **pnpm**. Do not use npm or yarn.
- Python uses uv package manager.

# Project Guidiles in General
- Do not create any description file like md during the code generation unless specifically asked for.

# Project Guidelines for Python
- Do use relative imports in python always use contramate as the root package.
- When ever possible if the modules are imported to another module first reimport them in the module level __init__.py file and then import from the package. For example: if you want to import `DynamoDBConversationAdapter` from `src/contramate/dbs/adapters/dynamodb_conversation.py` first import it in `src/contramate/dbs/adapters/__init__.py` and then import it from `contramate.dbs. 
- Do not reimport interfaces import them from root package.


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
- Configured for GPT-5 or GPT 4.1 via OpenAI provider
- API route at `/api/chat` expects `{ message: string }` and returns `{ response: string }` in the frontend for Testing Purpose
- Requires `OPENAI_API_KEY` in `.env.local` in the frontend directory

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

### Build and Run Commands
```bash
# Run backend locally (development)
uv run uvicorn src.contramate.api.main:app --host 0.0.0.0 --port 8000 --reload

# Run frontend locally (development)
cd frontend && pnpm dev

# Run full stack with Docker Compose
docker-compose up
```

### All access points:
  - Frontend (Next.js): http://localhost:3000
  - Backend API: http://localhost:8000
  - OpenSearch Dashboards: http://localhost:5601
  - OpenSearch API: http://localhost:9200

## AI Client System

### Client Architecture
**Location**: `src/contramate/utils/clients/ai/`

The project implements a comprehensive AI client system with support for multiple providers and both chat and embedding capabilities:

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
