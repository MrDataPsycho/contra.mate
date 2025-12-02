# Agent Refactoring Plan: Flat Agent Object with Decorator-Based Tool Registration

## Overview
Refactor `talk_to_contract.py` to use a flat agent object instead of factory classes, with tool registration using `@agent.tool` decorators directly instead of the `_register_tools()` helper function.

## Current Architecture
```
TalkToContractAgentFactory (class)
├── create_default() → creates Agent + calls _register_tools()
├── from_env_file() → creates Agent + calls _register_tools()
└── _register_tools(agent) → registers 5 tools via decorators

TalkToContractResponse (dataclass)
TalkToContractDependencies (dataclass)
```

**Pros**: Organized, factory pattern
**Cons**: Extra indirection, factory methods not always needed, tools hidden in function scope

---

## Target Architecture
```
# Module-level agent object (created immediately on import)
agent = Agent(...)  # Flat, single instance

# Tool registration directly on module level with @agent.tool decorators
@agent.tool
async def compare_filtered_documents(...): ...

@agent.tool
async def hybrid_search(...): ...

@agent.tool
async def search_by_project(...): ...

@agent.tool
async def search_similar_documents(...): ...

@agent.tool
async def search_by_document(...): ...

# Data models (unchanged)
TalkToContractResponse
TalkToContractDependencies

# Factory (optional, for convenience/backwards compatibility)
class TalkToContractAgentFactory:
    @staticmethod
    def get_agent() -> Agent[...]:
        return agent
```

**Pros**: Simpler, flatter structure, tools visible at module level, single instance
**Cons**: Module-level initialization, must handle imports carefully

---

## Step-by-Step Implementation Plan

### Phase 1: Setup & Preparation
1. ✅ Create this plan document
2. [ ] Analyze current code structure
3. [ ] Identify dependencies and import order requirements

### Phase 2: Create Module-Level Agent
4. [ ] Move `SYSTEM_PROMPT` (stays at top, no changes)
5. [ ] Move `TalkToContractResponse` model (no changes)
6. [ ] Move `TalkToContractDependencies` dataclass (no changes)
7. [ ] Create module-level agent initialization:
   ```python
   model, model_settings = PyadanticAIModelUtilsFactory.create_default()
   
   agent = Agent(
       model=model,
       instructions=SYSTEM_PROMPT,
       output_type=TalkToContractResponse,
       model_settings=model_settings,
       deps_type=TalkToContractDependencies,
       retries=2,
   )
   ```

### Phase 3: Register Tools Directly
8. [ ] Register `compare_filtered_documents` tool
   ```python
   @agent.tool
   async def compare_filtered_documents(ctx: RunContext[...], query: str) -> Dict[str, Any]:
       ...
   ```
9. [ ] Register `hybrid_search` tool
10. [ ] Register `search_by_project` tool
11. [ ] Register `search_similar_documents` tool
12. [ ] Register `search_by_document` tool

### Phase 4: Create Factory for Backwards Compatibility (Optional)
13. [ ] Create lightweight factory:
   ```python
   class TalkToContractAgentFactory:
       @staticmethod
       def create_default() -> Agent[TalkToContractResponse, TalkToContractDependencies]:
           return agent
       
       @staticmethod
       def from_env_file(env_path: str | Path) -> Agent[...]:
           # Re-initialize from env file if needed
           ...
   ```

### Phase 5: Update Test Code
14. [ ] Update `if __name__ == "__main__"` test to use `agent` directly or via factory

### Phase 6: Validation & Testing
15. [ ] Verify all 5 tools are registered
16. [ ] Test agent runs successfully with dependencies
17. [ ] Test with and without filters
18. [ ] Ensure citations work correctly
19. [ ] Run integration tests

---

## Code Structure After Refactoring

