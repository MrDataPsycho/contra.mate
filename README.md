# [Contra].[Mate]
A Conversational AI Agent Application to interact with CUAD (Contract Understanding Atticus Dataset) using LLM Agents, VectorDB, and workflows.

## Agent System Architecture

Contramate uses a multi-agent system for intelligent contract understanding and querying:

### Agent Components

- **Orchestrator Agent**: Main coordinator that manages the conversation flow and integrates all other agents
- **Query Rewriter Agent**: Refines and contextualizes user questions for better tool selection
- **Tool Executor Agent**: Selects and executes appropriate tools based on the query type
- **Answer Critique Agent**: Evaluates responses and suggests improvements

### Agent Orchestration Flow

```
┌─────────────────┐    ┌────────────────────┐    ┌──────────────────┐
│   User Query    │───▶│ Orchestrator Agent │───▶│ Query Rewriter   │
└─────────────────┘    └────────────────────┘    │     Agent        │
                                │                 └──────────────────┘
                                │                           │
                                ▼                           ▼
                       ┌────────────────────┐    ┌──────────────────┐
                       │ Answer Critique    │◀───│ Tool Executor    │
                       │     Agent          │    │     Agent        │
                       └────────────────────┘    └──────────────────┘
                                │                           │
                                ▼                           ▼
                       ┌────────────────────┐    ┌──────────────────┐
                       │ Final Response     │    │ Available Tools: │
                       │ Generation         │    │ • Vector Search  │
                       └────────────────────┘    │ • Summary Tool   │
                                                │ • Compare Tool   │
                                                └──────────────────┘
```

### Tool Selection System

```
User Question ──┐
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│                    Tool Executor Agent                        │
│                                                               │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │ Tool Analyzer   │───▶│ Function Caller │                  │
│  │ (LLM-powered)   │    │                 │                  │
│  └─────────────────┘    └─────────────────┘                  │
└───────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│                     Available Tools                          │
│                                                               │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐  │
│ │ Vector Retrieval│ │ Summary Getter  │ │ Contract Compare│  │
│ │ Tool            │ │ Tool            │ │ Tool            │  │
│ │                 │ │                 │ │                 │  │
│ │ • Semantic      │ │ • Get summaries │ │ • Compare       │  │
│ │   search        │ │   by CWID       │ │   contracts     │  │
│ │ • Top-K results │ │ • Short/Med/Long│ │ • Tabular view  │  │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                │
                ▼
        Tool Execution Results
```

### AI Client Support

The system supports both OpenAI and LiteLLM clients with identical interfaces:
- Standard chat completion methods
- Tool calling capabilities for function selection
- JSON mode support for structured responses
- Configurable temperature, max tokens, and other parameters

## Technology Stack

### Frontend
**Next.js with TypeScript and Tailwind CSS** provides the user interface for contract chat interactions. The frontend communicates with the backend via REST API and offers a responsive, modern web experience for contract querying and analysis.

### Backend
**FastAPI with Python 3.12** powers the main application server, handling API requests and orchestrating the multi-agent system. It uses Pydantic for data validation, SQLModel for database interactions, and supports both OpenAI and LiteLLM clients for flexible AI provider integration.

### Databases
**PostgreSQL** stores structured contract metadata, CUAD dataset information, and contract summaries. **OpenSearch** serves as the vector database for document embeddings and semantic search capabilities. **DynamoDB** manages user conversations, chat history, and workspace data for personalized experiences.

### AI Services
The system integrates with **OpenAI GPT models** and supports **LiteLLM** for multi-provider compatibility. OpenSearch Dashboards provides search analytics and visualization tools for monitoring and debugging vector search operations. **LangGraph** could be a possible to candidate for Agent and Workflow orchestration in future.

## Quick Start

### Development URLs
- **Frontend**: http://localhost:3001 (Next.js application)
- **Backend API**: http://localhost:8000 (FastAPI server)
- **OpenSearch Dashboards**: http://localhost:5601 (Search analytics)

### Running the Application
```bash
# Start all services with Docker
docker-compose up

# Or run individual services:
# Backend only
docker-compose up backend

# Frontend only (in frontend directory)
pnpm dev
```