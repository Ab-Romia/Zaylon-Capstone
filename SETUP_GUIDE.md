# Complete Instagram DM Automation Setup Guide

This guide walks you through setting up Instagram DM automation end-to-end, from Meta Developer configuration to n8n workflow integration with the microservice.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Meta Developer App Setup](#meta-developer-app-setup)
3. [Deploy Your Microservice](#deploy-your-microservice)
4. [Instagram Webhook Configuration](#instagram-webhook-configuration)
5. [n8n Workflow Setup](#n8n-workflow-setup)
6. [Testing the Integration](#testing-the-integration)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- [ ] Instagram Business or Creator account (NOT personal)
- [ ] Facebook Page connected to your Instagram account
- [ ] Meta (Facebook) Developer account
- [ ] n8n instance running (self-hosted or cloud)
- [ ] Domain with HTTPS (required by Meta)
- [ ] Supabase/PostgreSQL database with schema.sql applied
- [ ] Microservice deployed on Render (already live at https://dm-service-mpjf.onrender.com)

---

## Part 1: Meta Developer App Setup

### Step 1: Create Meta Developer Account

1. Go to https://developers.facebook.com
2. Click "Get Started" or "My Apps"
3. Accept the Platform Policies
4. Verify your account (phone number required)

### Step 2: Create a New App

1. Click **"Create App"**
2. Select use case: **"Other"**
3. Select app type: **"Business"**
4. Fill in:
   - **App Name**: `E-commerce DM Bot` (or your choice)
   - **App Contact Email**: your email
   - **Business Account**: Select or create one
5. Click **"Create App"**

### Step 3: Add Instagram Product

1. In your App Dashboard, find **"Add Products to Your App"**
2. Find **"Instagram"** and click **"Set Up"**
3. You'll see Instagram Basic Display and Instagram API options
4. We need **Instagram Graph API** for messaging

### Step 4: Configure App Settings

1. Go to **App Settings > Basic**
2. Note down:
   - **App ID**: `your-app-id`
   - **App Secret**: `your-app-secret` (Click "Show")
3. Add your **Privacy Policy URL** (required for production)
4. Add your **Terms of Service URL**
5. Select **Category**: "Business" or "E-commerce"

### Step 5: Request Permissions

Navigate to **App Review > Permissions and Features**. You need these permissions:

**Required Permissions:**
1. `instagram_basic` - Read profile info
2. `instagram_manage_messages` - Send and receive DMs (CRITICAL)
3. `pages_manage_metadata` - Manage page settings
4. `pages_show_list` - Access connected pages
5. `pages_read_engagement` - Read page data

**For each permission:**
1. Click **"Request"**
2. Complete the required information
3. Provide use case explanation
4. Submit for review

**IMPORTANT:** `instagram_manage_messages` takes 7-30 days for approval.

For development/testing, use **Test Users** or your own account as admin.

### Step 6: Generate Access Tokens

1. Go to **Tools > Graph API Explorer**
2. Select your app from the dropdown
3. Click **"Generate Access Token"**
4. Select permissions:
   - `instagram_basic`
   - `instagram_manage_messages`
   - `pages_show_list`
   - `pages_read_engagement`
5. Click **"Generate"**
6. **CRITICAL**: This is a short-lived token (1-2 hours)

**Get Long-Lived Token:**

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}"
```

This returns a token valid for 60 days.

**Get Page Access Token:**

```bash
curl -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token={long-lived-user-token}"
```

Response includes your Page ID and Page Access Token.

**Get Instagram Business Account ID:**

```bash
curl -X GET "https://graph.facebook.com/v18.0/{page-id}?fields=instagram_business_account&access_token={page-access-token}"
```

Note down your **Instagram Business Account ID** (IGSID).

---

## Part 2: Microservice Deployment (Render)

### ✅ Your Microservice is Already Deployed!

**Production URL:** `https://dm-service-mpjf.onrender.com`

The microservice is already live on Render with:
- ✅ IPv4 database connection fix applied
- ✅ Automatic HTTPS enabled
- ✅ Health monitoring active
- ✅ Connected to Supabase database

### Configure Environment Variables

You need to add your API key in Render:

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select your service: **dm-service-mpjf**
3. Go to **Environment** tab
4. Add environment variable:
   ```
   Key: API_KEY
   Value: your-secret-api-key-123
   ```
   (Choose a strong, random key - this will be used in n8n)

5. Add Supabase connection (Session Mode for IPv4 compatibility):
   ```
   Key: DATABASE_URL
   Value: postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```
   Get this from: Supabase Dashboard → Settings → Database → Connection String → **Session Mode**

6. Click **Save Changes**

### Verify Deployment

Test the health endpoint:
```bash
curl https://dm-service-mpjf.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2025-11-18T..."
}
```

### Optional: Deploy Your Own Instance

If you want to deploy your own instance on Render:

1. Go to https://render.com
2. **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `your-dm-service`
   - **Branch**: `claude/fix-render-deployment-01UMdivpCptUegkSPAT2HNLb`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables (API_KEY, DATABASE_URL)
6. Click **Create Web Service**

Your URL will be: `https://your-dm-service.onrender.com`

---

## Part 3: Instagram Webhook Configuration

### Step 1: Prepare Your Webhook Endpoint

Your n8n instance needs a publicly accessible URL. Meta requires HTTPS.

**n8n Cloud:** Already has HTTPS
**Self-hosted n8n:** Use ngrok, Cloudflare Tunnel, or reverse proxy

Example n8n webhook URL:
```
https://your-n8n.com/webhook/instagram-dm
```

### Step 2: Configure Webhook in Meta Dashboard

1. Go to your Meta App Dashboard
2. Navigate to **Products > Webhooks**
3. Click **"Add Product"** if Webhooks isn't listed
4. Select **"Instagram"** from the dropdown

### Step 3: Subscribe to Instagram Webhooks

1. Click **"Subscribe to this object"** (or "Edit Subscription")
2. Fill in:

   **Callback URL:**
   ```
   https://your-n8n-domain.com/webhook/instagram-dm
   ```

   **Verify Token:**
   ```
   my_instagram_verify_token_12345
   ```
   (Create your own secure random string)

3. **DON'T CLICK VERIFY YET** - We need to set up n8n first

### Step 4: Subscribe to Webhook Fields

After verification, subscribe to these fields:
- `messages` - Receive DM notifications (MOST IMPORTANT)
- `messaging_postbacks` - Button click events
- `messaging_optins` - User opt-ins

---

## Part 4: n8n Workflow Setup

### Step 1: Create Webhook Verification Handler

In n8n, Meta first sends a GET request to verify your webhook. Create this workflow:

1. **Create new workflow**: "Instagram Webhook Verification"

2. **Add Webhook node**:
   - HTTP Method: `GET`
   - Path: `instagram-dm`
   - Response Mode: `Last Node`

3. **Add IF node** (check for verification):
   - Condition: `{{ $json.query["hub.mode"] }}` equals `subscribe`

4. **Add Set node** (return challenge):
   - String: `{{ $json.query["hub.challenge"] }}`

5. **Activate the workflow**

6. **Get the webhook URL** (click on Webhook node):
   ```
   https://your-n8n.com/webhook/instagram-dm
   ```

### Step 2: Verify Webhook with Meta

1. Go back to Meta Webhooks dashboard
2. Paste your callback URL
3. Enter your verify token
4. Click **"Verify and Save"**

Meta sends:
```
GET your-url?hub.mode=subscribe&hub.verify_token=your-token&hub.challenge=random-string
```

Your n8n returns the challenge string. If successful, webhook is verified!

### Step 3: Create Main DM Handler Workflow

Now create the main workflow that processes incoming messages:

**Workflow: Instagram DM Automation**

See the file `instagram_dm_workflow.json` in this repository for the complete importable workflow.

**Workflow Structure:**
```
Instagram Webhook (POST)
    ↓
Parse Message Data
    ↓
Call Microservice: /n8n/prepare-context
    ↓
IF: skip_ai == true?
    ├─ YES → Use cached_response
    └─ NO  → Call OpenAI
    ↓
Call Microservice: /n8n/store-interaction
    ↓
Send Reply to Instagram
```

---

## Part 5: Complete n8n Workflow Configuration

### Node 1: Instagram Webhook (Trigger)

```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "instagram-dm",
    "responseMode": "onReceived",
    "responseData": "allEntries"
  },
  "name": "Instagram Webhook",
  "type": "n8n-nodes-base.webhook",
  "typeVersion": 1
}
```

### Node 2: Extract Message Data

```javascript
// Code node - Extract message from Meta webhook payload
const webhookData = $input.all()[0].json;

// Meta sends this structure
const entry = webhookData.entry?.[0];
const messaging = entry?.messaging?.[0];

if (!messaging) {
  return [{ json: { error: "No message data" } }];
}

const senderId = messaging.sender.id;
const recipientId = messaging.recipient.id;
const timestamp = messaging.timestamp;
const messageText = messaging.message?.text || "";
const messageId = messaging.message?.mid;

// Extract Instagram username from sender ID
// Note: You may need to call Graph API to get actual username
const customerId = `instagram:${senderId}`;

return [{
  json: {
    customer_id: customerId,
    sender_id: senderId,
    recipient_id: recipientId,
    message_text: messageText,
    message_id: messageId,
    timestamp: timestamp,
    channel: "instagram",
    raw_data: webhookData
  }
}];
```

### Node 3: Prepare Context (HTTP Request)

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://dm-service-mpjf.onrender.com/n8n/prepare-context",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {
          "name": "customer_id",
          "value": "={{ $json.customer_id }}"
        },
        {
          "name": "message",
          "value": "={{ $json.message_text }}"
        },
        {
          "name": "channel",
          "value": "instagram"
        }
      ]
    },
    "options": {}
  },
  "name": "Prepare Context",
  "type": "n8n-nodes-base.httpRequest"
}
```

**HTTP Header Auth credentials:**
- Name: `X-API-Key`
- Value: `your-microservice-api-key`

### Node 4: Check Skip AI (IF Node)

```json
{
  "parameters": {
    "conditions": {
      "boolean": [
        {
          "value1": "={{ $json.skip_ai }}",
          "value2": true
        }
      ]
    }
  },
  "name": "Skip AI?",
  "type": "n8n-nodes-base.if"
}
```

### Node 5a: Use Cached Response (True Branch)

```javascript
// Set node - Use cached response
return [{
  json: {
    response_text: $('Prepare Context').item.json.cached_response,
    intent: $('Prepare Context').item.json.intent_analysis.intent,
    action: "cached_response",
    tokens_used: 0,
    sender_id: $('Extract Message').item.json.sender_id,
    customer_id: $('Extract Message').item.json.customer_id,
    user_message: $('Extract Message').item.json.message_text,
    timestamp: $('Extract Message').item.json.timestamp
  }
}];
```

### Node 5b: Call OpenAI (False Branch)

```json
{
  "parameters": {
    "modelId": "gpt-4",
    "messages": {
      "values": [
        {
          "content": "=You are a helpful e-commerce assistant for an Egyptian clothing store. You help customers browse products, answer questions, and take orders.\n\n{{ $('Prepare Context').item.json.conversation_history }}\n\n{{ $('Prepare Context').item.json.relevant_products }}\n\nCustomer Intent: {{ $('Prepare Context').item.json.intent_analysis.intent }}\nCustomer Preferred Language: {{ $('Prepare Context').item.json.customer_metadata.preferred_language }}\nExtracted Entities: {{ JSON.stringify($('Prepare Context').item.json.intent_analysis.entities) }}\n\nRespond naturally in the customer's preferred language. If they want to order, collect: full name, phone number (Egyptian format), and delivery address.\n\nRespond ONLY with a JSON object in this format:\n{\n  \"text\": \"Your response message to the customer\",\n  \"action\": \"answer|request_info|create_order\",\n  \"order_data\": null or {\"product_id\": \"\", \"size\": \"\", \"color\": \"\", \"quantity\": 1, \"customer_name\": \"\", \"phone\": \"\", \"address\": \"\"}\n}"
        },
        {
          "content": "={{ $('Extract Message').item.json.message_text }}"
        }
      ]
    },
    "options": {
      "temperature": 0.7,
      "maxTokens": 500
    }
  },
  "name": "OpenAI Chat",
  "type": "n8n-nodes-base.openAi"
}
```

### Node 6: Parse AI Response

```javascript
// Parse OpenAI response
const aiResponse = $input.first().json;
let responseData;

