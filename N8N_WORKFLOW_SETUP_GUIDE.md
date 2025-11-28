# n8n E-commerce AI Assistant - Setup Guide

This guide explains how to set up and configure the n8n workflow for your AI-powered e-commerce assistant that handles Instagram and WhatsApp messages.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Import the Workflow](#import-the-workflow)
3. [Configure Environment Variables](#configure-environment-variables)
4. [Set Up Instagram Integration](#set-up-instagram-integration)
5. [Set Up WhatsApp Integration](#set-up-whatsapp-integration)
6. [Configure OpenAI](#configure-openai)
7. [Test the Workflow](#test-the-workflow)
8. [Webhook Payload Examples](#webhook-payload-examples)
9. [Troubleshooting](#troubleshooting)
10. [Workflow Features](#workflow-features)

---

## Prerequisites

Before starting, ensure you have:

- [ ] n8n instance running (cloud or self-hosted)
- [ ] AI Microservices API deployed on Render (from previous deployment)
- [ ] Instagram Business Account with API access
- [ ] WhatsApp Business API access
- [ ] OpenAI API account

---

## Import the Workflow

### Step 1: Open n8n

1. Log in to your n8n instance
2. Go to **Workflows** section
3. Click **"Add Workflow"**

### Step 2: Import the JSON

1. Click the **"⋮"** (three dots) menu in the top right
2. Select **"Import from File"**
3. Choose `n8n_ecommerce_workflow.json`
4. Click **"Import"**

The workflow will be imported with all nodes connected.

---

## Configure Environment Variables

The workflow uses environment variables for security. Add these in your n8n instance:

### In n8n Settings or Environment Variables

```bash
# Your deployed API URL (from Render deployment)
API_URL=https://your-service.onrender.com

# API Key (same as configured in Render)
API_KEY=your-super-secret-api-key

# Instagram Access Token (from Meta Developer Console)
INSTAGRAM_ACCESS_TOKEN=your-instagram-access-token

# WhatsApp API Configuration
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
WHATSAPP_ACCESS_TOKEN=your-whatsapp-access-token
```

### How to Set Environment Variables in n8n

**For n8n Cloud:**
1. Go to **Settings** → **Environments**
2. Add each variable

**For Self-Hosted n8n:**
1. Edit your `.env` file or docker-compose.yml
2. Add variables under `environment:` section
3. Restart n8n

---

## Set Up Instagram Integration

### Step 1: Create Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Click **"My Apps"** → **"Create App"**
3. Select **"Business"** as app type
4. Fill in app details and create

### Step 2: Add Instagram Product

1. In your app dashboard, click **"Add Product"**
2. Find **"Instagram"** and click **"Set Up"**
3. Complete the Instagram setup wizard

### Step 3: Get Access Token

1. Go to **Instagram** → **Settings**
2. Click **"Generate Token"**
3. Select your Instagram Business Account
4. Grant required permissions:
   - `instagram_basic`
   - `instagram_manage_messages`
   - `pages_messaging`
5. Copy the generated token → This is your `INSTAGRAM_ACCESS_TOKEN`

### Step 4: Set Up Webhook

1. In Meta App dashboard, go to **Instagram** → **Settings** → **Webhooks**
2. Click **"Subscribe to Topics"**
3. Select **"messages"**
4. Enter webhook URL:
   ```
   https://your-n8n-instance.com/webhook/instagram-webhook
   ```
5. Enter a verify token (can be any random string)
6. Click **"Verify and Save"**

### Step 5: Test Instagram Messages

1. Send a DM to your Instagram Business Account
2. Check n8n execution history
3. You should see the message processed and a reply sent

---

## Set Up WhatsApp Integration

### Step 1: Get WhatsApp Business API Access

**Option A: Meta Business Suite (Free for Testing)**
1. Go to [Meta Business Suite](https://business.facebook.com/)
2. Navigate to **WhatsApp** → **API Setup**
3. Follow the setup wizard

**Option B: WhatsApp Cloud API (Production)**
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create or select your app
3. Add **"WhatsApp"** product
4. Complete verification process

### Step 2: Get Phone Number ID and Token

1. In WhatsApp settings, find **Phone Number ID**
2. Copy it and replace in `WHATSAPP_API_URL`:
   ```
   https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
   ```
3. Generate access token:
   - Go to **WhatsApp** → **Settings** → **Access Tokens**
   - Click **"Generate Token"**
   - Copy token → This is your `WHATSAPP_ACCESS_TOKEN`

### Step 3: Configure Webhook

1. Go to **WhatsApp** → **Configuration** → **Webhooks**
2. Click **"Edit"**
3. Enter webhook URL:
   ```
   https://your-n8n-instance.com/webhook/whatsapp-webhook
   ```
4. Enter a verify token (any random string)
5. Subscribe to **"messages"** events
6. Click **"Verify and Save"**

### Step 4: Test WhatsApp Messages

1. Send a WhatsApp message to your business number
2. Check n8n execution history
3. You should see the message processed and a reply sent

---

## Configure OpenAI

### Step 1: Add OpenAI Credentials in n8n

1. In n8n, go to **Credentials**
2. Click **"Add Credential"**
3. Search for **"OpenAI"**
4. Select **"OpenAI API"**
5. Enter your OpenAI API Key
6. Save as `openai_api_cred`

### Step 2: Verify OpenAI Node

1. Open the workflow
2. Find the **"Call OpenAI"** node
3. Ensure it's using credentials: `openai_api_cred`
4. Verify model is set to: `gpt-4o-mini` (or your preferred model)

### Step 3: Adjust AI Parameters (Optional)

In the **"Call OpenAI"** node, you can adjust:
- **Temperature:** 0.7 (creativity level, 0-2)
- **Max Tokens:** 1000 (response length)
- **Model:** `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`

**Cost Consideration:**
- `gpt-4o-mini`: $0.15 per 1M input tokens (cheapest, good quality)
- `gpt-4o`: $2.50 per 1M input tokens (better quality)
- `gpt-4-turbo`: $10 per 1M input tokens (best quality)

---

## Test the Workflow

### Manual Test via Webhook

#### Test Instagram Webhook:

```bash
curl -X POST https://your-n8n-instance.com/webhook/instagram-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "123456789",
    "sender_username": "test_user",
    "sender_name": "Test User",
    "message_text": "I want to buy a red dress",
    "channel": "instagram",
    "timestamp": "2025-11-28T12:00:00Z"
  }'
```

#### Test WhatsApp Webhook:

```bash
curl -X POST https://your-n8n-instance.com/webhook/whatsapp-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_phone": "+201234567890",
    "sender_name": "Test User",
    "text": "أريد شراء فستان أحمر",
    "channel": "whatsapp",
    "timestamp": "2025-11-28T12:00:00Z"
  }'
```

### Expected Workflow Execution:

1. **Receive Message** → Webhook triggers
2. **Normalize Data** → Extracts customer_id, message, channel
3. **Prepare Context** → Calls API to get conversation history, products, intent
4. **Check Cache** → If cached response exists, skip AI
5. **Call AI** → If not cached, call OpenAI with full context
6. **Create Order** → If customer wants to order and provides all details
7. **Store Interaction** → Save conversation, cache response, log analytics
8. **Send Reply** → Send response back to Instagram/WhatsApp

### Check Execution Logs:

1. Go to **Executions** tab in n8n
2. Click on the latest execution
3. Verify all nodes executed successfully (green checkmarks)
4. Check the output of each node

---

## Webhook Payload Examples

### Instagram Incoming Message Format

Meta will send messages in this format:

```json
{
  "object": "instagram",
  "entry": [{
    "id": "PAGE_ID",
    "time": 1234567890,
    "messaging": [{
      "sender": {
        "id": "SENDER_INSTAGRAM_ID"
      },
      "recipient": {
        "id": "PAGE_ID"
      },
      "timestamp": 1234567890,
      "message": {
        "mid": "MESSAGE_ID",
        "text": "I want to buy a dress"
      }
    }]
  }]
}
```

**You may need to add a preprocessing node to transform this to:**

```json
{
  "sender_id": "SENDER_INSTAGRAM_ID",
  "sender_username": "username",
  "message_text": "I want to buy a dress",
  "channel": "instagram",
  "timestamp": "2025-11-28T12:00:00Z"
}
```

### WhatsApp Incoming Message Format

Meta will send messages in this format:

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "PHONE_NUMBER",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {
            "name": "Test User"
          },
          "wa_id": "201234567890"
        }],
        "messages": [{
          "from": "201234567890",
          "id": "MESSAGE_ID",
          "timestamp": "1234567890",
          "text": {
            "body": "Hello, I want to order"
          },
          "type": "text"
        }]
      }
    }]
  }]
}
```

**You may need to add a preprocessing node to transform this to:**

```json
{
  "sender_phone": "+201234567890",
  "sender_name": "Test User",
  "text": "Hello, I want to order",
  "channel": "whatsapp",
  "timestamp": "2025-11-28T12:00:00Z"
}
```

### Recommended: Add Message Transformation Nodes

**For Instagram:**
Add a **Code** node after the Instagram webhook:

```javascript
// Transform Meta Instagram format to workflow format
const entry = $input.item.json.entry?.[0];
const messaging = entry?.messaging?.[0];

return {
  json: {
    sender_id: messaging?.sender?.id,
    sender_username: messaging?.sender?.username || 'unknown',
    sender_name: messaging?.sender?.name || 'Instagram User',
    message_text: messaging?.message?.text,
    channel: 'instagram',
    timestamp: new Date(messaging?.timestamp * 1000).toISOString()
  }
};
```

**For WhatsApp:**
Add a **Code** node after the WhatsApp webhook:

```javascript
// Transform Meta WhatsApp format to workflow format
const change = $input.item.json.entry?.[0]?.changes?.[0];
const message = change?.value?.messages?.[0];
const contact = change?.value?.contacts?.[0];

return {
  json: {
    sender_phone: '+' + message?.from,
    sender_name: contact?.profile?.name || 'WhatsApp User',
    text: message?.text?.body,
    channel: 'whatsapp',
    timestamp: new Date(parseInt(message?.timestamp) * 1000).toISOString()
  }
};
```

---

## Troubleshooting

### Issue 1: Webhook Not Receiving Messages

**Check:**
1. Webhook URL is correct and accessible from the internet
2. n8n workflow is **activated** (toggle in top right)
3. Meta app has proper permissions
4. Webhook subscription is active in Meta dashboard

**Test:**
```bash
curl -X GET https://your-n8n-instance.com/webhook/instagram-webhook
# Should return 200 OK
```

### Issue 2: API Call Fails (Prepare Context)

**Symptoms:**
- Node shows red error
- Error: "Connection refused" or "401 Unauthorized"

**Solutions:**
1. Verify `API_URL` is correct: `https://your-service.onrender.com`
2. Verify `API_KEY` matches the one configured in Render
3. Check Render service is running and healthy
4. Test API manually:
   ```bash
   curl -X POST https://your-service.onrender.com/n8n/prepare-context-enhanced \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"customer_id": "instagram:@test", "message": "hello", "channel": "instagram"}'
   ```

### Issue 3: OpenAI Call Fails

**Symptoms:**
- "Invalid API key" error
- "Rate limit exceeded"
- "Model not found"

**Solutions:**
1. Verify OpenAI API key is valid and has credits
2. Check you haven't exceeded rate limits
3. Verify model name: `gpt-4o-mini` is correct
4. Check OpenAI API status: https://status.openai.com/

### Issue 4: Order Creation Fails

**Symptoms:**
- Order not created in database
- AI mentions order but no order_id

**Check:**
1. Product ID exists in database
2. Product has sufficient stock
3. All required fields are provided (customer name, phone, address)
4. Review API logs in Render dashboard

### Issue 5: Messages Not Sent to Instagram/WhatsApp

**Instagram:**
- Verify `INSTAGRAM_ACCESS_TOKEN` is valid (tokens expire)
- Check `sender_id` is correct
- Verify page has permission to send messages

**WhatsApp:**
- Verify `WHATSAPP_ACCESS_TOKEN` is valid
- Check phone number format: `+201234567890` (with country code)
- Ensure business account is verified
- Check WhatsApp API quota

### Issue 6: Workflow Executes but No Response

**Check Execution Logs:**
1. Go to **Executions** tab
2. Find the failed execution
3. Click each node to see its output
4. Look for errors in red nodes

**Common Causes:**
- Data format mismatch (check "Normalize Message Data" output)
- Missing required fields
- API timeout (increase timeout in HTTP Request nodes)

---

## Workflow Features

### ✅ What the Workflow Does

1. **Receives Messages**
   - Instagram DMs via webhook
   - WhatsApp messages via webhook
   - Normalizes data from both channels

2. **Fetches Context**
   - Customer conversation history (last 50 messages)
   - Customer order history (last 5 orders)
   - Customer metadata (name, phone, total spent)
   - Detects customer intent and extracts entities

3. **Searches Products**
   - RAG-powered semantic search
   - Multilingual support (Arabic, English, Franco-Arabic)
   - Returns relevant products with prices, sizes, colors

4. **Caching & Optimization**
   - Checks for cached responses
   - Skips AI call if response is cached
   - Saves tokens and reduces latency

5. **AI Response Generation**
   - Uses full context (history, products, customer data)
   - Generates contextual, bilingual responses
   - Extracts action and order data from AI response

6. **Order Processing**
   - Creates orders when customer provides all details
   - Validates product and stock
   - Updates customer profile
   - Replaces {{ORDER_ID}} placeholder in response

7. **Analytics & Storage**
   - Stores conversation in database
   - Caches responses for future use
   - Logs analytics events (cache hits, orders, etc.)
   - Tracks response times and token usage

8. **Sends Responses**
   - Sends reply to Instagram via Graph API
   - Sends reply to WhatsApp via Business API
   - Returns webhook acknowledgment

### 🔄 Workflow Flow Diagram

```
Instagram/WhatsApp Message
         ↓
   Normalize Data
         ↓
   Prepare Context (API Call)
   - Get conversation history
   - Search products (RAG)
   - Classify intent
   - Get order history
         ↓
   Check if Cached? ──Yes──→ Use Cached Response
         ↓ No                        ↓
   Build AI Prompt                   │
         ↓                           │
   Call OpenAI GPT-4                 │
         ↓                           │
   Parse AI Response                 │
         ↓                           │
   ←──────────────────────────────────
         ↓
   Check if Create Order? ──Yes──→ Create Order (API Call)
         ↓ No                        ↓
         │                    Process Order Result
         │                           ↓
   ←──────────────────────────────────
         ↓
   Store Interaction (API Call)
   - Save conversation
   - Cache response
   - Log analytics
         ↓
   Route by Channel
         ├─Instagram──→ Send Instagram Reply
         └─WhatsApp───→ Send WhatsApp Reply
                            ↓
                    Webhook Response (200 OK)
```

### 📊 Node Breakdown

| Node Name | Purpose | API Endpoint |
|-----------|---------|--------------|
| Instagram Message Received | Webhook trigger for Instagram | - |
| WhatsApp Message Received | Webhook trigger for WhatsApp | - |
| Normalize Message Data | Standardize data format | - |
| Prepare Context (API Call) | Get full context for AI | `POST /n8n/prepare-context-enhanced` |
| Check if Cached/Skip AI | Optimization check | - |
| Use Cached Response | Use cached reply | - |
| Build AI Prompt | Prepare OpenAI prompt | - |
| Call OpenAI | Generate AI response | OpenAI API |
| Parse AI Response | Extract action & order data | - |
| Merge Responses | Combine cached/AI paths | - |
| Check if Create Order | Decision node | - |
| Create Order (API Call) | Create order in DB | `POST /n8n/create-order` |
| Process Order Result | Replace placeholders | - |
| Merge Order Flow | Combine order paths | - |
| Store Interaction (API Call) | Save & log everything | `POST /n8n/store-interaction` |
| Prepare Final Response | Format final message | - |
| Route by Channel | Send to correct platform | - |
| Send Instagram Reply | Send via Graph API | Instagram Graph API |
| Send WhatsApp Reply | Send via Business API | WhatsApp Business API |
| Webhook Response | Acknowledge webhook | - |

---

## Advanced Configuration

### Customize AI Personality

Edit the **"Build AI Prompt"** node, find the `system_prompt`:

```markdown
You are a helpful Arabic/English bilingual customer service assistant...

## Your Personality
- Friendly, professional, and helpful
- Respond in the same language as the customer
- Be concise but thorough
- Use emojis sparingly

[Customize this section to match your brand voice]
```

### Adjust Product Search Limit

In the API configuration (Render environment variables):
```bash
MAX_PRODUCT_SEARCH_RESULTS=5  # Change to 3, 7, or 10
```

### Enable/Disable Features

In the API configuration:
```bash
ENABLE_SEMANTIC_SEARCH=true   # RAG search
ENABLE_KNOWLEDGE_BASE=true    # KB articles
ENABLE_HYBRID_SEARCH=true     # Keyword + semantic
```

### Add Custom Intent Handling

In the **"Check if Cached/Skip AI"** node, you can add custom logic:

```javascript
// Skip AI for specific intents
if ($json.intent_analysis.intent === "greeting") {
  return {
    skip_ai: true,
    cached_response: "Hello! How can I help you today? 👋"
  };
}
```

### Add Error Notifications

Add a **Slack** or **Discord** node after error paths:
1. Connect to error outputs (red dots)
2. Send notification with error details
3. Alert your team about issues

---

## Performance Optimization

### 1. Response Caching

Already enabled! Common queries are cached for 24 hours by default.

**Adjust cache TTL:**
```bash
# In Render environment variables
DEFAULT_CACHE_TTL_HOURS=24  # Change to 12, 48, or 72
```

### 2. Reduce AI Costs

**Use cheaper models:**
- Current: `gpt-4o-mini` ($0.15/1M tokens)
- Alternative: `gpt-3.5-turbo` ($0.50/1M tokens)

**Reduce max tokens:**
- Current: 1000 tokens
- Set to 500 for shorter responses

**Enable more caching:**
- Increase cache TTL
- Cache more intent types

### 3. Parallelize API Calls

The workflow already runs optimized, but you can add parallel HTTP requests if needed.

### 4. Use Local Embeddings

To eliminate OpenAI embedding costs:
```bash
# In Render environment variables
USE_LOCAL_EMBEDDINGS=true
```

---

## Security Best Practices

1. **Never expose API keys in workflow**
   - Always use environment variables
   - Never hardcode in nodes

2. **Validate webhook signatures**
   - Add signature verification for Instagram/WhatsApp
   - Prevents unauthorized webhook calls

3. **Rate limiting**
   - Already enabled in API (100 req/min)
   - Add n8n rate limiting if needed

4. **HTTPS only**
   - All webhooks must use HTTPS
   - n8n Cloud provides this automatically

5. **Rotate tokens regularly**
   - Instagram/WhatsApp tokens
   - API keys
   - OpenAI keys

---

## Monitoring & Maintenance

### Daily:
- Check n8n execution history for errors
- Monitor API logs in Render dashboard
- Verify messages are being processed

### Weekly:
- Review analytics dashboard (`/analytics/dashboard`)
- Check cache hit rate
- Monitor OpenAI costs

### Monthly:
- Refresh Instagram/WhatsApp tokens if needed
- Update product catalog
- Review and optimize AI prompts
- Check for n8n workflow updates

---

## Support & Resources

### Documentation:
- **n8n Docs:** https://docs.n8n.io/
- **Meta Graph API:** https://developers.facebook.com/docs/graph-api
- **WhatsApp Business API:** https://developers.facebook.com/docs/whatsapp
- **OpenAI API:** https://platform.openai.com/docs/api-reference

### API Endpoints Reference:
See your deployed API documentation at:
```
https://your-service.onrender.com/docs
```

### Need Help?
1. Check n8n execution logs
2. Review API logs in Render
3. Test endpoints manually with curl
4. Check Meta webhooks dashboard for delivery issues

---

## Workflow Summary

**Input:** Instagram/WhatsApp message via webhook
**Processing:**
- Fetch customer context & history
- Search relevant products (RAG)
- Generate AI response (OpenAI)
- Create order if requested
- Store interaction & analytics

**Output:** Reply sent to customer via Instagram/WhatsApp

**Key Features:**
- ✅ Bilingual (Arabic/English)
- ✅ Context-aware responses
- ✅ Order creation & tracking
- ✅ Response caching (saves tokens)
- ✅ RAG-powered product search
- ✅ Analytics logging
- ✅ Multi-channel support

---

**Your AI assistant is now ready to handle customer messages automatically! 🚀**
