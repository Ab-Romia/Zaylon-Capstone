# Cloud Setup Quick Start

## Overview

Get your Instagram DM bot running with **cloud n8n** + **Render microservice** in 15 minutes, without going live on Meta.

---

## Prerequisites

- [x] Render account with deployed microservice
- [x] n8n Cloud account
- [x] Meta Developer account
- [x] Instagram Business account
- [x] Facebook Page connected to Instagram

---

## Quick Setup (5 Steps)

### Step 1: Get Your URLs (2 min)

**Render Microservice URL:**
```
https://your-app-name.onrender.com
```

**n8n Cloud Webhook URL:**
```
https://your-instance.app.n8n.cloud/webhook/instagram-dm
```

### Step 2: Configure n8n Cloud (5 min)

1. **Import Workflow:**
   - Login to n8n Cloud
   - Click **Workflows** → **Import from File**
   - Upload: `n8n_workflows/instagram_dm_cloud_workflow.json`

2. **Set Environment Variables:**
   - Go to **Settings** → **Environments**
   - Add these variables:
     ```
     RENDER_MICROSERVICE_URL=https://your-app.onrender.com
     INSTAGRAM_PAGE_ACCESS_TOKEN=your_page_access_token
     VERIFY_TOKEN=my_secret_verify_token_12345
     MICROSERVICE_API_KEY=your_api_key_here
     ```

3. **Activate Workflow:**
   - Click **Active** toggle (top right)
   - Copy the webhook URL shown

### Step 3: Configure Meta Developer App (5 min)

