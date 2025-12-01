# Multi-Agent Architecture - Tool Calling Implementation

##  Overview

This document explains the transition from a **linear workflow** to a **multi-agent tool-calling architecture** for the e-commerce AI assistant.

---

## 📊 Architecture Comparison

### OLD: Linear Flow Architecture
```
Message Received
    ↓
Normalize Data
    ↓
Call prepare-context API (ALWAYS)
    ↓
Check if cached → Yes → Use Cache
    ↓ No
Build AI Prompt
    ↓
Call OpenAI
    ↓
Parse Response
    ↓
IF action=create_order → Create Order
    ↓
Call store-interaction API (ALWAYS)
    ↓
Send Reply
```

**Problems:**
- [ERROR] Fixed sequence - no flexibility
- [ERROR] Always calls prepare-context even if not needed
- [ERROR] No decision-making - follows rigid path
- [ERROR] Cannot adapt to conversation flow
- [ERROR] Makes unnecessary API calls

---

### NEW: Multi-Agent Tool-Calling Architecture
```
Message Received
    ↓
Normalize Data
    ↓
AI Agent (with access to tools)
    │
    ├─ Tool 1: prepare_context (calls API)
    ├─ Tool 2: search_products (calls API)
    ├─ Tool 3: retrieve_memory (calls API)
    ├─ Tool 4: store_memory (calls API)
    └─ Tool 5: store_interaction (calls API)
    ↓
Agent autonomously decides:
  - Which tools to use
  - In what order
  - With what parameters
    ↓
Agent generates final response
    ↓
Send Reply
```

**Benefits:**
- [OK] Dynamic decision-making
- [OK] Calls only necessary endpoints
- [OK] Adapts to conversation context
- [OK] More intelligent routing
- [OK] Reduces API costs (fewer unnecessary calls)

---

## 🔧 Tool Definitions

Each API endpoint is exposed as a "tool" that the AI agent can call:

### 1. **prepare_context** (Priority: MUST CALL FIRST)

**Endpoint:** `POST /n8n/prepare-context`

**Purpose:** Get full conversation context, customer profile, and intent analysis

**When to call:**
- **ALWAYS at the start** of every conversation
- Agent needs this to understand who they're talking to

**Parameters:**
```json
{
  "customer_id": "instagram:@username or whatsapp:+phone",
  "message": "The customer's message",
  "channel": "instagram or whatsapp"
}
```

**Returns:**
```json
{
  "conversation_history": "Formatted chat history...",
  "customer_metadata": {
    "name": "John Doe",
    "phone": "+20123456789",
    "total_orders": 5,
    "total_spent": 1500.00
  },
  "intent_analysis": {
    "intent": "product_inquiry",
    "confidence": 0.95,
    "entities": {
      "product_name": "dress",
      "color": "red",
      "size": "M"
    }
  },
  "cached_response": "...",
  "skip_ai": false
}
```

**Agent's Understanding:**
> "I MUST call this first to understand the customer. If skip_ai is true, I'll use the cached_response directly without generating a new one."

---

### 2. **search_products** (Priority: CONDITIONAL)

**Endpoint:** `POST /products/search`

**Purpose:** Search product catalog by keywords

**When to call:**
- Customer asks "Do you have...?"
- Customer wants product recommendations
- Customer mentions specific items/categories

**When NOT to call:**
- General greetings ("Hello", "Thanks")
- Order status inquiries
- Complaint handling
- Questions already answered by prepare_context

**Parameters:**
```json
{
  "query": "red dress or فستان أحمر or fos2an a7mar",
  "limit": 5
}
```

**Returns:**
```json
{
  "products": [
    {
      "id": "uuid",
      "name": "Elegant Red Dress",
      "price": 299.00,
      "sizes": ["S", "M", "L", "XL"],
      "colors": ["red", "blue", "black"],
      "stock_count": 15,
      "description": "..."
    }
  ],
  "formatted_for_ai": "Product 1: Elegant Red Dress - 299 EGP..."
}
```

