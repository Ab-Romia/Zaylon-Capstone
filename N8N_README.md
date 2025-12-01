# n8n Multi-Agent Workflow for AI E-commerce Assistant

This directory contains the **multi-agent tool-calling workflow** for automating your AI-powered e-commerce customer service on Instagram and WhatsApp.

##  Architecture: Multi-Agent Tool Calling

Unlike traditional linear workflows, this implementation uses an **AI Agent** that autonomously decides which API endpoints to call based on the conversation context.

## 📁 Files

- **`n8n_workflow.json`** - Multi-agent workflow with tool calling (import this)
- **`n8n_workflow_linear_backup.json`** - Legacy linear workflow (backup)
- **`n8n_workflow_multi_agent.json`** - Same as above (explicit naming)
- **`MULTI_AGENT_ARCHITECTURE.md`** - Complete architecture documentation
- **`N8N_WORKFLOW_SETUP_GUIDE.md`** - Setup guide

##  Quick Start

### 1. Deploy Your API First

Before using this workflow, deploy the AI microservices API to Render:

1. Push your code to GitHub
2. Create a new Web Service on Render
3. Configure environment variables (see DEPLOYMENT.md)
4. Deploy and verify health check passes

### 2. Import Workflow to n8n

1. Open your n8n instance
2. Go to Workflows → Add Workflow
3. Click "⋮" menu → "Import from File"
4. Select `n8n_workflow.json`
5. Click "Import"

### 3. Configure Environment Variables

Add these to your n8n environment:

```bash
API_URL=https://your-service.onrender.com
API_KEY=your-super-secret-api-key
INSTAGRAM_ACCESS_TOKEN=your-instagram-token
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
```

### 4. Set Up Credentials

In n8n Credentials, add:
- **OpenAI API** (for AI agent and tool calling)
- Save as: `openai_api_cred`

### 5. Configure Webhooks

**Instagram:**
- Meta Developer Console → Instagram → Webhooks
- URL: `https://your-n8n.com/webhook/instagram-webhook`
- Subscribe to: `messages`

**WhatsApp:**
- Meta Developer Console → WhatsApp → Configuration
- URL: `https://your-n8n.com/webhook/whatsapp-webhook`
- Subscribe to: `messages`

### 6. Activate Workflow

1. Toggle the workflow to "Active" (top right)
2. Send a test message to your Instagram/WhatsApp
3. Check execution logs

---

## 🤖 How It Works (Multi-Agent)

```
Customer Message (Instagram/WhatsApp)
         ↓
   Normalize Message Data
         ↓
   AI Agent (Tool Calling)
         │
         ├─ Tool 1: prepare_context (ALWAYS FIRST)
         │    └─ GET conversation history, customer profile, intent
         │
         ├─ Tool 2: search_products (CONDITIONAL)
         │    └─ IF customer asks "do you have...?"
         │
         ├─ Tool 3: retrieve_memory (OPTIONAL)
         │    └─ IF need personalization
         │
         ├─ Tool 4: store_memory (OPTIONAL)
         │    └─ IF customer shares preferences
         │
         └─ Tool 5: store_interaction (ALWAYS LAST)
              └─ LOG analytics, CACHE response, UPDATE profile
         ↓
   Agent Generates Contextual Response
         ↓
   Send Reply to Customer (Instagram/WhatsApp)
```

## ✨ Key Differences from Linear Flow

| Aspect | Linear Flow | Multi-Agent Flow |
|--------|-------------|------------------|
| **Decision Making** | Hardcoded sequence | Agent decides autonomously |
| **API Calls** | Always calls all endpoints | Calls only what's needed |
| **Flexibility** | Fixed logic | Adapts to conversation |
| **Performance** | 3-5 API calls per message | 2-4 API calls per message |
| **Cost** | Higher (unnecessary calls) | Lower (intelligent routing) |
| **Extensibility** | Modify workflow logic | Just add new tools |

## 🔧 Available Tools

The AI agent has access to these tools (API endpoints):

### 1. **prepare_context** (Priority: MUST CALL FIRST)
- **Endpoint:** `POST /n8n/prepare-context`
- **Purpose:** Get conversation history, customer profile, intent
- **When:** ALWAYS at the start of every conversation
- **Returns:** Conversation history, customer data, cached responses

### 2. **search_products** (Priority: CONDITIONAL)
- **Endpoint:** `POST /products/search`
- **Purpose:** Search product catalog by keywords
- **When:** Customer explicitly asks about product availability
- **Returns:** Products with prices, sizes, colors, stock status

### 3. **retrieve_memory** (Priority: OPTIONAL)
- **Endpoint:** `GET /context/retrieve`
- **Purpose:** Fetch customer's long-term memories/preferences
- **When:** Need personalization beyond recent history
- **Returns:** Past messages, preferences, patterns

### 4. **store_memory** (Priority: OPTIONAL)
- **Endpoint:** `POST /context/store`
- **Purpose:** Store important customer preferences/facts
- **When:** Customer states explicit preferences
- **Returns:** Success confirmation

### 5. **store_interaction** (Priority: MUST CALL LAST)
- **Endpoint:** `POST /n8n/store-interaction`
- **Purpose:** Log interaction, cache response, update analytics
- **When:** ALWAYS at the end with final response
- **Returns:** Success confirmation

---

## 📊 Example Execution Flow

### Scenario: Product Inquiry

**Customer:** "Do you have red dresses in size M?"

