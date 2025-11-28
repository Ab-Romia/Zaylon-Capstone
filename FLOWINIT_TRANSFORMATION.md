# Flowinit AI Microservices Transformation

## Project Overview

Transforming the AI_Microservices project from a simple automation system into a **Hierarchical Multi-Agent Architecture** using LangGraph for the AI Engineering Capstone project.

---

## Progress Status

### ✅ Phase 1: Infrastructure & Tooling (COMPLETED)

#### What Was Built:

1. **Tool Wrappers (app/tools/)**
   - Created LangChain-compatible wrappers around existing services
   - Total: 10 tools across 4 categories

2. **Products Tools** (`products_tools.py`)
   - `search_products_tool`: Multilingual product search
   - `get_product_details_tool`: Detailed product information by ID
   - `check_product_availability_tool`: Stock/variant checking

3. **Orders Tools** (`orders_tools.py`)
   - `create_order_tool`: Complete order creation with validation
   - `get_order_history_tool`: Customer order history retrieval
   - `check_order_status_tool`: Order status tracking

4. **RAG Tools** (`rag_tools.py`)
   - `search_knowledge_base_tool`: Semantic FAQ/policy search
   - `semantic_product_search_tool`: Vector-based product search with **SELF-CORRECTION**
     - Automatically rewrites queries if first attempt yields poor results
     - Implements retry logic with similarity threshold checking

5. **Memory Tools** (`memory_tools.py`)
   - `get_customer_facts_tool`: Retrieve stored customer preferences
   - `save_customer_fact_tool`: Store long-term customer facts

6. **Database Schema Extension**
   - Added `CustomerFact` model to `database.py`
   - Created migration `001_add_customer_facts_table.sql`
   - Indexes: customer_id, (customer_id, fact_key), fact_type

7. **Dependencies Updated**
   - Added LangChain 0.1.0
   - Added LangGraph 0.0.20
   - Added LangSmith 0.0.80 (for observability)
   - Added pandas 2.1.4 (for evaluation)
   - Added pytest & pytest-asyncio

---

### ✅ Phase 2: The Agentic Core (COMPLETED)

**Goal**: Build the Supervisor and Sub-agents using LangGraph

#### What Was Built:

1. **State Schema** (`app/agents/state.py`) ✅
   - `FlowinitState` TypedDict with:
     - messages: Conversation history
     - customer_id & channel: Customer context
     - user_profile: Long-term memory
     - next: Routing decision
     - chain_of_thought: Observability logging
     - tool_calls: Tool invocation tracking
   - AgentType and NodeName constants for type safety

2. **Agent Nodes** (`app/agents/nodes.py`) ✅
   - **load_memory_node**: Loads customer facts using get_customer_facts_tool
   - **supervisor_node**: LLM-based router with structured prompts
     - Routes to Sales or Support based on intent analysis
     - Uses user profile for personalization
     - Safe default to Support on errors
   - **sales_agent_node**: Sales specialist with 6 tools
     - Handles orders, products, purchases
     - Tool-bound LLM agent
   - **support_agent_node**: Support specialist with 4 tools
     - Handles FAQs, policies, tracking
     - RAG with self-correction built-in
   - **save_memory_node**: Fact extraction and storage
     - Uses LLM to extract preferences/constraints
     - Saves to Memory Bank automatically

3. **Graph Assembly** (`app/agents/graph.py`) ✅
   - LangGraph StateGraph with conditional routing
   - Flow: START → Load Memory → Supervisor → [Sales | Support] → Save Memory → END
   - MemorySaver for conversation persistence
   - Convenient `invoke_agent()` and `stream_agent()` wrappers

4. **Test Suite** (`tests/manual_test_graph.py`) ✅
   - 5 comprehensive test cases:
     - Graph structure verification
     - Basic sales flow
     - Support flow
     - Mixed intent handling
     - Memory persistence across interactions
   - Assertions for node execution order
   - Tool call verification

---

### ✅ Phase 3: API Integration (COMPLETED)

**Goal**: Expose the agent via `/api/v2/agent/invoke`

#### What Was Built:

1. **Request/Response Models** (`models.py`) ✅
   - `AgentInvokeRequest`: customer_id, message, channel, thread_id
   - `AgentInvokeResponse`: success, response, agent_used, chain_of_thought, tool_calls, user_profile, execution_time_ms
   - `AgentThought`: node name + reasoning step
   - `AgentToolCall`: tool_name, arguments, result, success
   - `AgentStreamChunk`: For real-time streaming updates