try {
  // Try to parse as JSON
  const content = aiResponse.message?.content || aiResponse.choices?.[0]?.message?.content;
  responseData = JSON.parse(content);
} catch (e) {
  // Fallback if not valid JSON
  responseData = {
    text: aiResponse.message?.content || "Sorry, I couldn't process that. Please try again.",
    action: "answer",
    order_data: null
  };
}

return [{
  json: {
    response_text: responseData.text,
    action: responseData.action,
    order_data: responseData.order_data,
    intent: $('Prepare Context').item.json.intent_analysis.intent,
    tokens_used: aiResponse.usage?.total_tokens || 0,
    sender_id: $('Extract Message').item.json.sender_id,
    customer_id: $('Extract Message').item.json.customer_id,
    user_message: $('Extract Message').item.json.message_text,
    timestamp: $('Extract Message').item.json.timestamp
  }
}];
```

### Node 7: Merge Responses

Merge the cached and AI response branches:
```json
{
  "name": "Merge Responses",
  "type": "n8n-nodes-base.merge",
  "parameters": {
    "mode": "append"
  }
}
```

### Node 8: Store Interaction

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://dm-service-mpjf.onrender.com/n8n/store-interaction",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={\n  \"customer_id\": \"{{ $json.customer_id }}\",\n  \"channel\": \"instagram\",\n  \"user_message\": \"{{ $json.user_message }}\",\n  \"ai_response\": \"{{ $json.response_text }}\",\n  \"intent\": \"{{ $json.intent }}\",\n  \"action\": \"{{ $json.action }}\",\n  \"order_data\": {{ $json.order_data ? JSON.stringify($json.order_data) : 'null' }},\n  \"response_time_ms\": {{ Date.now() - $json.timestamp }},\n  \"ai_tokens_used\": {{ $json.tokens_used }}\n}"
  },
  "name": "Store Interaction",
  "type": "n8n-nodes-base.httpRequest"
}
```

