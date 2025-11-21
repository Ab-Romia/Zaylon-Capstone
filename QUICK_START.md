# Quick Start: Instagram DM Automation Setup

This is a condensed step-by-step checklist. For detailed instructions, see `SETUP_GUIDE.md`.

## Phase 1: Meta Developer Setup (Day 1-2)

### 1.1 Create Meta App
- [ ] Go to https://developers.facebook.com/apps
- [ ] Click "Create App"
- [ ] Select: Use case = **Other**, Type = **Business**
- [ ] App Name: `E-commerce DM Bot`
- [ ] Note down: **App ID** and **App Secret**

### 1.2 Add Instagram Product
- [ ] In App Dashboard, find "Add Products"
- [ ] Click "Set Up" under Instagram
- [ ] Navigate to Instagram > Basic Display > Settings

### 1.3 Request Permissions (THIS TAKES TIME)
Go to App Review > Permissions and Features:
- [ ] Request `instagram_basic`
- [ ] Request `instagram_manage_messages` **(CRITICAL - takes 7-30 days)**
- [ ] Request `pages_show_list`
- [ ] Request `pages_manage_metadata`

**For development:** Add your account as Test User under Roles > Test Users

### 1.4 Connect Instagram to Facebook Page
- [ ] Instagram Settings > Account > Linked Accounts > Facebook
- [ ] Link to your Facebook Page
- [ ] Ensure Instagram is **Business** or **Creator** account

### 1.5 Generate Tokens
```bash
# Step 1: Get short-lived user token from Graph API Explorer
# Go to: Tools > Graph API Explorer > Generate Access Token

# Step 2: Exchange for long-lived token (60 days)
curl "https://graph.facebook.com/v18.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_APP_ID&\
client_secret=YOUR_APP_SECRET&\
fb_exchange_token=YOUR_SHORT_TOKEN"

# Step 3: Get Page Access Token
curl "https://graph.facebook.com/v18.0/me/accounts?\
access_token=YOUR_LONG_LIVED_TOKEN"
# Note the "access_token" and "id" (Page ID) from response

# Step 4: Get Instagram Business Account ID
curl "https://graph.facebook.com/v18.0/YOUR_PAGE_ID?\
fields=instagram_business_account&\
access_token=YOUR_PAGE_ACCESS_TOKEN"
# Note the "instagram_business_account.id" value
```

**Save these values:**
```
META_APP_ID=
META_APP_SECRET=
PAGE_ACCESS_TOKEN=
PAGE_ID=
INSTAGRAM_BUSINESS_ACCOUNT_ID=
```

---

## Phase 2: Deploy Microservice (30 minutes)

### 2.1 Configure Environment
```bash
cd AI_Microservices
cp .env.example .env
```

Edit `.env`:
```bash
# IMPORTANT: Use postgresql+psycopg:// (NOT asyncpg) for Render compatibility
DATABASE_URL=postgresql+psycopg://USER:PASS@db.xxxx.supabase.co:5432/postgres
API_KEY=your-super-secure-api-key-minimum-32-chars
```