2. **Agent API Router** (`routes/agent.py`) ✅
   - **POST `/api/v2/agent/invoke`**: Main agent invocation endpoint
     - Rate limited with API key authentication
     - Full integration with flowinit_graph
     - Comprehensive error handling
     - Response includes chain of thought and tool calls
   - **POST `/api/v2/agent/stream`**: Real-time streaming endpoint
     - Server-Sent Events (SSE) format
     - Streams thoughts, tool calls, and responses
     - Useful for interactive UIs

3. **Analytics Integration** ✅
   - Added new event types to `core/enums.py`:
     - `AGENT_INVOKED`: Tracks every agent call
     - `AGENT_ROUTED`: Logs routing decisions
     - `MEMORY_LOADED`: Memory Bank reads
     - `MEMORY_SAVED`: Memory Bank writes
   - Chain-of-Thought logging in analytics events
   - Tool usage tracking (tool names, success rates)
   - Execution time monitoring

4. **Main App Integration** (`main.py`) ✅
   - Added agent_router to FastAPI app
   - Backward compatibility maintained (v1 endpoints unchanged)

5. **Test Suite** (`tests/test_agent_api.py`) ✅
   - HTTP-based tests using httpx
   - Tests all three scenarios:
     - Sales flow (product inquiry)
     - Support flow (order tracking)
     - Memory persistence (follow-up messages)
   - Streaming endpoint validation

---

### 🧪 Phase 4: Evaluation & Hardening (PENDING)

**Goal**: Prove the agent works with quantitative metrics

#### Tasks:

1. **Golden Dataset** (`tests/evaluation/golden_dataset.csv`)
   - Create 20-30 test cases
   - Columns: input_message, expected_intent, expected_action, context
   - Mix of simple and complex scenarios

2. **Evaluation Runner** (`tests/evaluation/run_eval.py`)
   - Load golden dataset
   - Run agent against each test case
   - Use LLM-as-judge to score responses (1-5)
   - Calculate metrics: Accuracy, Avg Score, Intent Match Rate

3. **Generate Report** (`tests/evaluation/report.md`)
   - Quantitative results
   - Failure analysis
   - Recommendations

---

## Key Design Decisions

### Tool Architecture
- All tools return JSON strings (LLM-friendly)
- Comprehensive docstrings for LLM understanding
- Error handling with structured responses
- Self-correction built into RAG tool

### Memory Bank Strategy
- Facts stored with confidence scores (0-100)
- Source tracking: "explicit" vs "inferred"
- Fact types: preference, constraint, personal_info
- Automatic updates on duplicate keys

### Self-Correction Implementation
- Semantic search checks similarity scores
- If avg_similarity < 0.7, query is rewritten
- Extraction of keywords, colors, garment types
- Comparison of original vs corrected results

---

## Next Steps

### To Continue Phase 2:

1. Create `app/agents/__init__.py`
2. Create `app/agents/state.py` (State Schema)
3. Create `app/agents/nodes.py` (Supervisor, Sales, Support, Memory nodes)
4. Create `app/agents/graph.py` (LangGraph workflow assembly)
5. Test with sample inputs

### Example Agent Flow:

**Input**: "I want to return my last order and buy a new red hoodie in size M"

**Expected Flow**:
1. Memory Node loads facts: "preferred_size=M"
2. Supervisor analyzes: Mixed intent (Support + Sales)
3. Route to Support: Check order history
4. Support finds last order
5. Route to Sales: Search for red hoodies
6. Sales finds products, checks size M availability
7. Generate unified response
8. Memory Node saves: "recently_browsed=red_hoodie"

---

## Architecture Comparison

### Before (v1 - Automation)
```
n8n Webhook → API → Intent Service → Product Service → n8n Logic → Response
```

### After (v2 - Agentic)
```
API v2 → LangGraph
  ├─ Supervisor (LLM Router)
  ├─ Sales Agent (Tools: Orders, Products)
  ├─ Support Agent (Tools: RAG, KB Search)
  └─ Memory Node (Fact Extraction)
  → Response with CoT logging
```

---

## File Structure