### Node 9: Send Instagram Reply

```json
{
  "parameters": {
    "method": "POST",
    "url": "=https://graph.facebook.com/v18.0/me/messages",
    "authentication": "genericCredentialType",
    "genericAuthType": "httpQueryAuth",
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={\n  \"recipient\": {\n    \"id\": \"{{ $('Extract Message').item.json.sender_id }}\"\n  },\n  \"message\": {\n    \"text\": \"{{ $json.response_text }}\"\n  }\n}"
  },
  "name": "Send Instagram Reply",
  "type": "n8n-nodes-base.httpRequest"
}
```

**Query Auth credentials:**
- Name: `access_token`
- Value: `your-page-access-token`

### Node 10: Handle Order Creation (Optional)

If `action === "create_order"` and `order_data` is not null:

```json
{
  "parameters": {
    "operation": "insert",
    "table": "orders",
    "columns": "product_id,product_name,size,color,quantity,total_price,customer_name,customer_phone,delivery_address,status,instagram_user",
    "values": "={{ $json.order_data.product_id }},={{ $json.order_data.product_name }},={{ $json.order_data.size }},={{ $json.order_data.color }},={{ $json.order_data.quantity }},={{ $json.order_data.total_price }},={{ $json.order_data.customer_name }},={{ $json.order_data.phone }},={{ $json.order_data.address }},pending,={{ $json.customer_id }}"
  },
  "name": "Create Order in Supabase",
  "type": "n8n-nodes-base.supabase"
}
```

