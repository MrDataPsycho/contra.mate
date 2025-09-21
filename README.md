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