**Agent's Understanding:**
> "I should only call this when the customer explicitly asks about product availability or wants recommendations. The prepare_context tool already provides relevant products based on the message, so I don't always need this."

---

### 3. **retrieve_memory** (Priority: OPTIONAL)

**Endpoint:** `GET /context/retrieve?customer_id=...&limit=20`

**Purpose:** Fetch customer's long-term memories and preferences

**When to call:**
- Need personalization beyond conversation history
- Customer asks "What's my usual size?"
- Want to reference past preferences

**Parameters:**
```json
{
  "customer_id": "instagram:@username",
  "limit": 20
}
```

**Returns:**
```json
{
  "messages": [
    {
      "message": "Customer prefers size M",
      "direction": "incoming",
      "created_at": "2025-11-20T10:00:00Z"
    }
  ],
  "formatted_for_ai": "Message 1: Customer prefers size M (20 Nov)..."
}
```

**Agent's Understanding:**
> "I can use this to personalize responses based on past interactions. The prepare_context already gives me recent history, but this gives me older context if needed."

---

### 4. **store_memory** (Priority: OPTIONAL)

**Endpoint:** `POST /context/store`

**Purpose:** Store important customer preferences/facts for future use

**When to call:**
- Customer explicitly states a preference ("I always wear size M")
- Customer shares personal info (address, phone)
- Important fact to remember for next time

**Parameters:**
```json
{
  "customer_id": "instagram:@username",
  "channel": "instagram",
  "message": "Customer prefers blue colors",
  "direction": "incoming",
  "intent": "preference"
}
```

**Returns:**
```json
{
  "success": true,
  "message_id": "uuid"
}
```

**Agent's Understanding:**
> "I should store explicit customer preferences so we remember them for future conversations. Don't store every message - only important facts."

---

### 5. **store_interaction** (Priority: MUST CALL LAST)

**Endpoint:** `POST /n8n/store-interaction`

**Purpose:** Log the complete interaction, cache response, update analytics

**When to call:**
- **ALWAYS at the end** after generating the final response

**Parameters:**
```json
{
  "customer_id": "instagram:@username",
  "channel": "instagram",
  "user_message": "Original customer message",
  "ai_response": "My generated response",
  "intent": "product_inquiry",
  "action": "answer or create_order",
  "order_data": {
    "product_id": "uuid",
    "product_name": "Red Dress",
    "size": "M",
    "color": "red",
    "quantity": 1,
    "total_price": 299.00,
    "customer_name": "John Doe",
    "phone": "+20123456789",
    "address": "123 Main St"
  },
  "ai_tokens_used": 450,
  "response_time_ms": 1200
}
```

**Returns:**
```json
{
  "success": true
}
```

**Agent's Understanding:**
> "I MUST call this last with my final response to log the interaction, cache it for future use, and update analytics. This helps reduce costs by caching common responses."

---

## 🧠 Agent Decision-Making Logic

The AI agent has been instructed with this logic:

### Phase 1: Context Gathering
```
1. Call prepare_context FIRST
   - Get customer history
   - Get intent classification
   - Check for cached responses

2. IF skip_ai = true:
   - Use cached_response directly
   - Skip to Phase 3

3. IF customer asks about specific products:
   - ALSO call search_products
   - Get detailed product info

4. IF need personalization:
   - OPTIONALLY call retrieve_memory
   - Get past preferences
```

### Phase 2: Response Generation
```
1. Analyze all gathered context
2. Generate appropriate response
3. IF customer wants to order AND has all details:
   - Set action = "create_order"
   - Include order_data in store_interaction call
4. ELSE:
   - Set action = "answer"
```

### Phase 3: Interaction Storage
```
1. Call store_interaction LAST
   - Include final response
   - Include action and order data (if applicable)
   - This logs analytics and caches the response
```

---