```
AI_Microservices/
├── app/
│   ├── __init__.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── products_tools.py  ✅
│   │   ├── orders_tools.py    ✅
│   │   ├── rag_tools.py       ✅
│   │   └── memory_tools.py    ✅
│   └── agents/                ✅
│       ├── __init__.py        ✅
│       ├── state.py           ✅
│       ├── nodes.py           ✅
│       └── graph.py           ✅
├── migrations/
│   └── 001_add_customer_facts_table.sql  ✅
├── tests/
│   ├── manual_test_graph.py   ✅ (Phase 2)
│   ├── test_agent_api.py      ✅ (Phase 3)
│   └── evaluation/            📝 (Phase 4)
│       ├── golden_dataset.csv
│       ├── run_eval.py
│       └── report.md
├── routes/
│   └── agent.py               ✅ (Phase 3)
├── models.py                  ✅ (Agent models added)
└── core/
    └── enums.py               ✅ (Agent events added)
```

---

## Success Criteria (From Requirements)

- [x] **Phase 1**: Tools created with self-correction in RAG ✅
- [x] **Phase 1**: Memory Bank database schema created ✅
- [x] **Phase 2**: Agent handles complex mixed-intent queries ✅
- [x] **Phase 2**: Memory Bank retrieves preferences automatically ✅
- [x] **Phase 3**: Chain-of-Thought logging in database ✅
- [x] **Phase 3**: Backward compatibility with v1 API ✅
- [ ] **Phase 4**: Evaluation report shows >70% accuracy

---

## Technical Notes

### LangGraph State Schema (Proposed)
```python
from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    customer_id: str
    channel: str
    customer_facts: Dict[str, Any]
    conversation_history: str
    current_agent: str  # "supervisor", "sales", "support"
    final_response: str
    chain_of_thought: List[str]
```

### Supervisor Prompt (Proposed)
```
You are a routing agent for an e-commerce chatbot. Analyze the customer's message
and decide which agent should handle it:

- **Sales Agent**: Orders, purchases, product availability, pricing
- **Support Agent**: FAQs, policies, returns, general questions, order tracking

Customer Message: {message}
Customer Facts: {facts}
Recent Context: {context}

Output your decision as: "Next: sales" or "Next: support"
```

---

## Deployment Considerations

- Database migration must be run on Supabase
- Environment variable: `OPENAI_API_KEY` required for LangGraph
- Optional: `LANGSMITH_API_KEY` for tracing
- Backward compatibility: v1 endpoints remain operational
- Render deployment: Single worker (async session constraints)

---

## Questions for Clarification

1. Should the supervisor be able to route to BOTH agents sequentially?
2. Preference for LLM: GPT-4 or GPT-3.5-turbo for cost?
3. Should evaluation use same LLM or separate judge model?
4. Memory Bank: Should we implement automatic fact expiration (TTL)?

---

**Last Updated**: 2025-11-26 (Phase 3 Completion)
**Current Status**: Phase 1, 2 & 3 Complete ✅
**Next Milestone**: Phase 4 - Evaluation & Hardening
**Estimated Time**: 3-4 hours for Phase 4

---

## Phase 3 Implementation Details

### API Endpoints

**1. POST `/api/v2/agent/invoke`**

Main endpoint for synchronous agent invocation.

**Request**:
```json
{
  "customer_id": "instagram:@username",
  "message": "I want to buy a red hoodie in size L",
  "channel": "instagram",
  "thread_id": "optional-thread-id"
}
```

**Response**:
```json
{
  "success": true,
  "response": "I found several red hoodies in size L...",
  "agent_used": "sales",
  "chain_of_thought": [
    {
      "node": "load_memory",
      "reasoning": "Loading customer preferences...",
      "timestamp": "2025-11-26T10:30:00Z"
    },
    {
      "node": "supervisor",
      "reasoning": "Customer wants to buy - routing to Sales",
      "timestamp": "2025-11-26T10:30:01Z"
    }
  ],
  "tool_calls": [
    {
      "tool_name": "search_products_tool",
      "arguments": {"query": "red hoodie", "limit": 5},
      "result": "Found 3 products",
      "success": true
    }
  ],
  "user_profile": {
    "preferred_size": "L",
    "favorite_color": "blue"
  },
  "execution_time_ms": 2340,
  "thread_id": "uuid-here"
}
```

**2. POST `/api/v2/agent/stream`**

Streaming endpoint for real-time updates using Server-Sent Events.

**Request**: Same as invoke endpoint

**Response**: SSE stream with chunks:
```
data: {"type": "thought", "node": "supervisor", "content": "Analyzing intent...", "done": false}

data: {"type": "tool_call", "tool_name": "search_products_tool", "content": "Calling tool...", "done": false}

data: {"type": "response", "content": "I found several red hoodies...", "done": false}

data: {"type": "final", "content": "Agent execution complete", "done": true}
```

