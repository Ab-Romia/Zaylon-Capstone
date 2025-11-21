# Instagram Cloud Testing Guide

## Overview

This guide shows you how to test Instagram DMs with your **cloud n8n** and **deployed Render microservice** WITHOUT having your Meta app go live.

**The Solution**: Use Instagram Test Users - Meta allows test accounts to send DMs to your page and receive webhooks even when the app is in Development Mode.

## Architecture

```
Instagram Test User → Sends DM → Your Instagram Page
                                         ↓
                                  Meta Graph API
                                         ↓
                              Webhooks (Development Mode)
                                         ↓
                                  Cloud n8n Webhook
                                         ↓
                              Deployed Render Microservice
                                         ↓
                                    RAG System
                                         ↓
                                  Response to Test User
```

## Prerequisites

- Meta Developer account
- Instagram Business/Creator account
- Facebook Page connected to Instagram
- n8n Cloud instance
- Render deployed microservice (already deployed)

---

## Step 1: Configure Meta App for Development Testing

### 1.1 Add Instagram Test Users

1. Go to [Meta Developers Console](https://developers.facebook.com)
2. Select your app
3. Go to **Roles** → **Test Users**
4. Click **Add Test Users** or **Create Test User**
5. Create 2-3 test users (free, unlimited)

### 1.2 Grant Test Users Instagram Access

1. Go to **Products** → **Instagram** → **Basic Display**
2. Under **User Token Generator**, add your test users
3. Note: Test users can interact with your Instagram Business account

### 1.3 Connect Test Users to Instagram

For each test user:
1. Login to Instagram with a test account (create new IG accounts if needed)
2. These accounts can DM your business page
3. Meta will send webhooks for DMs from test users **even in Development Mode**

---

## Step 2: Configure n8n Cloud Webhook

### 2.1 Get Your n8n Webhook URL

1. Login to your n8n Cloud instance
2. Create or open your Instagram DM workflow
3. Add a **Webhook** node (if not already added)
4. Set webhook path: `/webhook/instagram-dm`
5. Your webhook URL will be:
   ```
   https://your-instance.app.n8n.cloud/webhook/instagram-dm
   ```
6. **Important**: Set **Respond** to "Immediately" for webhook verification

### 2.2 Configure Webhook Verification in n8n

Your webhook node should handle Meta's verification challenge:

```javascript
// In n8n Webhook node
// Method: GET
// Response Mode: "When last node finishes"

// Add a Code node after webhook for verification:
if ($input.all()[0].json.query['hub.mode'] === 'subscribe') {
  const challenge = $input.all()[0].json.query['hub.verify_token'];
  const token = 'your_verify_token_12345'; // Same as in Meta app

  if ($input.all()[0].json.query['hub.verify_token'] === token) {
    // Return the challenge
    return {
      json: {
        'hub.challenge': parseInt($input.all()[0].json.query['hub.challenge'])
      }
    };
  }
}

// For POST requests (actual messages), continue to microservice
return $input.all();
```

---

## Step 3: Configure Meta App Webhooks

### 3.1 Add Webhook to Meta App

1. Go to **Products** → **Webhooks**
2. Select **Instagram** from dropdown
3. Click **Edit Subscription**
4. Enter your n8n webhook URL:
   ```
   https://your-instance.app.n8n.cloud/webhook/instagram-dm
   ```
5. Enter **Verify Token**: `your_verify_token_12345` (must match n8n workflow)
6. Click **Verify and Save**

### 3.2 Subscribe to Webhook Fields

Subscribe to these fields:
- ✅ `messages`
- ✅ `messaging_postbacks`
- ✅ `message_echoes`
- ✅ `messaging_handovers`

---

## Step 4: Configure n8n Workflow for Cloud Deployment

### 4.1 Update n8n Workflow

Your n8n workflow should have this structure:

```
1. Webhook Trigger (GET + POST)
   ↓
2. IF Node (Check if verification or message)
   ↓
   |→ Verification → Return hub.challenge
   ↓
   |→ Message → Extract data → HTTP Request to Render
   ↓
3. HTTP Request Node
   - URL: https://your-app.onrender.com/webhook/instagram
   - Method: POST
   - Body: Pass through webhook data
   ↓
4. Process Response
   ↓
5. Send Reply via Instagram Graph API
```

### 4.2 Full n8n Workflow JSON

<details>
<summary>Click to expand complete workflow</summary>

```json
{
  "name": "Instagram DM Handler - Cloud",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "=",
        "path": "instagram-dm",
        "options": {}
      },
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [250, 300],
      "webhookId": "instagram-dm-handler"
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.query['hub.mode'] }}",
              "value2": "subscribe"
            }
          ]
        }
      },
      "name": "Is Verification?",
      "type": "n8n-nodes-base.if",
      "position": [450, 300]
    },
    {
      "parameters": {
        "jsCode": "const challenge = $input.all()[0].json.query['hub.challenge'];\nconst verifyToken = $input.all()[0].json.query['hub.verify_token'];\nconst expectedToken = 'your_verify_token_12345';\n\nif (verifyToken === expectedToken) {\n  return [{ json: parseInt(challenge) }];\n} else {\n  throw new Error('Invalid verify token');\n}"
      },
      "name": "Return Challenge",
      "type": "n8n-nodes-base.code",
      "position": [650, 200]
    },
    {
      "parameters": {
        "url": "https://your-app.onrender.com/webhook/instagram",
        "options": {
          "timeout": 30000
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "=",
              "value": "={{ JSON.stringify($json.body) }}"
            }
          ]
        }
      },
      "name": "Call Render Microservice",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 400]
    },
    {
      "parameters": {
        "jsCode": "// Extract response from microservice\nconst response = $input.all()[0].json;\n\n// Prepare Instagram API request\nconst recipientId = response.recipient_id;\nconst message = response.message;\nconst pageAccessToken = '{{ $env.INSTAGRAM_PAGE_ACCESS_TOKEN }}';\n\nreturn [{\n  json: {\n    recipient: { id: recipientId },\n    message: { text: message },\n    access_token: pageAccessToken\n  }\n}];"
      },
      "name": "Prepare Instagram Reply",
      "type": "n8n-nodes-base.code",
      "position": [850, 400]
    },
    {
      "parameters": {
        "url": "=https://graph.facebook.com/v21.0/me/messages",
        "options": {},
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "recipient",
              "value": "={{ JSON.stringify($json.recipient) }}"
            },
            {
              "name": "message",
              "value": "={{ JSON.stringify($json.message) }}"
            },
            {
              "name": "access_token",
              "value": "={{ $json.access_token }}"
            }
          ]
        }
      },
      "name": "Send to Instagram",
      "type": "n8n-nodes-base.httpRequest",
      "position": [1050, 400]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [
        [
          {
            "node": "Is Verification?",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Is Verification?": {
      "main": [
        [
          {
            "node": "Return Challenge",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "Call Render Microservice",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Call Render Microservice": {
      "main": [
        [
          {
            "node": "Prepare Instagram Reply",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Prepare Instagram Reply": {
      "main": [
        [
          {
            "node": "Send to Instagram",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

</details>

### 4.3 Set n8n Environment Variables

In your n8n Cloud instance, add these environment variables:

1. Go to **Settings** → **Environment Variables**
2. Add:
   - `INSTAGRAM_PAGE_ACCESS_TOKEN` = Your Instagram page access token
   - `RENDER_MICROSERVICE_URL` = `https://your-app.onrender.com`
   - `VERIFY_TOKEN` = `your_verify_token_12345`

---

## Step 5: Get Instagram Page Access Token

### 5.1 Generate Long-Lived Token

1. Go to [Meta Developers Console](https://developers.facebook.com)
2. Navigate to **Tools** → **Graph API Explorer**
3. Select your app
4. Select your Instagram Business Account
5. Add permissions:
   - `pages_messaging`
   - `pages_manage_metadata`
   - `instagram_basic`
   - `instagram_manage_messages`
6. Click **Generate Access Token**
7. Copy the token

### 5.2 Exchange for Long-Lived Token (60 days)

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

Response:
```json
{
  "access_token": "LONG_LIVED_TOKEN",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

Use this `LONG_LIVED_TOKEN` in your n8n environment variables.

---

## Step 6: Test with Instagram Test Users

### 6.1 Send Test Messages

1. Login to Instagram with your test user account
2. Find your Instagram Business page
3. Send a DM to the page

**Test Messages** (try these):

```
# Test 1: Arabic greeting
السلام عليكم

# Test 2: Product search
عايز جينز ازرق

# Test 3: Franco-Arabic
Ana 3ayez shoes

# Test 4: English
Show me red dresses

# Test 5: Price inquiry
كم السعر؟

# Test 6: Knowledge base
What is your return policy?
```

### 6.2 What Happens

1. Test user sends DM → Your Instagram Business page
2. Meta sends webhook → n8n Cloud webhook
3. n8n processes → Calls Render microservice
4. Render microservice:
   - Runs RAG semantic search
   - Finds relevant products
   - Generates response
   - Returns to n8n
5. n8n sends reply → Instagram Graph API → Test user receives response

---

## Step 7: Monitor and Debug

### 7.1 Check n8n Executions

1. Go to n8n Cloud → **Executions**
2. You should see webhook triggers when test users send messages
3. Check each node's output for debugging

### 7.2 Check Render Logs

```bash
# If you have Render CLI
render logs -a your-app-name

# Or via Render Dashboard
# Go to your service → Logs tab
```

### 7.3 Check Meta Webhooks

1. Go to Meta Developers → **Webhooks**
2. Click **Test** to send test events
3. Check webhook delivery status

### 7.4 Common Issues

| Issue | Solution |
|-------|----------|
| Webhook verification fails | Check verify token matches in n8n and Meta app |
| No webhooks received | Ensure app is subscribed to correct fields |
| 403 errors | Check page access token permissions |
| Timeout errors | Increase n8n HTTP request timeout to 30s |
| Empty responses | Check Render microservice logs for errors |

---

## Step 8: Test RAG System

### 8.1 Index Products on Render

Make sure your Render microservice has products indexed:

```bash
# Call the indexing endpoint
curl -X POST https://your-app.onrender.com/rag/index/products \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key"
```

### 8.2 Add Knowledge Base Documents

```bash
# Index FAQ
curl -X POST https://your-app.onrender.com/rag/index/knowledge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "document_id": "faq_returns",
    "content": "Return Policy: You can return items within 14 days. Refunds processed within 5-7 business days.",
    "metadata": {
      "category": "returns",
      "language": "en"
    }
  }'
```

### 8.3 Verify RAG Status

```bash
curl https://your-app.onrender.com/rag/status \
  -H "X-API-Key: your-api-key"
```

Expected response:
```json
{
  "connected": true,
  "products_collection": {
    "points_count": 150,
    "status": "green"
  },
  "knowledge_collection": {
    "points_count": 25,
    "status": "green"
  },
  "embedding_dimension": 1536,
  "embedding_model": "text-embedding-3-small"
}
```

---

## Step 9: Advanced Testing Scenarios

### 9.1 Test Semantic Search

Send these messages to verify RAG is working:

```
# Scenario 1: Synonym search
"Looking for denim pants" → Should find "جينز" products

# Scenario 2: Color variants
"dark blue jeans" → Should find navy/blue jeans

# Scenario 3: Multi-language
"عايز حاجة للصيف" (want something for summer)
→ Should find summer clothes

# Scenario 4: Contextual
Message 1: "Show me shoes"
Message 2: "What sizes?"
→ Should reference shoes from previous message
```

### 9.2 Test Knowledge Base

```
# Returns policy
"How can I return?"
"What is the return policy?"
"عايز ارجع منتج" (want to return product)

# Shipping
"How long does shipping take?"
"Delivery time?"
"متى هيوصل الطلب؟" (when will order arrive?)

# Payment
"Do you accept cash on delivery?"
"Payment methods?"
```

### 9.3 Test Hybrid Search

Hybrid search combines semantic + keyword matching:

```
# This should use both:
"red nike shoes size 42"

Semantic: Understands "footwear", "crimson"
Keyword: Exact match "nike", "42"
```

---

## Step 10: Performance Monitoring

### 10.1 Check Response Times

In n8n executions, monitor:
- Webhook → Microservice: < 500ms
- Microservice processing: < 2s
- Reply sent: < 3s total

### 10.2 Monitor Render Metrics

1. Go to Render Dashboard → Your service
2. Check:
   - Response time (p95 should be < 2s)
   - Error rate (should be < 1%)
   - Memory usage (< 512MB)

### 10.3 Check Qdrant Performance

```bash
# Check collection stats
curl https://your-app.onrender.com/rag/status \
  -H "X-API-Key: your-api-key"
```

---

## Going Live Checklist

Once you've tested thoroughly with test users and are ready to go live:

### Before Submitting for Review

- [ ] Tested all message types (text, media, postbacks)
- [ ] Verified RAG responses are accurate
- [ ] Tested in Arabic, Franco-Arabic, English
- [ ] Confirmed knowledge base is populated
- [ ] Verified webhook reliability (no timeouts)
- [ ] Tested edge cases (empty messages, special chars)
- [ ] Set up monitoring and alerting
- [ ] Prepared privacy policy URL
- [ ] Prepared app review screencast

### Submit for App Review

1. Go to Meta Developers → **App Review**
2. Select **Permissions and Features**
3. Request:
   - `pages_messaging`
   - `instagram_manage_messages`
4. Provide:
   - Detailed use case description
   - Screencast showing your app
   - Privacy policy URL
5. Submit for review (usually takes 3-5 days)

### After Approval

1. Switch app mode from Development → Live
2. All Instagram users can now message your page
3. Webhooks will work for all users (not just test users)
4. Monitor performance and scale Render if needed

---

## Troubleshooting

### Issue: Webhooks Not Received

**Check:**
1. Webhook URL is correct in Meta app
2. n8n workflow is active (not paused)
3. Webhook verification succeeded
4. App subscribed to correct fields (`messages`)
5. Test user has permission to message your page

**Debug:**
```bash
# Check Meta webhook status
curl -X GET "https://graph.facebook.com/v21.0/YOUR_APP_ID/subscriptions?access_token=YOUR_APP_TOKEN"
```

### Issue: Render Microservice Timeout

**Solutions:**
1. Increase n8n HTTP request timeout:
   ```javascript
   options: {
     timeout: 30000  // 30 seconds
   }
   ```

2. Check Render service status:
   - Go to Render Dashboard
   - Check if service is sleeping (free tier)
   - Upgrade to paid tier for instant wake

3. Optimize RAG queries:
   - Reduce `rag_top_k` from 5 to 3
   - Lower similarity threshold

### Issue: Empty or Generic Responses

**Check:**
1. Products are indexed:
   ```bash
   curl https://your-app.onrender.com/rag/status
   ```

2. OpenAI API key is valid:
   ```bash
   # In Render dashboard → Environment
   # Verify OPENAI_API_KEY is set
   ```

3. Qdrant is running:
   ```bash
   # Check RAG status endpoint
   curl https://your-app.onrender.com/health
   ```

### Issue: Test Users Can't Message Page

**Solutions:**
1. Verify test user is linked to your Meta app
2. Ensure Instagram Business account is connected to Facebook page
3. Check page settings allow DMs
4. Test user Instagram account must be active (not banned)

---

## Cost Estimation

### Free Tier (Development/Testing)

- **n8n Cloud**: Free tier (5,000 executions/month)
- **Render**: Free tier (750 hours/month, sleeps after inactivity)
- **Qdrant Cloud**: Free tier (1GB, 100k vectors)
- **OpenAI**: Pay-as-you-go (~$0.10 per 1000 messages)

**Total for testing**: ~$0-5/month

### Production Tier (After Going Live)

- **n8n Cloud**: Starter $20/month (unlimited executions)
- **Render**: Starter $7/month (no sleep, 512MB RAM)
- **Qdrant Cloud**: Free tier sufficient for < 10k products
- **OpenAI**: ~$0.10 per 1000 messages

**Total for production**: ~$30-50/month + OpenAI usage

---

## Summary

You can now:

✅ Test Instagram DMs **without going live** using test users
✅ Use **cloud n8n** (no local setup needed)
✅ Connect to **deployed Render microservice**
✅ Test **RAG semantic search** with real queries
✅ Verify **multilingual support** (Arabic, Franco-Arabic, English)
✅ Monitor **performance and errors**
✅ Prepare for **production launch**

**Key Advantage**: Test users can send DMs and receive webhooks even when your Meta app is in Development Mode - no app review needed for testing!

---

## Next Steps

1. Set up test users in Meta Developers Console
2. Configure n8n Cloud webhook
3. Connect Meta app webhooks to n8n
4. Send test messages from test users
5. Verify RAG responses are accurate
6. Test for 1-2 weeks with various scenarios
7. Submit app for review when ready
8. Go live! 🚀

**Questions?** Check the troubleshooting section or review Render logs for errors.