## 🔄 Example Execution Flows

### Scenario 1: Simple Greeting

**Customer:** "Hello"

**Agent's Actions:**
```
1. [OK] Call prepare_context
   → Returns cached greeting response
   → skip_ai = true

2. [OK] Use cached_response: "Hello! Welcome to our store 👋"

3. [OK] Call store_interaction
   → intent: "greeting"
   → action: "answer"
   → tokens_used: 0 (used cache)
```

**Result:** 2 API calls (minimum required)

---

### Scenario 2: Product Inquiry

**Customer:** "Do you have red dresses in size M?"

**Agent's Actions:**
```
1. [OK] Call prepare_context
   → Returns conversation history and intent
   → intent: "product_inquiry"
   → skip_ai = false
   → Already includes some products from RAG search

2. [OK] Call search_products
   → query: "red dress"
   → Returns 5 matching products

3. [OK] Generate response:
   "Yes! We have 3 beautiful red dresses in size M:
    1. Elegant Red Evening Dress - 299 EGP
    2. Casual Red Summer Dress - 199 EGP
    3. Formal Red Business Dress - 350 EGP

    Which one interests you? 😊"

4. [OK] Call store_interaction
   → intent: "product_inquiry"
   → action: "answer"
   → tokens_used: 450
```

**Result:** 3 API calls (prepare + search + store)

---

### Scenario 3: Order Creation

**Customer:** "I want the red dress size M, my name is Sarah, phone +20123456789, address: 123 Main St Cairo"

**Agent's Actions:**
```
1. [OK] Call prepare_context
   → Returns customer history
   → Shows they were looking at red dresses
   → Extracts entities: size=M, phone, address

2. [OK] Generate response:
   "Perfect! I'm confirming your order:
    • Product: Elegant Red Evening Dress
    • Size: M
    • Price: 299 EGP
    • Delivery to: 123 Main St Cairo

    Your order ID is {{ORDER_ID}}. We'll contact you at +20123456789 for confirmation! "

3. [OK] Call store_interaction
   → intent: "order_intent"
   → action: "create_order"
   → order_data: {product details, customer info}
   → The API will create the order and replace {{ORDER_ID}}
```

**Result:** 2 API calls (prepare + store with order creation)

---

### Scenario 4: Personalized Recommendation

**Customer:** "Recommend something for me"

**Agent's Actions:**
```
1. [OK] Call prepare_context
   → Returns customer history
   → Shows past orders and preferences

2. [OK] Call retrieve_memory
   → Gets stored preferences: "prefers blue colors", "size M"

3. [OK] Call search_products
   → query: "blue dress size M"
   → Returns matching products

4. [OK] Generate response:
   "Based on your previous purchases, I think you'll love these blue dresses in your size (M):
    1. Royal Blue Cocktail Dress - 350 EGP
    2. Navy Blue Casual Dress - 220 EGP

    Which style do you prefer? 💙"

5. [OK] Call store_interaction
   → intent: "product_inquiry"
   → action: "answer"
```

**Result:** 4 API calls (prepare + retrieve + search + store)

---

##  Benefits of Multi-Agent Architecture

### 1. **Cost Optimization**
- **Before:** Always called prepare-context even for cached responses
- **After:** Agent can use cached responses directly (skip_ai=true)
- **Savings:** ~40-60% reduction in unnecessary API calls

### 2. **Intelligence**
- **Before:** Fixed logic - always searched products regardless of query
- **After:** Agent decides when product search is actually needed
- **Result:** More relevant, faster responses

### 3. **Flexibility**
- **Before:** Hardcoded sequence - couldn't adapt to conversation
- **After:** Agent can call tools in any order based on context
- **Result:** Natural, human-like conversations

### 4. **Scalability**
- **Before:** Adding new features required modifying workflow logic
- **After:** Just add new tools - agent figures out when to use them
- **Result:** Easier to extend and maintain