### Chain-of-Thought Analytics

Every agent invocation logs comprehensive data to the analytics database:

```python
{
  "event_type": "agent_invoked",
  "event_data": {
    "success": true,
    "agent_used": "sales",
    "channel": "instagram",
    "message_preview": "I want to buy a red hoodie...",
    "response_preview": "I found several red hoodies...",
    "chain_of_thought": [
      {"node": "supervisor", "reasoning": "Routing to Sales"},
      {"node": "sales_agent", "reasoning": "Searching products"}
    ],
    "tool_calls_count": 2,
    "tools_used": ["search_products_tool", "check_product_availability_tool"]
  },
  "response_time_ms": 2340
}
```

This enables:
- **Observability**: Track agent reasoning paths
- **Debugging**: Identify where agents fail
- **Optimization**: Find bottlenecks in tool calls
- **Analytics**: Understand which agents/tools are most used

### Testing Phase 3

**Running API Tests**:

```bash
# 1. Start the server
uvicorn main:app --reload

# 2. In another terminal, run tests
python tests/test_agent_api.py
```

**Expected Output**:
```
================================================================================
TEST: Agent Invoke Endpoint
================================================================================

[Test 1] Sales Flow - Product Inquiry
--------------------------------------------------------------------------------
Status Code: 200
✓ Success: True
✓ Agent Used: sales
✓ Execution Time: 2340ms
✓ Response Preview: I found several red hoodies in size L...
✓ Chain of Thought Steps: 4
✓ Tool Calls: 2

[Test 2] Support Flow - Order Status Inquiry
--------------------------------------------------------------------------------
✓ Agent Used: support

[Test 3] Memory Persistence - Follow-up Message
--------------------------------------------------------------------------------
✓ Memory appears to be working (response mentions preferences)
```

### Integration with Existing System

**Backward Compatibility**:
- All v1 endpoints remain unchanged
- n8n workflows continue to work
- v2 API is completely separate
- No breaking changes to existing functionality

**Migration Path**:
- Clients can gradually move from v1 to v2
- Both APIs can run simultaneously
- v2 offers richer responses with agent reasoning

---

## Phase 2 Implementation Details

### How the Agent System Works

**Example Execution Flow**:

```
User: "I want to buy a red hoodie in size M"

1. load_memory_node:
   - Calls get_customer_facts_tool(customer_id)
   - Loads: {"preferred_size": "M", "favorite_color": "blue"}
   - Updates state.user_profile

2. supervisor_node:
   - Analyzes: "buy a red hoodie"
   - Context: User prefers size M
   - Decision: Route to SALES (buying intent)
   - Updates state.next = "sales"

3. sales_agent_node:
   - System prompt includes user profile
   - Calls search_products_tool("red hoodie")
   - Calls check_product_availability_tool(size="M")
   - Generates response with product recommendations
   - Updates state.final_response

4. save_memory_node:
   - Analyzes conversation
   - Extracts: "recently_browsed=red_hoodie"
   - Calls save_customer_fact_tool to store
   - Logs fact extraction

Result: Complete, personalized response with memory persistence
```

### Supervisor Routing Logic

The supervisor uses a carefully crafted prompt that:
- Analyzes the customer's message
- Considers their profile (preferences, history)
- Routes to the appropriate specialist
- Defaults to Support for ambiguous cases
- Handles mixed intent by routing to Sales (can do both)

### Memory Extraction

The save_memory_node uses an LLM to extract facts:
- **Explicit facts**: User directly states ("I wear size M")
  - Confidence: 100
  - Source: "explicit"
- **Inferred facts**: Agent deduces from context
  - Confidence: 70-90
  - Source: "inferred"

Facts are categorized:
- **preference**: Likes, favorites, usual choices
- **constraint**: Budget limits, delivery requirements
- **personal_info**: Address updates, contact changes

---

## Testing Phase 2

### Running the Test Suite

```bash
# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'

# Run all tests
python -m tests.manual_test_graph
```

### Expected Results

All 5 tests should pass:
- ✓ Graph Structure (nodes present)
- ✓ Basic Sales Flow (routing works)
- ✓ Support Flow (knowledge base accessed)
- ✓ Mixed Intent (handled correctly)
- ✓ Memory Persistence (facts saved & loaded)

### Test Output Example

```
TEST SUMMARY
================================
Total Tests: 5
Passed: 5
Failed: 0
Success Rate: 100.0%

🎉 ALL TESTS PASSED!
```
