# n8n Workflow Setup Guide

## Overview
This guide will help you set up the Instagram DM automation workflow that integrates with your deployed microservice.

## Prerequisites

1. **n8n Instance** - Cloud or self-hosted
2. **Microservice Deployed** - https://dm-service-mpjf.onrender.com
3. **Meta Business Account** - With Instagram messaging enabled
4. **Supabase Account** - With products and orders tables
5. **OpenAI API Key** - For GPT-4 responses

---

## Step 1: Import Workflow

1. Open your n8n instance
2. Go to **Workflows** → **Add Workflow**
3. Click the **⋮** menu → **Import from File**
4. Select: `instagram_dm_handler_updated.json`
5. The workflow will be imported

---

## Step 2: Set Up Credentials

### A. Microservice API Key

1. In n8n, go to **Credentials** → **Add Credential**
2. Search for **Header Auth**
3. Configure:
   - **Name**: `Microservice API Key`
   - **Header Name**: `X-API-Key`
   - **Header Value**: `YOUR_API_KEY_FROM_RENDER`
4. **Save**

**How to get your API key:**
- Go to Render Dashboard → Your Service → Environment
- Find or add `API_KEY` variable
- Use that value here

---

### B. OpenAI Credentials

1. Add Credential → Search **OpenAI**
2. Configure:
   - **Name**: `OpenAI`
   - **API Key**: Your OpenAI API key from https://platform.openai.com/api-keys
3. **Save**

---

### C. Supabase Credentials

1. Add Credential → Search **Supabase**
2. Configure:
   - **Name**: `Supabase`
   - **Host**: `https://YOUR-PROJECT.supabase.co`
   - **Service Role Secret**: From Supabase Dashboard → Settings → API
3. **Save**

---

### D. Meta Business (Facebook/Instagram) Credentials

1. Add Credential → Search **Meta for Business**
2. Configure:
   - **Name**: `Meta Business`
   - **Access Token**: Your Page Access Token
3. **Save**

**How to get Page Access Token:**
1. Go to https://developers.facebook.com/apps
2. Select your app → Settings → Basic
3. Go to **Messenger** → **Settings**
4. Generate Page Access Token (select your Instagram page)
5. Copy the token

---

## Step 3: Configure Workflow Nodes

### Update These Nodes:

#### 1. **Prepare Context (Microservice)** - Node ID: `prepare-context`
- **URL**: Already set to `https://dm-service-mpjf.onrender.com/n8n/prepare-context`
- **Authentication**: Select your `Microservice API Key` credential
- ✅ No changes needed if using the updated workflow

#### 2. **Store Interaction (Microservice)** - Node ID: `store-interaction`
- **URL**: Already set to `https://dm-service-mpjf.onrender.com/n8n/store-interaction`
- **Authentication**: Select your `Microservice API Key` credential
- ✅ No changes needed

#### 3. **OpenAI GPT-4** - Node ID: `openai-chat`
- **Credentials**: Select your `OpenAI` credential
- **Model**: `gpt-4-turbo-preview` (or `gpt-4` if you prefer)
- **Temperature**: 0.7
- **Max Tokens**: 800

#### 4. **Create Order in Supabase** - Node ID: `create-order`
- **Credentials**: Select your `Supabase` credential
- **Table**: `orders`
- ✅ Fields are already mapped

#### 5. **Send Instagram Reply** - Node ID: `send-instagram-reply`
- **Credentials**: Select your `Meta Business` credential
- ✅ Endpoint already configured

---

## Step 4: Set Up Instagram Webhook

### A. Get Webhook URL

1. In the workflow, click on **Instagram Webhook** node
2. Copy the **Webhook URL** (looks like: `https://your-n8n.com/webhook/instagram-dm`)
3. Save this URL

### B. Configure Meta App Webhook

1. Go to https://developers.facebook.com/apps
2. Select your app
3. Go to **Products** → **Webhooks**
4. Click **Edit** next to Instagram
5. Configure:
   - **Callback URL**: Your webhook URL from step A
   - **Verify Token**: Create a random string (e.g., `my_verify_token_123`)
6. **Subscribe to fields:**
   - ✅ `messages`
   - ✅ `messaging_postbacks`
7. **Verify and Save**

### C. Update Webhook Verification (if needed)

If Meta requires webhook verification:

1. Import the `webhook_verification.json` workflow
2. Update the verify token to match what you set in Meta
3. Activate it
4. Re-verify in Meta dashboard

---

## Step 5: Test the Workflow

### Test Mode (Manual Testing)

1. Click **Execute Workflow** button in n8n
2. The workflow is now listening
3. Send a message to your Instagram business account
4. Check the execution in n8n

