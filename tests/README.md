# Flowinit Agent Tests

## Overview

This directory contains test suites for the Flowinit agentic system.

## Test Files

### `manual_test_graph.py`

Manual verification script for the LangGraph implementation.

**Tests Included:**
1. **Graph Structure** - Verifies all nodes are present
2. **Basic Sales Flow** - Tests sales agent routing
3. **Support Flow** - Tests support agent routing
4. **Mixed Intent** - Tests complex multi-intent routing
5. **Memory Persistence** - Tests Memory Bank across interactions

**Usage:**
```bash
# Set OpenAI API key
export OPENAI_API_KEY='your-key-here'

# Run tests
python -m tests.manual_test_graph
```

**Expected Output:**
```
TEST SUMMARY
================================
Total Tests: 5
Passed: 5
Failed: 0
Success Rate: 100.0%

🎉 ALL TESTS PASSED!
```

## Test Cases

### Test 1: Basic Sales Flow
- **Input**: "I want to buy a red hoodie in size M"
- **Expected**: Routes to Sales Agent
- **Verifies**:
  - Memory load runs
  - Supervisor routes correctly
  - Sales agent uses tools
  - Memory save runs

### Test 2: Support Flow
- **Input**: "What is your return policy?"
- **Expected**: Routes to Support Agent
- **Verifies**:
  - Support agent handles FAQ queries
  - Knowledge base tool invoked

### Test 3: Memory Persistence
- **Interaction 1**: "I wear size M and I love blue"
- **Interaction 2**: "Show me hoodies"
- **Expected**: Second interaction loads size preference
- **Verifies**:
  - Facts extracted and saved
  - Facts loaded in subsequent interaction

### Test 4: Mixed Intent
- **Input**: "I want to return my last order and buy a new red hoodie"
- **Expected**: Routes to Sales (handles both)
- **Verifies**:
  - Supervisor handles complex intents
  - Routes appropriately for mixed scenarios

### Test 5: Graph Structure
- **Verifies**: All nodes present in graph
- **Nodes**:
  - load_memory
  - supervisor
  - sales_agent
  - support_agent
  - save_memory

## Requirements

- OpenAI API key in environment
- Database connection configured
- All Phase 1 & 2 implementations complete

## Future Tests

- `evaluation/` - Golden dataset evaluation (Phase 4)
- Unit tests for individual tools
- Integration tests for API endpoints