### File Layout (Simplified View)
```python
# Imports
from loguru import logger
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, RunContext
from contramate.core.agents import PyadanticAIModelUtilsFactory
from contramate.services.opensearch_vector_search_service import (
    OpenSearchVectorSearchService,
    OpenSearchVectorSearchServiceFactory,
)

# 1. System Prompt (2000+ lines)
SYSTEM_PROMPT = """..."""

# 2. Data Models
@dataclass
class TalkToContractDependencies:
    search_service: OpenSearchVectorSearchService
    filters: Optional[Dict[str, Any]] = None

class TalkToContractResponse(BaseModel):
    answer: str = Field(...)
    citations: Dict[str, str] = Field(...)
    
    @field_validator('citations')
    @classmethod
    def validate_citations_are_strings(cls, v: Dict[str, str]) -> Dict[str, str]:
        ...

# 3. Module-Level Agent Initialization
model, model_settings = PyadanticAIModelUtilsFactory.create_default()

agent = Agent(
    model=model,
    instructions=SYSTEM_PROMPT,
    output_type=TalkToContractResponse,
    model_settings=model_settings,
    deps_type=TalkToContractDependencies,
    retries=2,
)

# 4. Tool Registration (Direct Decorators)
@agent.tool
async def compare_filtered_documents(
    ctx: RunContext,
    query: str,
) -> Dict[str, Any]:
    """..."""
    logger.info(f"🔍 Tool: compare_filtered_documents called...")
    ...

@agent.tool
async def hybrid_search(
    ctx: RunContext,
    query: str,
) -> Dict[str, Any]:
    """..."""
    logger.info(f"🔍 Tool: hybrid_search called...")
    ...

@agent.tool
async def search_by_project(
    ctx: RunContext,
    project_id: str,
    query: Optional[str] = None,
    search_type: str = "hybrid",
    size: int = 10,
) -> Dict[str, Any]:
    """..."""
    logger.info(f"🔍 Tool: search_by_project called...")
    ...

@agent.tool
async def search_similar_documents(
    ctx: RunContext,
    record_id: str,
    size: int = 5,
) -> Dict[str, Any]:
    """..."""
    logger.info(f"🔍 Tool: search_similar_documents called...")
    ...

@agent.tool
async def search_by_document(
    ctx: RunContext,
    project_id: str,
    reference_doc_id: str,
    size: Optional[int] = None,
) -> Dict[str, Any]:
    """..."""
    logger.info(f"🔍 Tool: search_by_document called...")
    ...

# 5. Factory Class (Optional, for Backwards Compatibility)
class TalkToContractAgentFactory:
    @staticmethod
    def create_default():
        """Get the module-level agent instance."""
        return agent
    
    @staticmethod
    def from_env_file(env_path: str | Path):
        """Optionally create agent from specific env file (can reuse agent or create new)."""
        # Could either:
        # Option A: Return agent (simpler)
        return agent
        
        # Option B: Create new agent from env (more flexible)
        # model, model_settings = PyadanticAIModelUtilsFactory.from_env_file(env_path)
        # ... create new agent with those settings ...

# 6. Test Code
if __name__ == "__main__":
    import asyncio

    async def test_agent():
        logger.info("=== Testing Talk To Contract Agent ===")
        search_service = OpenSearchVectorSearchServiceFactory.create_default()
        
        # Option 1: Use directly
        deps = TalkToContractDependencies(search_service=search_service)
        result = await agent.run("Your query here", deps=deps)
        
        # Option 2: Use via factory
        agent_instance = TalkToContractAgentFactory.create_default()
        result = await agent_instance.run("Your query here", deps=deps)
        
        print(result.output.answer)
        print(result.output.citations)

    asyncio.run(test_agent())
```

---

## Benefits of This Refactoring

1. **Simpler Code**
   - Removes factory class complexity
   - Direct module-level initialization
   - Tools are visible at module level

2. **Easier to Use**
   - Can import agent directly: `from talk_to_contract import agent`
   - No factory methods needed for basic usage
   - Cleaner test code

3. **Better Tool Discovery**
   - Tools defined with `@agent.tool` are visually explicit
   - IDE can find tool definitions easily
   - No hidden function scope

4. **Single Instance**
   - Guaranteed single agent per module
   - No accidental multiple instances
   - Thread-safe (agent is created at module load time)

5. **Backwards Compatibility**
   - Optional factory can still exist for existing code
   - No breaking changes if factory is kept

---

## Potential Concerns & Solutions

### Concern 1: Module-Level Initialization Order
**Problem**: Creating agent at module level requires dependencies (model, settings)
**Solution**: Dependencies are created in correct order (imports → PROMPT → models → agent init)

### Concern 2: Testing
**Problem**: Module-level agent is created once on import
**Solution**: 
- Pass different `deps` to `agent.run()` for different tests
- Use `TalkToContractDependencies` to configure filters per test

### Concern 3: Multiple Environments
**Problem**: What if different environments need different model settings?
**Solution**:
- Keep factory method that can reinitialize with different settings
- Or accept environment configuration before agent import

### Concern 4: Tool Registration Scope
**Problem**: Tools can't access closure variables if not in `_register_tools()`
**Solution**: Tools use `ctx.deps` for dependencies (correct pattern anyway)

---

## Implementation Checklist

- [ ] Create plan document (THIS FILE)
- [ ] Move system prompt to top (no changes needed)
- [ ] Move data models (no changes needed)
- [ ] Create module-level agent initialization
- [ ] Register `compare_filtered_documents` with @agent.tool
- [ ] Register `hybrid_search` with @agent.tool
- [ ] Register `search_by_project` with @agent.tool
- [ ] Register `search_similar_documents` with @agent.tool
- [ ] Register `search_by_document` with @agent.tool
- [ ] Create (optional) lightweight factory class
- [ ] Update test code in `if __name__ == "__main__"`
- [ ] Test agent functionality
- [ ] Test with single document filter
- [ ] Test with multiple document filters
- [ ] Test tool execution paths
- [ ] Verify citation validation works
- [ ] Check all tools log correctly

---

## Files to Modify

1. **src/contramate/core/agents/talk_to_contract.py**
   - Main agent file
   - Remove factory classes and `_register_tools()`
   - Add module-level agent and direct tool decorators

2. **Potentially Updated Files** (if they import the factory):
   - Search for `TalkToContractAgentFactory` imports
   - Update to use factory or import agent directly
   - Check API controllers and other consumers

---

## Success Criteria

✅ **Agent can be imported directly**:
```python
from contramate.core.agents.talk_to_contract import agent
```

✅ **All 5 tools are registered and callable**:
- `compare_filtered_documents`
- `hybrid_search`
- `search_by_project`
- `search_similar_documents`
- `search_by_document`

✅ **Agent runs successfully** with and without filters

✅ **Citations are properly validated** (Dict[str, str] with string values)

✅ **Tests pass** for all search scenarios

✅ **Code is cleaner and easier to maintain**

---

## Timeline Estimate
- Phase 1 (Setup): 5 min ✓
- Phase 2 (Module-level agent): 10 min
- Phase 3 (Tool registration): 15 min
- Phase 4 (Factory): 5 min
- Phase 5 (Tests): 10 min
- Phase 6 (Validation): 15 min
- **Total**: ~60 minutes