---

## Part 6: Environment Variables Summary

### Meta App:
```
META_APP_ID=your-app-id
META_APP_SECRET=your-app-secret
PAGE_ACCESS_TOKEN=your-long-lived-page-token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your-igsid
VERIFY_TOKEN=my_instagram_verify_token_12345
```

### Microservice (.env):
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
API_KEY=your-secure-random-key
RATE_LIMIT_PER_MINUTE=100
```

### n8n Credentials:
1. **HTTP Header Auth** for microservice API calls
2. **HTTP Query Auth** for Meta Graph API calls
3. **OpenAI API** credentials
4. **Supabase** credentials (for order creation)

---

## Part 7: Testing the Integration

### Test 1: Webhook Verification
```bash
curl "https://your-n8n.com/webhook/instagram-dm?hub.mode=subscribe&hub.verify_token=your-token&hub.challenge=test123"
# Should return: test123
```

### Test 2: Microservice Health
```bash
curl -H "X-API-Key: your-key" https://dm-service-mpjf.onrender.com/health
```

### Test 3: Simulate Webhook Message
```bash
curl -X POST https://your-n8n.com/webhook/instagram-dm \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "id": "123456789",
      "time": 1234567890,
      "messaging": [{
        "sender": {"id": "987654321"},
        "recipient": {"id": "123456789"},
        "timestamp": 1234567890000,
        "message": {
          "mid": "msg_id_123",
          "text": "3ayez jeans azra2 size 32"
        }
      }]
    }]
  }'