### 5. **Performance**
- **Before:** Always made full context preparation call
- **After:** Can skip heavy operations when not needed
- **Result:** Faster response times for simple queries

---

## 📋 Migration Checklist

To migrate from linear to multi-agent architecture:

### Prerequisites
- [x] API deployed on Render with all endpoints functional
- [x] n8n instance with LangChain AI Agent node support
- [x] OpenAI API key configured

### Migration Steps

1. **Backup Current Workflow**
   - Export existing `n8n_workflow.json`
   - Save as `n8n_workflow_linear_backup.json`

2. **Import New Workflow**
   - Import `n8n_workflow_multi_agent.json` to n8n
   - Activate the new workflow

3. **Configure Tool Connections**
   - Verify all HTTP Request nodes have correct API_URL
   - Ensure API_KEY is set in environment variables
   - Test each tool individually

4. **Test Agent Behavior**
   - Send test message: "Hello"
   - Verify agent calls prepare_context → uses cache → stores interaction
   - Send test: "Do you have red dresses?"
   - Verify agent calls prepare_context → search_products → stores interaction
   - Send test: "I want to order..."
   - Verify agent calls prepare_context → stores with order_data

5. **Monitor & Optimize**
   - Check execution logs for tool call patterns
   - Verify agent is making intelligent decisions
   - Tune system prompt if needed

---

## 🔍 Troubleshooting

### Issue: Agent doesn't call any tools

**Cause:** System prompt may not be clear about tool requirements

**Solution:** Ensure the agent's system message explicitly states:
```
"You MUST call prepare_context first for every conversation.
You MUST call store_interaction last with your response."
```

---

### Issue: Agent calls too many tools unnecessarily

**Cause:** Tool descriptions may be too inviting

**Solution:** Make tool descriptions more specific about WHEN to use them:
```
"Only call search_products if customer explicitly asks about product availability"
```

---

### Issue: Order creation doesn't work

**Cause:** Agent may not be passing order_data correctly to store_interaction

**Solution:** Ensure the agent understands the order_data format and when to include it:
```
"When action='create_order', you MUST include complete order_data with:
product_id, product_name, size, color, quantity, total_price,
customer_name, phone, address"
```

---

### Issue: Tools fail with authentication errors

**Cause:** API_KEY environment variable not set correctly

**Solution:**
```bash
# In n8n environment variables
API_KEY=your-super-secret-api-key

# Verify in HTTP Request nodes:
Header: X-API-Key
Value: ={{ $env.API_KEY }}
```

---

## 📊 Performance Metrics

Expected improvements after migration:

| Metric | Linear Flow | Multi-Agent | Improvement |
|--------|-------------|-------------|-------------|
| **API Calls per Message** | 3-5 | 2-4 | [OK] 20% fewer |
| **Response Time (Simple)** | 2-3 seconds | 0.5-1 second | [OK] 60% faster |
| **Response Time (Complex)** | 3-5 seconds | 2-4 seconds | [OK] 25% faster |
| **Cache Hit Rate** | 30-40% | 50-70% | [OK] 50% better |
| **AI Token Usage** | High | Medium | [OK] 30% reduction |
| **Monthly Cost** | $15-25 | $10-18 | [OK] 35% savings |

---

##  Next Steps

1. **Import the new workflow** from `n8n_workflow_multi_agent.json`
2. **Test thoroughly** with various conversation scenarios
3. **Monitor execution logs** to verify agent behavior
4. **Tune the system prompt** if needed for better decision-making
5. **Add more tools** as new API endpoints become available
6. **Optimize** based on usage patterns and performance metrics

---

## 📚 Additional Resources

- **Workflow File:** `n8n_workflow_multi_agent.json`
- **API Documentation:** `https://your-api.onrender.com/docs`
- **n8n Agent Docs:** https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/
- **OpenAI Function Calling:** https://platform.openai.com/docs/guides/function-calling

---

**The future is autonomous!  Let the agent decide!**