### Production Mode

1. Click **Active** toggle in top-right corner
2. The workflow is now live and running 24/7
3. All Instagram messages will be processed automatically

---

## Step 6: Monitor & Debug

### Check Execution Logs

1. Go to **Executions** tab
2. View each execution with status (success/error)
3. Click on any execution to see detailed flow

### Common Issues & Fixes

#### ❌ "Authentication failed" on Microservice calls
**Fix**: Check API key in Render environment variables matches n8n credential

#### ❌ "skip_ai is undefined"
**Fix**: Ensure Prepare Context response is being parsed correctly. Check node outputs.

#### ❌ OpenAI returns markdown instead of JSON
**Fix**: The Parse AI Response node handles this automatically with markdown cleanup

#### ❌ Order not created in Supabase
**Fix**:
- Verify Supabase credentials
- Check `product_id` exists in products table
- Ensure all required fields are present

#### ❌ Message not sent to Instagram
**Fix**:
- Verify Page Access Token is valid
- Check token has `pages_messaging` permission
- Ensure Instagram account is connected to your Facebook Page

---

## Workflow Flow Diagram

```
Instagram Message
    ↓
Extract Message Data
    ↓
Should Skip? (Invalid messages)
    ├─ Yes → Skip Response
    └─ No ↓
Prepare Context (Microservice)
    ├─ Checks cache
    ├─ Gets conversation history
    ├─ Searches products
    └─ Classifies intent
    ↓
Skip AI? (Cached response available)
    ├─ Yes → Use Cached Response
    └─ No → OpenAI GPT-4
    ↓
Parse AI Response
    ↓
Merge Responses
    ↓
Store Interaction (Microservice)
    ├─ Saves conversation
    ├─ Caches response
    └─ Logs analytics
    ↓
Should Create Order?
    ├─ Yes → Create Order in Supabase
    └─ No → Skip
    ↓
Send Instagram Reply
    ↓
Success Response
```

---

## Environment Variables for n8n

Set these in your n8n instance:

```bash
# Optional: If you want to use environment variables
MICROSERVICE_URL=https://dm-service-mpjf.onrender.com
PAGE_ACCESS_TOKEN=your_meta_page_access_token
```

You can reference them in nodes with: `{{ $env.MICROSERVICE_URL }}`

---

## What the Microservice Does

### `/n8n/prepare-context` endpoint:
✅ Checks cache for instant responses
✅ Retrieves customer conversation history
✅ Searches relevant products from message
✅ Classifies intent (order, inquiry, greeting, etc.)
✅ Extracts entities (product, size, color, phone)
✅ Returns everything formatted for AI

### `/n8n/store-interaction` endpoint:
✅ Saves conversation message to database
✅ Caches response for future use
✅ Logs analytics (response time, tokens, events)
✅ Updates customer metadata

**Benefits:**
- 🚀 Smart caching saves OpenAI costs
- 📊 Full analytics and tracking
- 🔍 Automatic product search
- 💬 Cross-channel conversation history
- 🎯 Intent-based routing

---

## Next Steps

1. ✅ Import workflow
2. ✅ Set up all credentials
3. ✅ Configure Meta webhook
4. ✅ Test with a message
5. ✅ Activate workflow
6. 📊 Monitor analytics at: `https://dm-service-mpjf.onrender.com/analytics/dashboard`

---

## Support & Troubleshooting

### View Microservice Logs
- Go to Render Dashboard → Your Service → Logs
- Look for IPv4 resolution and database connection messages

### View Analytics Dashboard
```bash
curl -X GET "https://dm-service-mpjf.onrender.com/analytics/dashboard" \
  -H "X-API-Key: your-api-key"
```

Shows:
- Total messages & orders
- Conversion rate
- Cache hit rate
- Popular products
- AI cost estimate

### Test Microservice Directly
```bash
# Test prepare-context
curl -X POST "https://dm-service-mpjf.onrender.com/n8n/prepare-context" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "customer_id": "test:user",
    "channel": "instagram",
    "message": "Hello"
  }'
```

---

## Production Checklist

- [ ] All credentials configured and tested
- [ ] Webhook verified with Meta
- [ ] Test message successfully processed
- [ ] Order creation tested in Supabase
- [ ] Instagram reply sent successfully
- [ ] Analytics dashboard accessible
- [ ] Workflow activated
- [ ] Error handling tested
- [ ] Products added to Supabase
- [ ] API rate limits understood (100/min default)

**You're all set! 🎉**

Your Instagram DM automation is now powered by AI with smart caching, product search, and full analytics tracking.