```

### Test 4: Send Real Instagram DM
1. Open Instagram
2. Message your business account
3. Check n8n execution logs
4. Verify response is sent back

---

## Part 8: Common Issues & Troubleshooting

### Issue: "Callback URL couldn't be validated"

**Causes:**
- n8n workflow not active
- HTTPS not properly configured
- Verify token mismatch
- Firewall blocking Meta's IPs

**Solution:**
1. Ensure workflow is **ACTIVE** (toggle on)
2. Test URL manually with curl
3. Check n8n logs for incoming requests
4. Verify token matches exactly (case-sensitive)

### Issue: Webhook verified but no messages received

**Causes:**
- Not subscribed to "messages" field
- Permissions not approved
- Instagram account not linked to Facebook Page

**Solution:**
1. Go to Webhooks > Instagram > Subscribe to "messages"
2. Verify `instagram_manage_messages` permission is approved
3. Ensure Instagram Business Account is connected to Page

### Issue: Messages received but can't reply

**Causes:**
- Invalid or expired access token
- Missing `instagram_manage_messages` permission
- Rate limiting

**Solution:**
1. Regenerate Page Access Token
2. Use long-lived token (60 days)
3. Check Graph API errors in response

### Issue: 24-hour messaging window

**Important:** Instagram has a 24-hour messaging window policy. You can only send messages to users who have messaged you within the last 24 hours.

### Issue: Slow response times

**Solution:**
1. Microservice deployed geographically close to users
2. Database connection pooling enabled
3. Response caching working (check cache_hit_rate in analytics)

---

## Part 9: Production Checklist

Before going live:

- [ ] Meta App reviewed and approved
- [ ] `instagram_manage_messages` permission approved
- [ ] Long-lived Page Access Token generated
- [ ] Microservice deployed with proper environment variables
- [ ] Database schema applied and indexes created
- [ ] n8n workflows tested end-to-end
- [ ] Error handling in place
- [ ] Monitoring/logging configured
- [ ] Backup access token ready (tokens expire)
- [ ] GDPR/Privacy compliance verified
- [ ] Rate limiting configured appropriately

---

## Part 10: Maintenance

### Regular Tasks:

1. **Refresh Access Token** (every 60 days)
   ```bash
   # Exchange current token for new one
   curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app-id}&client_secret={app-secret}&fb_exchange_token={current-token}"
   ```

2. **Clean up cache** (weekly)
   ```sql
   SELECT cleanup_expired_cache();
   ```

3. **Clean up old analytics** (monthly)
   ```sql
   SELECT cleanup_old_analytics(90);  -- Keep 90 days
   ```

4. **Monitor performance**
   ```bash
   curl -H "X-API-Key: your-key" "https://dm-service-mpjf.onrender.com/analytics/dashboard"
   ```

5. **Check n8n execution logs** for errors

---

## Security Best Practices

1. **Validate Webhook Signatures** - Meta signs requests with your app secret
2. **Use HTTPS only** - Required by Meta
3. **Rate limit** incoming requests
4. **Store tokens securely** - Use environment variables, not code
5. **Regular token rotation** - Don't wait for expiry
6. **Monitor for abuse** - Track unusual patterns
7. **Implement request deduplication** - Meta may send duplicate webhooks

---

## Cost Optimization Tips

1. **Cache hit rate target**: 40%+ means healthy caching
2. **Skip AI for simple intents**: Greetings, thanks, goodbyes
3. **Batch similar queries**: Similar product searches use cache
4. **Monitor token usage**: Dashboard shows AI costs
5. **Optimize prompts**: Shorter prompts = lower costs

With this setup, expect **60-80% reduction** in OpenAI API costs compared to calling AI for every message.
