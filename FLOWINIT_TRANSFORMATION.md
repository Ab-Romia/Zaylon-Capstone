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

### 🔄 Phase 2: The Agentic Core (IN PROGRESS)

**Goal**: Build the Supervisor and Sub-agents using LangGraph

#### Tasks Remaining:

1. **Create `app/agents/graph.py`**
   - Define State Schema (messages, customer_id, facts, context)
   - Build LangGraph workflow

2. **Supervisor Node** (Router)
   - LLM-based routing decision
   - Routes to either Sales or Support agent
   - Input: customer message + context
   - Output: `Next: sales` or `Next: support`

3. **Sales Agent Node**
   - Has access to: SALES_TOOLS (6 tools)
   - Handles: Orders, product inquiries, purchase intent
   - Can create orders, check availability, get pricing

4. **Support Agent Node**
   - Has access to: SUPPORT_TOOLS (4 tools)
   - Handles: FAQs, policies, general questions, order status
   - Implements SELF-CORRECTION loop (already in semantic_product_search_tool)

5. **Memory Node**
   - Runs after agent response
   - Extracts facts from conversation
   - Saves to Memory Bank using memory_tools

6. **Graph Flow**:
   ```
   START → Load Memory → Supervisor → [Sales Agent | Support Agent] → Memory Node → END
   ```

---

### 📝 Phase 3: API Integration (PENDING)

**Goal**: Expose the agent via `/api/v2/agent/invoke`

#### Tasks:

1. Create new API route (`routes/agent.py`)
2. Define request/response models for v2 API
3. Integrate LangGraph compiled graph
4. Add Chain-of-Thought logging to analytics
5. Keep v1 endpoints functional (backward compatibility)

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
│   └── agents/                🔄 (Next)
│       ├── __init__.py
│       ├── state.py
│       ├── nodes.py
│       └── graph.py
├── migrations/
│   └── 001_add_customer_facts_table.sql  ✅
├── tests/
│   └── evaluation/            📝 (Phase 4)
│       ├── golden_dataset.csv
│       ├── run_eval.py
│       └── report.md
└── routes/
    └── agent.py               📝 (Phase 3)
```

---

## Success Criteria (From Requirements)

- [ ] Agent handles complex mixed-intent queries
- [ ] Memory Bank retrieves "Size M" preference automatically
- [ ] RAG self-correction retries poor searches
- [ ] Evaluation report shows >70% accuracy
- [ ] Chain-of-Thought logging in database
- [ ] Backward compatibility with v1 API

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

**Last Updated**: 2024 (Phase 1 Completion)
**Next Milestone**: Phase 2 - LangGraph Agent Implementation
**Estimated Time**: 4-6 hours for Phase 2
