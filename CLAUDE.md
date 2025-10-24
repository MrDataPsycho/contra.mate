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
- Never import inside of a function rather at the root
- Always use logger from loguru and do not add logger into the class like self.logger = logger rather use the loguru logger from import

## Message History Conversion Standard

When working with agents that accept conversation history, always use the `MessageHistory` model for conversion:

```python
from contramate.models import MessageHistory

# Build conversation history
message_dicts = [
    {
        "role": "user",
        "content": "What are the key details of this contract?",
        "timestamp": "2024-10-01T12:00:00Z"
    },
    {
        "role": "assistant",
        "content": "The contract is between..."
    },
]

# Convert to pydantic-ai format
message_history = MessageHistory.model_validate({"messages": message_dicts})
pydantic_messages = message_history.to_pydantic_ai_messages()

# Use with agent
result = await agent.run(user_query, message_history=pydantic_messages)
```

**Important**:
- Always use `MessageHistory.model_validate()` to create the history object
- Always call `.to_pydantic_ai_messages()` to convert to pydantic-ai format
- Pass the converted messages to `agent.run()` via the `message_history` parameter
- This ensures consistency across all agents in the system

## Agent Factory Pattern

All agents follow a consistent factory pattern for creation:

```python
class MyAgentFactory:
    """Factory for creating MyAgent instances."""

    @staticmethod
    def create_default() -> Agent:
        """Create agent with default settings from environment."""
        model, model_settings = PyadanticAIModelUtilsFactory.create_default()
        # ... create and configure agent
        return agent

    @staticmethod
    def from_env_file(env_path: str) -> Agent:
        """Create agent from specific environment file."""
        model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path)
        # ... create and configure agent
        return agent
```

**Important**:
- Always use `create_default()` and `from_env_file()` as factory method names
- Do NOT create convenience functions like `create_my_agent()` - use the factory directly
- Use `PyadanticAIModelUtilsFactory` to get model and settings
- Register tools via `_register_tools(agent)` helper function if needed
- Use `deps_type` parameter to specify dependencies for agents that need context

## Terminal Usage Guideline
- If docker any service is not working, try /bin/zsh -il -c as terminal.


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
**Location**: `src/contramate/llm/`

The project implements a comprehensive AI client system with support for multiple providers and both chat and embedding capabilities:

#### Client Features
- **Unified Interface**: All clients inherit from `BaseChatClient` or `BaseEmbeddingClient`
- **Native OpenAI Responses**: Returns native OpenAI SDK objects (not custom wrappers)
- **Sync/Async Support**: Both synchronous and asynchronous operations
- **Tool Calling**: Function calling capabilities for agent interactions via `select_tool()` method
- **Vanilla Clients**: Auto-selection based on environment configuration
- **No Singletons**: Dependency injection pattern throughout
- **Backward Compatibility**: Simplified `chat()` method for existing agent code

#### Quick Start - LLMVanillaClientFactory (Recommended for Pure OpenAI SDK)

```python
from contramate.llm import LLMVanillaClientFactory
import asyncio

# Create factory (auto-selects based on APP_LLM_PROVIDER)
factory = LLMVanillaClientFactory()

# Get sync client - ONE client for BOTH chat and embeddings!
client = factory.get_default_client(async_mode=False)

# Chat completion
chat_response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
print(chat_response.choices[0].message.content)

# Embeddings (same client!)
embed_response = client.embeddings.create(
    model="text-embedding-3-small",
    input="Hello world"
)
print(embed_response.data[0].embedding[:5])

# Get async client
async_client = factory.get_default_client(async_mode=True)

async def example():
    # Chat
    response = await async_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello async!"}]
    )
    print(response.choices[0].message.content)

    # Embeddings (same client!)
    embeddings = await async_client.embeddings.create(
        model="text-embedding-3-small",
        input="Async embeddings"
    )
    print(embeddings.data[0].embedding[:5])

asyncio.run(example())

# Explicitly specify provider
factory_openai = LLMVanillaClientFactory(provider="openai")
factory_azure = LLMVanillaClientFactory(provider="azure_openai")
```

#### Alternative - Wrapper Clients (Simplified API)
```python
from contramate.llm import create_vanilla_chat_client, create_vanilla_embedding_client
import asyncio

# Set APP_LLM_PROVIDER=openai or APP_LLM_PROVIDER=azure_openai in .env

# Chat client - auto-selects based on APP_LLM_PROVIDER
# Single client supports BOTH sync and async operations!
client = create_vanilla_chat_client()

# Synchronous usage
response = client.chat_completion([{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)

# Asynchronous usage (same client!)
async def async_example():
    async_response = await client.async_chat_completion([{"role": "user", "content": "Hello"}])
    print(async_response.choices[0].message.content)

asyncio.run(async_example())

# Embedding client - also supports both sync and async
embed_client = create_vanilla_embedding_client()

# Sync
embeddings = embed_client.create_embeddings("Hello world")
print(embeddings.data[0].embedding)

# Async (same client!)
async def async_embed():
    async_embeddings = await embed_client.async_create_embeddings("Hello world")
    print(async_embeddings.data[0].embedding)

asyncio.run(async_embed())
```

#### Authentication Methods
- **OpenAI**: API key-based authentication via `OPENAI_API_KEY`
- **Azure OpenAI**: Multiple auth options (priority order):
  1. Certificate-based via `AOAICertSettings` object
  2. Custom Azure AD token provider
  3. API key authentication

#### Client Creation Methods
1. **Vanilla Client** (Recommended): `create_vanilla_chat_client()` - Auto-selects based on `APP_LLM_PROVIDER`
2. **Explicit Selection**: `create_default_chat_client(client_type="openai")` or `client_type="azure_openai"`
3. **Direct Instantiation**: `OpenAIChatClient(...)` or `AzureOpenAIChatClient(...)` for custom config

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
- **AI Client System**:
  - Full implementation with OpenAI and Azure OpenAI support
  - Native OpenAI response objects (no custom wrappers)
  - Vanilla client creation with auto-provider selection
  - Multiple authentication methods for Azure OpenAI
  - Factory pattern with dependency injection (no singletons)
  - Loguru logging throughout
- **Agent Framework**: All four agents implemented with tool calling capabilities
- **Settings System**: Complete configuration management with Azure support and factory pattern
- **Tool Infrastructure**: Function calling framework ready for tool execution
- **Docker & Dependencies**: All dependencies properly configured

#### Environment Configuration
```bash
# Required: Choose your LLM provider
APP_LLM_PROVIDER=openai  # or "azure_openai"

# For OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# For Azure OpenAI (if using certificate auth)
AZURE_OPENAI_TENANT_ID=...
AZURE_OPENAI_CLIENT_ID=...
AZURE_OPENAI_AZURE_ENDPOINT=...
AZURE_OPENAI_MODEL=gpt-4
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
# Plus certificate keys...
```

#### 🚧 In Progress / Pending
- **Database Models**: Contract metadata and summary models need implementation
- **Vector Store Integration**: OpenSearch connection and embedding storage
- **Tool Implementations**: Actual database queries and vector search functionality
- **Frontend Integration**: Agent system integration with Next.js interface