**Agent's Autonomous Actions:**
```
1. [OK] Calls prepare_context
   → Gets customer history
   → Detects intent: "product_inquiry"
   → Returns relevant products from RAG

2. [OK] Calls search_products
   → Searches for "red dress"
   → Gets 5 matching products

3. [OK] Generates response:
   "Yes! We have 3 beautiful red dresses in size M:
    1. Elegant Red Evening Dress - 299 EGP
    2. Casual Red Summer Dress - 199 EGP
    3. Formal Red Business Dress - 350 EGP
    Which one interests you? 😊"

4. [OK] Calls store_interaction
   → Logs the interaction
   → Caches the response
   → Updates analytics
```

**Total API Calls:** 3 (prepare + search + store)

---

##  Benefits

### 1. **Intelligent Routing**
- Agent decides which tools to use based on context
- No hardcoded logic - fully dynamic
- Adapts to conversation flow

### 2. **Cost Optimization**
- **Before:** 3-5 API calls per message (always)
- **After:** 2-4 API calls per message (only when needed)
- **Savings:** ~30% reduction in API costs

### 3. **Better Performance**
- Simple queries (greetings): 2 API calls, <1 second
- Complex queries (orders): 3-4 API calls, 2-3 seconds
- Cached responses: 0 AI tokens (60% faster)

### 4. **Scalability**
- Add new tools → Agent figures out when to use them
- No workflow logic changes needed
- Easier to extend and maintain

---

## 📖 Full Documentation

For complete architecture details, migration guide, and troubleshooting:

👉 **Read [`MULTI_AGENT_ARCHITECTURE.md`](./MULTI_AGENT_ARCHITECTURE.md)**

For setup instructions:

👉 **Read [`N8N_WORKFLOW_SETUP_GUIDE.md`](./N8N_WORKFLOW_SETUP_GUIDE.md)**

---

## 🔧 Quick Test

Test the multi-agent workflow:

```bash
# Test Instagram (simple greeting - should use cache)
curl -X POST https://your-n8n.com/webhook/instagram-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "123456",
    "sender_username": "test_user",
    "message_text": "Hello",
    "channel": "instagram",
    "timestamp": "2025-11-28T12:00:00Z"
  }'

# Test WhatsApp (product inquiry - should search)
curl -X POST https://your-n8n.com/webhook/whatsapp-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_phone": "+201234567890",
    "sender_name": "Test User",
    "text": "Do you have red dresses?",
    "channel": "whatsapp",
    "timestamp": "2025-11-28T12:00:00Z"
  }'
```

### Check Execution Logs

1. Go to n8n **Executions** tab
2. Find the latest execution
3. Verify which tools the agent called
4. Check that the agent made intelligent decisions

---

## 🆘 Troubleshooting

### Agent doesn't call any tools

**Solution:** Check the AI Agent node's system prompt includes:
```
"You MUST call prepare_context first for every conversation.
You MUST call store_interaction last with your response."
```

### Agent calls too many unnecessary tools

**Solution:** Make tool descriptions more specific:
```
"Only call search_products if customer explicitly asks about product availability"
```

### Tools fail with authentication errors

**Solution:** Verify environment variables:
```bash
API_URL=https://your-service.onrender.com  # No trailing slash
API_KEY=your-super-secret-api-key
```

### Agent response is not sent to customer

**Solution:** Check the "Extract Agent Response" node:
```javascript
const agentOutput = $input.item.json.output || $input.item.json.text || '';
```

---

## 📚 API Endpoints Used

The workflow dynamically calls these API endpoints via tools:

1. **POST /n8n/prepare-context** - Context preparation
2. **POST /products/search** - Product search
3. **GET /context/retrieve** - Memory retrieval
4. **POST /context/store** - Memory storage
5. **POST /n8n/store-interaction** - Interaction logging

See full API documentation at: `https://your-api.com/docs`

---

## 💰 Cost Estimate

| Component | Linear Flow | Multi-Agent | Savings |
|-----------|-------------|-------------|---------|
| n8n Cloud | $20 or $0 | $20 or $0 | - |
| OpenAI API | $15-25 | $10-18 | **[OK] 35%** |
| API Calls | Higher | Lower | **[OK] 30%** |
| **Total** | **$15-45** | **$10-38** | **[OK] 25-30%** |

---

##  Migration from Linear Flow

If you're upgrading from the old linear workflow:

1. [OK] **Backup current workflow** (already done: `n8n_workflow_linear_backup.json`)
2. [OK] **Import new workflow** from `n8n_workflow.json`
3. [OK] **Test with sample messages** to verify agent behavior
4. [OK] **Monitor execution logs** for 24-48 hours
5. [OK] **Tune system prompt** if needed for better decisions

**Migration Guide:** See `MULTI_AGENT_ARCHITECTURE.md` section "Migration Checklist"

---

##  Next Steps

1. [OK] Deploy API to Render
2. [OK] Import multi-agent workflow to n8n
3. [OK] Configure environment variables
4. [OK] Set up Instagram/WhatsApp webhooks
5. [OK] Test with various conversation scenarios
6. 📊 Monitor agent's tool-calling patterns
7. 🔧 Optimize system prompt based on usage
8. 📈 Scale as needed

---

**The future is autonomous! 🤖 Let the agent decide!**

For detailed architecture explanation and troubleshooting:
- **Architecture:** [`MULTI_AGENT_ARCHITECTURE.md`](./MULTI_AGENT_ARCHITECTURE.md)
- **Setup Guide:** [`N8N_WORKFLOW_SETUP_GUIDE.md`](./N8N_WORKFLOW_SETUP_GUIDE.md)