### 2.2 Apply Database Schema
In Supabase SQL Editor (https://app.supabase.com):
- [ ] Open SQL Editor
- [ ] Copy contents of `schema.sql`
- [ ] Click "Run"
- [ ] Verify tables created: conversations, customers, response_cache, analytics_events

### 2.3 Deploy to Render.com (Recommended - NO Credit Card Required)

**Why Render?** Free tier, no credit card required, simple GitHub deployment.

1. **Push to GitHub** (if not already):
```bash
git push origin main
```

2. **Create Render Account**:
   - Go to https://render.com
   - Sign up with GitHub (NO credit card needed!)

3. **Create Web Service**:
   - Click "New +" > "Web Service"
   - Connect your GitHub repo
   - Configure:
     - Name: `ecommerce-dm-service`
     - Region: `Frankfurt (EU)` (closest to Egypt)
     - Runtime: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - Instance Type: `Free`

4. **Add Environment Variables** (in Render dashboard > Environment):
```
DATABASE_URL = postgresql+psycopg://user:pass@db.supabase.co:5432/postgres
API_KEY = your-secure-api-key-32-chars
```
**IMPORTANT:** Use `postgresql+psycopg://` NOT `postgresql+asyncpg://`

5. **Deploy** - Click "Create Web Service"

**✅ Your Service is Already Deployed!**

**Production URL:** `https://dm-service-mpjf.onrender.com`

The microservice is live with:
- IPv4 database connection fix
- Automatic HTTPS
- Health monitoring
- Supabase integration

**Next Step:** Add your API key in Render Dashboard:
1. Go to https://dashboard.render.com
2. Select service: **dm-service-mpjf**
3. Environment tab → Add:
   - `API_KEY` = your-secret-key-123

**⚠️ IMPORTANT: Keep Service Awake**
Free tier sleeps after 15 min inactivity (cold start = 30-60s delay).

**Solution:** Use https://uptimerobot.com (free):
- Create monitor for `https://dm-service-mpjf.onrender.com/health`
- Set interval: 14 minutes
- This keeps your service always warm!

See `DEPLOYMENT_OPTIONS.md` for deploying your own instance.

### 2.4 Verify Deployment
```bash
# Check health (first request may be slow due to cold start)
curl https://dm-service-mpjf.onrender.com/health
# Should return: {"status": "healthy", "database": "connected", ...}

# Test product search
curl -X POST https://dm-service-mpjf.onrender.com/products/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "jeans", "limit": 3}'
```

**Microservice URL:** `https://dm-service-mpjf.onrender.com`

---

## Phase 3: n8n Workflow Setup (1-2 hours)

### 3.1 Set n8n Environment Variables
In your n8n instance (Settings > Variables or .env):
```
MICROSERVICE_URL=https://dm-service-mpjf.onrender.com
PAGE_ACCESS_TOKEN=your-page-access-token
INSTAGRAM_VERIFY_TOKEN=my_secure_verify_token_123
```

### 3.2 Create Credentials in n8n

**Credential 1: HTTP Header Auth (Microservice)**
- Go to Credentials > Add Credential > HTTP Header Auth
- Name: `Microservice API Key`
- Header Name: `X-API-Key`
- Header Value: `your-api-key`

**Credential 2: OpenAI API**
- Go to Credentials > Add Credential > OpenAI API
- Name: `OpenAI Account`
- API Key: `your-openai-api-key`

**Credential 3: Supabase API**
- Go to Credentials > Add Credential > Supabase API
- Name: `Supabase Account`
- Project URL: `https://your-project.supabase.co`
- Service Role Key: `your-service-role-key`

### 3.3 Import Verification Workflow
1. Go to Workflows > Import from File
2. Select `n8n_workflows/webhook_verification.json`
3. Update the verify token check to match your `INSTAGRAM_VERIFY_TOKEN`
4. **ACTIVATE** the workflow (toggle ON)
5. Note the webhook URL: `https://your-n8n.com/webhook/instagram-dm`

### 3.4 Configure Meta Webhook
1. Go to Meta App Dashboard > Products > Webhooks
2. Select "Instagram" from dropdown
3. Click "Subscribe to this object"
4. Enter:
   - **Callback URL:** `https://your-n8n.com/webhook/instagram-dm`
   - **Verify Token:** `my_secure_verify_token_123`
5. Click "Verify and Save"
6. If successful, subscribe to fields:
   - [x] `messages`
   - [x] `messaging_postbacks` (optional)

### 3.5 Import Main DM Handler Workflow
1. Import `n8n_workflows/instagram_dm_handler.json`
2. Update credential references:
   - Click "Prepare Context" node > Credentials > Select your HTTP Header Auth
   - Click "Store Interaction" node > Credentials > Select your HTTP Header Auth
   - Click "OpenAI Chat" node > Credentials > Select your OpenAI API
   - Click "Create Order in Supabase" node > Credentials > Select your Supabase API
3. Update URLs if needed:
   - "Prepare Context" URL should be: `{{ $env.MICROSERVICE_URL }}/n8n/prepare-context`
   - "Store Interaction" URL should be: `{{ $env.MICROSERVICE_URL }}/n8n/store-interaction`
4. **ACTIVATE** the workflow

---

## Phase 4: Testing (30 minutes)

### 4.1 Test Webhook Verification
```bash
curl "https://your-n8n.com/webhook/instagram-dm?\
hub.mode=subscribe&\
hub.verify_token=my_secure_verify_token_123&\
hub.challenge=test123"
# Should return: test123
```

### 4.2 Test Simulated Message
```bash
curl -X POST https://your-n8n.com/webhook/instagram-dm \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "id": "123456789",
      "time": 1234567890,
      "messaging": [{
        "sender": {"id": "TEST_SENDER_123"},
        "recipient": {"id": "YOUR_IG_ACCOUNT_ID"},
        "timestamp": '$(date +%s000)',
        "message": {
          "mid": "test_msg_123",
          "text": "السلام عليكم، عايز جينز ازرق سايز 32"
        }
      }]
    }]
  }'
```

Check:
- [ ] n8n shows execution in "Executions" tab
- [ ] Microservice logs show context preparation
- [ ] OpenAI was called (or response was cached)
- [ ] Response was stored in database

### 4.3 Test Real Instagram DM
1. Open Instagram app
2. Go to your business account's DM
3. Send: "مرحبا" (Arabic greeting)
4. Wait 2-5 seconds
5. You should receive an automated reply

### 4.4 Check Analytics
```bash
curl -H "X-API-Key: your-key" \
  "https://dm-service-mpjf.onrender.com/analytics/dashboard"
```

---

## Phase 5: Production Checklist

### Security
- [ ] API keys are strong (32+ characters)
- [ ] HTTPS everywhere
- [ ] Rate limiting configured
- [ ] No secrets in code

### Performance
- [ ] Microservice deployed close to users (Egypt = Europe region)
- [ ] Database connection pooling enabled
- [ ] Cache working (check cache_hit_rate)

### Compliance
- [ ] Privacy Policy URL added to Meta App
- [ ] Terms of Service URL added
- [ ] GDPR/data privacy compliant
- [ ] Instagram 24-hour messaging window understood

### Monitoring
- [ ] n8n execution logs accessible
- [ ] Microservice logs accessible
- [ ] Error notifications configured
- [ ] Token expiration alerts set (60-day tokens)

---

## Common Commands

**Refresh Page Access Token (every 60 days):**
```bash
curl "https://graph.facebook.com/v18.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=APP_ID&\
client_secret=APP_SECRET&\
fb_exchange_token=CURRENT_TOKEN"
```

**Check microservice health:**
```bash
curl https://dm-service-mpjf.onrender.com/health
```

**View analytics:**
```bash
curl -H "X-API-Key: key" https://dm-service-mpjf.onrender.com/analytics/dashboard
```

**Clean expired cache:**
```sql
SELECT cleanup_expired_cache();
```

**Test intent classification:**
```bash
curl -X POST https://dm-service-mpjf.onrender.com/intent/classify \
  -H "X-API-Key: key" \
  -H "Content-Type: application/json" \
  -d '{"message": "3ayez hoodie aswad size L"}'
```

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Webhook not verified | Ensure n8n workflow is ACTIVE |
| No messages received | Subscribe to "messages" field in Meta |
| Can't reply to user | Check Page Access Token is valid |
| 403 on microservice | Check X-API-Key header |
| AI not responding | Check OpenAI credentials in n8n |
| Orders not created | Check Supabase credentials and table exists |
| Slow responses | Check microservice logs, optimize DB queries |

---

## Expected Cost Savings

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Products sent to AI | 50 per message | 3-5 per message | 90% fewer tokens |
| AI calls for greetings | Every time | Cached/skipped | 100% saved |
| Conversation context | 3 messages | Full history | Better responses |
| Average tokens per message | ~2000 | ~500 | 75% reduction |
| **Estimated monthly cost** | $50-100 | $10-25 | **60-80% savings** |

---

## Next Steps After Setup

1. **Add more products** to your Supabase products table
2. **Train the system** by having test conversations
3. **Monitor analytics** to optimize cache and intents
4. **Expand keywords** in `services/intent.py` and `services/products.py`
5. **Add WhatsApp** channel (similar Meta setup)
6. **Custom responses** - Update suggested responses in intent patterns

---

**Need help?** Check the detailed `SETUP_GUIDE.md` or examine workflow execution logs in n8n.
