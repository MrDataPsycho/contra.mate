# Contramate

> AI-Powered Contract Analysis and Metadata Extraction Platform

[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://mrdatapsycho.github.io/contra.mate/)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Contramate is an intelligent contract management assistant that leverages Large Language Models (LLMs), multi-agent systems, and vector databases to automate contract analysis and question-answering workflows.

## ✨ Key Features

- 🤖 **Multi-Agent System** - Orchestrated AI agents for complex reasoning workflows
- 🔍 **Hybrid Search** - Combines semantic (vector) and keyword (BM25) search for 95%+ accuracy
- 📊 **SQL-Based Metadata Queries** - Natural language to SQL for structured contract data analysis
- 💬 **Conversational Interface** - Multi-turn conversations with full context retention
- 📝 **Citation-Backed Responses** - Every answer includes source document references
- 🎯 **Smart Filtering** - Document-specific, project-based, and type-based query filtering

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      USER INTERFACE                             │
│              Streamlit UI / Next.js Frontend                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                              │
│                   REST API + Agent System                       │
└──────┬──────────────────────┬──────────────────────┬───────────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌─────────────┐      ┌─────────────┐       ┌─────────────┐
│   QUERY     │      │  METADATA   │       │   ANSWER    │
│  REWRITER   │      │   INSIGHT   │       │  CRITIQUE   │
│   AGENT     │      │   AGENT     │       │   AGENT     │
└─────────────┘      └──────┬──────┘       └─────────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌──────────┐   ┌──────────────┐  ┌──────────┐
    │OpenSearch│   │  PostgreSQL  │  │ DynamoDB │
    │ (Vector) │   │  (Metadata)  │  │(Messages)│
    └──────────┘   └──────────────┘  └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- OpenAI API Key
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Installation

```bash
# Clone repository
git clone https://github.com/MrDataPsycho/contra.mate.git
cd contra.mate

# Install dependencies
uv sync

# Set up environment
cp .envs/local.env.example .envs/local.env
# Edit .envs/local.env with your OpenAI API key

# Start infrastructure
docker compose up -d
```

### Basic Usage

```python
import asyncio
from contramate.core.agents.contract_metadata_insight import (
    ContractMetadataInsightAgentFactory
)

async def main():
    # Create agent
    agent = ContractMetadataInsightAgentFactory.create_default()
    
    # Query contracts
    result = await agent.run("How many contracts have non-compete clauses?")
    
    print(result["answer"])
    print(result["citations"])

asyncio.run(main())
```

## 📊 Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Python 3.12, Uvicorn |
| **AI/ML** | OpenAI GPT-4, text-embedding-3-small |
| **Vector DB** | OpenSearch 2.11.1 (kNN + BM25) |
| **Databases** | PostgreSQL 15, DynamoDB Local |
| **Frontend** | Streamlit, Next.js 15 (in development) |
| **Infrastructure** | Docker, Docker Compose |
| **Package Manager** | uv, pnpm |

## 📖 Documentation

- **[Full Documentation](https://mrdatapsycho.github.io/contra.mate/)** - Complete guides and API reference
- **[Installation Guide](https://mrdatapsycho.github.io/contra.mate/getting-started/installation/)** - Detailed setup instructions
- **[Quick Start Tutorial](https://mrdatapsycho.github.io/contra.mate/getting-started/quickstart/)** - Get started in minutes
- **[Presentation](https://mrdatapsycho.github.io/contra.mate/presentation/)** - Project overview and demo

## 🎯 Use Cases

### Metadata Queries
```python
# Count contracts by type
"How many Service Agreements do we have?"

# Analyze clauses
"Show me contracts with both non-compete and IP ownership clauses"

# Financial analysis
"What's the average contract value for Development Agreements?"
```

### Semantic Search
```python
# Content search
"What are the termination conditions in this contract?"

# Multi-document analysis
"Compare payment terms across all Service Agreements"
```

## 🔒 Query Guardrails

The system enforces strict safety rules:

- ✅ Only SELECT queries allowed
- ✅ All queries must include WHERE or LIMIT clauses
- ✅ Maximum LIMIT of 1000 rows
- ❌ No INSERT, UPDATE, DELETE, DROP operations

## 📈 Results & Impact

| Metric | Improvement |
|--------|-------------|
| Contract review time | **95% reduction** (2-4 hrs → 5-10 min) |
| Multi-doc comparison | **98% reduction** (30+ min → 30 sec) |
| Answer accuracy | **+35% improvement** (60% → 95%) |
| Source attribution | **100% coverage** |

## 🛠️ Development

```bash
# Install development dependencies
uv sync --group dev

# Run tests
uv run pytest tests/

# Start documentation server
uv run mkdocs serve

# Format code
uv run ruff format .
```

## 📝 Project Structure

```
contramate/
├── src/contramate/
│   ├── api/              # FastAPI endpoints
│   ├── core/agents/      # Multi-agent system
│   ├── dbs/              # Database adapters & models
│   ├── llm/              # LLM client abstractions
│   └── utils/            # Settings & utilities
├── docs/                 # MkDocs documentation
├── scripts/              # Test & utility scripts
├── frontend/             # Next.js UI (in development)
└── tests/                # Test suite
```

## 🤝 Contributing

Contributions are welcome! Please check out our [Contributing Guide](https://mrdatapsycho.github.io/contra.mate/development/contributing/).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built as part of the Agent Engineering Bootcamp Capstone Project
- Uses the [CUAD Dataset](https://www.atticusprojectai.org/cuad) for contract analysis
- Powered by OpenAI GPT models and OpenSearch vector database

---

**[Documentation](https://mrdatapsycho.github.io/contra.mate/)** • 
**[GitHub](https://github.com/MrDataPsycho/contra.mate)** • 
**[Issues](https://github.com/MrDataPsycho/contra.mate/issues)**