1. **Add Webhooks:**
   - Go to [Meta Developers](https://developers.facebook.com)
   - Select your app → **Products** → **Webhooks**
   - Select **Instagram** from dropdown
   - Click **Edit Subscription**
   - Callback URL: `https://your-instance.app.n8n.cloud/webhook/instagram-dm`
   - Verify Token: `my_secret_verify_token_12345` (same as n8n)
   - Click **Verify and Save**

2. **Subscribe to Fields:**
   - Select these fields:
     - ✅ `messages`
     - ✅ `messaging_postbacks`
   - Click **Save**

### Step 4: Get Page Access Token (2 min)

1. Go to **Graph API Explorer**
2. Select your app
3. Add permissions:
   - `pages_messaging`
   - `instagram_manage_messages`
4. Click **Generate Access Token**
5. Copy token and add to n8n environment variables

### Step 5: Test with Test Users (1 min)

1. **Create Test User:**
   - Meta Developers → **Roles** → **Test Users**
   - Click **Add** → Create new test user
   - Login to Instagram with a test account

2. **Send Test Message:**
   - Open Instagram
   - Find your business page
   - Send DM: "السلام عليكم" or "Hi"

3. **Check Results:**
   - n8n Cloud → **Executions** (should show new execution)
   - Instagram → Should receive response

✅ **Done! Your bot is working!**

---

## Test Messages

Try these to test different features:

```
# Arabic greeting
السلام عليكم

# Product search (semantic RAG)
عايز جينز ازرق

# Franco-Arabic
Ana 3ayez shoes

# Price inquiry
كم السعر؟

# Knowledge base
What is your return policy?
```

---

## Environment Variables Reference

### n8n Cloud Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `RENDER_MICROSERVICE_URL` | Your Render app URL | `https://myapp.onrender.com` |
| `INSTAGRAM_PAGE_ACCESS_TOKEN` | Instagram page token | `EAAxx...` (long string) |
| `VERIFY_TOKEN` | Webhook verification | `my_secret_123` |
| `MICROSERVICE_API_KEY` | API key for your service | Your API key |

### Render Environment Variables

These should already be set in your Render deployment:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection | Auto-set by Render |
| `QDRANT_URL` | Qdrant vector DB | `http://localhost:6333` or cloud |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `API_KEY` | Microservice API key | Your secret key |

---

## Troubleshooting

### Webhook Verification Fails

**Error:** "The URL couldn't be validated. Callback verification failed with the following errors..."

**Fix:**
1. Check `VERIFY_TOKEN` matches in both n8n and Meta app
2. Ensure n8n workflow is **Active** (green toggle)
3. Test the webhook URL directly:
   ```bash
   curl "https://your-instance.app.n8n.cloud/webhook/instagram-dm?hub.mode=subscribe&hub.verify_token=my_secret_verify_token_12345&hub.challenge=1234"
   ```
   Should return: `1234`

### No Response from Bot

**Check:**
1. **n8n Executions:** Go to n8n → Executions → Check for errors
2. **Render Logs:** Go to Render → Your service → Logs
3. **Products Indexed:**
   ```bash
   curl https://your-app.onrender.com/rag/status
   ```

### Render Service Sleeping (Free Tier)

**Problem:** First request takes 30+ seconds

**Solutions:**
1. **Upgrade to Paid:** $7/month for instant wake
2. **Keep-alive Ping:** Use UptimeRobot to ping every 5 minutes:
   ```
   https://your-app.onrender.com/health
   ```
3. **Accept Delay:** First message slow, subsequent fast

### Test User Can't Message Page

**Fix:**
1. Instagram account must be Business/Creator
2. Page must be connected to Instagram
3. DMs must be enabled in Instagram settings
4. Test user must be added to app roles

---

## Next Steps

### 1. Index Your Products

```bash
# Index all products
curl -X POST https://your-app.onrender.com/rag/index/products \
  -H "X-API-Key: your_api_key"
```

### 2. Add Knowledge Base

```bash
# Add FAQ documents
curl -X POST https://your-app.onrender.com/rag/index/knowledge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "document_id": "faq_returns",
    "content": "Return Policy: Items can be returned within 14 days...",
    "metadata": {"category": "returns", "language": "en"}
  }'
```

### 3. Monitor Performance

- **n8n:** Check executions for errors
- **Render:** Monitor logs and metrics
- **RAG Status:** Check `/rag/status` endpoint

### 4. Test Thoroughly

Use test users to verify:
- ✅ Arabic queries work
- ✅ Franco-Arabic understood
- ✅ Product search returns relevant results
- ✅ Knowledge base answers questions
- ✅ Context maintained across messages
- ✅ Response time < 3 seconds

### 5. Go Live

When ready:
1. Submit app for Meta review (App Review → Request permissions)
2. Provide screencast and use case description
3. Wait 3-5 days for approval
4. Switch app to Live mode
5. All users can now message your page!

---

## Cost Breakdown

### Free Tier (Testing)

- n8n Cloud: Free (5,000 executions/month)
- Render: Free (sleeps after inactivity)
- Qdrant: Free tier (1GB)
- OpenAI: Pay-as-you-go (~$0.10/1000 messages)

**Total:** ~$0-5/month

### Paid Tier (Production)

- n8n Cloud: $20/month (unlimited)
- Render: $7/month (no sleep, 512MB)
- Qdrant: Free tier OK
- OpenAI: ~$0.10/1000 messages

**Total:** ~$30/month + usage

---

## Architecture Diagram

```
┌─────────────────┐
│ Instagram User  │
│ (Test Account)  │
└────────┬────────┘
         │ Sends DM
         ▼
┌─────────────────┐
│ Instagram Page  │
│ (Your Business) │
└────────┬────────┘
         │ Webhook Event
         ▼
┌─────────────────┐
│  Meta Graph API │
└────────┬────────┘
         │ POST /webhook
         ▼
┌─────────────────┐
│   n8n Cloud     │
│  ┌───────────┐  │
│  │ Webhook   │  │
│  │ Handler   │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Extract   │  │
│  │ Message   │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Call      │  │
│  │ Render    │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│ Render Service  │
│  ┌───────────┐  │
│  │ FastAPI   │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ RAG       │  │
│  │ System    │  │
│  │           │  │
│  │ ┌───────┐ │  │
│  │ │Qdrant │ │  │
│  │ └───────┘ │  │
│  │           │  │
│  │ ┌───────┐ │  │
│  │ │OpenAI │ │  │
│  │ └───────┘ │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │ Response
         ▼
┌─────────────────┐
│   n8n Cloud     │
│  ┌───────────┐  │
│  │ Send to   │  │
│  │ Instagram │  │
│  └─────┬─────┘  │
└────────┼────────┘
         │ POST to Graph API
         ▼
┌─────────────────┐
│  Meta Graph API │
└────────┬────────┘
         │ Delivers message
         ▼
┌─────────────────┐
│ Instagram User  │
│ Receives Reply  │
└─────────────────┘
```

---

## Support

- **Full Guide:** See `INSTAGRAM_CLOUD_TESTING.md` for detailed documentation
- **RAG Implementation:** See `RAG_IMPLEMENTATION_GUIDE.md`
- **Deployment:** See `RENDER_RAG_DEPLOYMENT.md`

---

**You're all set! Start testing with Instagram test users now! 🚀**
