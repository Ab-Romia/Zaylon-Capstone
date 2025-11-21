# Complete Instagram DM Automation Setup Guide

## 🎯 What Was Fixed in the Workflow

### Issues Fixed:
1. ✅ **OpenAI node** - Configured with proper system prompt and context injection
2. ✅ **Create Order in Supabase** - Added all field mappings
3. ✅ **Send Instagram Reply** - Fixed Meta API authentication
4. ✅ **AI Agent** - Configured with Egyptian e-commerce context
5. ✅ **Merge node** - Fixed to use `combineByPosition` mode
6. ✅ **Error handling** - Returns 200 status even on errors (Meta requirement)

---

## 📋 Prerequisites

- [ ] n8n instance (cloud or self-hosted)
- [ ] Supabase account
- [ ] OpenAI API key
- [ ] Meta Developer account
- [ ] Instagram Business account
- [ ] Microservice running at https://dm-service-mpjf.onrender.com

---

## Part 1: Supabase Database Setup

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Click **New Project**
3. Name it: `ecommerce-dm`
4. Choose a database password (save it!)
5. Select region: **closest to your users**
6. Click **Create new project**

### Step 2: Run Database Schema

1. In Supabase Dashboard → **SQL Editor**
2. Click **New Query**
3. Paste the complete schema from `/AI_Microservices/schema.sql`:

```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Products table (your existing products)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    price FLOAT NOT NULL,
    sizes TEXT[] DEFAULT '{}',
    colors TEXT[] DEFAULT '{}',
    stock_count INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    product_name VARCHAR(255),
    size VARCHAR(50),
    color VARCHAR(50),
    quantity INTEGER DEFAULT 1,
    total_price FLOAT,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(50),
    delivery_address TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    instagram_user VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Conversations table (microservice uses this)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    direction VARCHAR(20) NOT NULL,
    intent VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_created ON conversations(created_at);
CREATE INDEX idx_conversations_customer_created ON conversations(customer_id, created_at);

-- Customers table (for cross-channel linking)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_id VARCHAR(255) UNIQUE NOT NULL,
    linked_ids JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customers_primary ON customers(primary_id);

-- Response cache table
CREATE TABLE IF NOT EXISTS response_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_hash VARCHAR(64) UNIQUE NOT NULL,
    normalized_message TEXT NOT NULL,
    cached_response TEXT NOT NULL,
    intent VARCHAR(100),
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cache_hash ON response_cache(message_hash);
CREATE INDEX idx_cache_expires ON response_cache(expires_at);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    response_time_ms INTEGER,
    ai_tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_customer ON analytics_events(customer_id);
CREATE INDEX idx_analytics_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_created ON analytics_events(created_at);
CREATE INDEX idx_analytics_type_created ON analytics_events(event_type, created_at);
```

4. Click **Run**
5. Verify all tables created successfully

### Step 3: Add Sample Products

```sql
INSERT INTO products (name, price, sizes, colors, stock_count, description) VALUES
('Blue Hoodie', 599.00, ARRAY['S', 'M', 'L', 'XL'], ARRAY['blue', 'navy'], 50, 'Comfortable cotton hoodie'),
('Black Jeans', 799.00, ARRAY['28', '30', '32', '34', '36'], ARRAY['black', 'dark blue'], 30, 'Classic fit jeans'),
('White T-Shirt', 299.00, ARRAY['S', 'M', 'L', 'XL'], ARRAY['white', 'off-white'], 100, 'Basic cotton t-shirt'),
('Red Sweatshirt', 549.00, ARRAY['M', 'L', 'XL'], ARRAY['red', 'burgundy'], 25, 'Warm winter sweatshirt');
```

### Step 4: Get Supabase Credentials

1. Go to **Settings** → **API**
2. Note down:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public key**: `eyJhbGc...` (for public access)
   - **service_role secret**: `eyJhbGc...` (for n8n - full access)

3. Go to **Settings** → **Database**
4. Get **Connection String** → **Session Mode** (for microservice):
   ```
   postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```

---

## Part 2: Microservice Configuration

### Step 1: Add Environment Variables in Render

1. Go to https://dashboard.render.com
2. Select service: **dm-service-mpjf**
3. Go to **Environment** tab
4. Add these variables:

```bash
# Required
API_KEY=your-secret-key-here-make-it-long-and-random
DATABASE_URL=postgresql+asyncpg://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres

# Optional (defaults work fine)
RATE_LIMIT_PER_MINUTE=100
DEFAULT_CACHE_TTL_HOURS=24
MAX_CONVERSATION_HISTORY=50
MAX_PRODUCT_SEARCH_RESULTS=5
DEBUG=false
```

5. Click **Save Changes**
6. Service will automatically redeploy

### Step 2: Verify Microservice

```bash
# Test health
curl https://dm-service-mpjf.onrender.com/health

# Should return:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "timestamp": "2025-11-18T..."
}
```

---

## Part 3: n8n Workflow Setup

### Step 1: Import Workflow

1. Open your n8n instance
2. **Workflows** → **Add Workflow**
3. Click **⋮** menu → **Import from File**
4. Select: `instagram_dm_workflow_PERFECTED.json`
5. Workflow imported! ✅

### Step 2: Configure Credentials

#### A. Microservice API Key (Header Auth)

1. **Credentials** → **Add Credential**
2. Search: **Header Auth**
3. Configure:
   - **Name**: `Microservice API Key`
   - **Header Name**: `X-API-Key`
   - **Header Value**: `your-secret-key-here` (same as Render API_KEY)
4. **Save**

#### B. OpenAI Credentials

1. **Add Credential** → Search: **OpenAI**
2. Configure:
   - **Name**: `OpenAI Account`
   - **API Key**: Get from https://platform.openai.com/api-keys
3. **Save**

**Cost Estimate:**
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Average message: ~500 tokens = $0.0004 per message
- 1000 messages ≈ $0.40

#### C. Supabase Credentials

1. **Add Credential** → Search: **Supabase**
2. Configure:
   - **Name**: `Supabase Account`
   - **Host**: `https://xxxxx.supabase.co`
   - **Service Role Secret**: `eyJhbGc...` (from Supabase Settings → API)
3. **Save**

#### D. Meta Page Access Token (Environment Variable)

Instead of using credentials, we'll use an environment variable for security:

1. In n8n **Settings** → **Environment Variables**
2. Add:
   ```
   PAGE_ACCESS_TOKEN=your_meta_page_access_token
   ```

**How to get Page Access Token:**

1. Go to https://developers.facebook.com/apps
2. Select your app
3. **Messenger** → **Settings**
4. Under "Access Tokens", select your Instagram page
5. Click **Generate Token**
6. **IMPORTANT**: This is short-lived (1-2 hours). For production, you need a long-lived token:

   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
   ```

7. This returns a long-lived token (60 days)

### Step 3: Assign Credentials to Nodes

Go through the workflow and assign credentials:

1. **Prepare Context (Microservice)** node:
   - Authentication → Select: `Microservice API Key`

2. **OpenAI GPT-4o-mini** node:
   - Credentials → Select: `OpenAI Account`

3. **Store Interaction (Microservice)** node:
   - Authentication → Select: `Microservice API Key`

4. **Create Order in Supabase** node:
   - Credentials → Select: `Supabase Account`

5. **Send Instagram Reply** node:
   - Already configured to use `$env.PAGE_ACCESS_TOKEN`
   - Make sure environment variable is set

### Step 4: Test the Workflow

1. Click **Execute Workflow** (don't activate yet)
2. In another terminal, simulate a Meta webhook:

```bash
curl -X POST "https://your-n8n.app.n8n.cloud/webhook/instagram-dm" \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "messaging": [{
        "sender": {"id": "test_sender_123"},
        "recipient": {"id": "your_page_id"},
        "timestamp": 1234567890,
        "message": {
          "mid": "test_message_id",
          "text": "Hello, I want to order a blue hoodie"
        }
      }]
    }]
  }'
```

3. Check n8n execution:
   - ✅ Extract Message Data → should parse correctly
   - ✅ Prepare Context → should return products and intent
   - ✅ OpenAI → should generate response
   - ✅ Store Interaction → should save to microservice
   - ✅ Success Response → should return 200

---

## Part 4: Instagram Webhook Setup

### Step 1: Get Webhook URL

1. In n8n workflow, click **Instagram Webhook** node
2. Copy the **Production URL**:
   ```
   https://your-n8n.app.n8n.cloud/webhook/instagram-dm
   ```

### Step 2: Configure Meta Webhook

1. Go to https://developers.facebook.com/apps
2. Select your app
3. **Products** → **Webhooks**
4. Find **Instagram** → Click **Edit**
5. Configure:
   - **Callback URL**: Your n8n webhook URL
   - **Verify Token**: Create a random string (e.g., `my_verify_token_12345`)
6. **BEFORE clicking Verify**, create verification workflow...

### Step 3: Create Verification Workflow

Create a separate workflow for webhook verification:

1. **New Workflow** → Name: "Instagram Webhook Verification"
2. Add **Webhook** node:
   - HTTP Method: `GET`
   - Path: `instagram-dm` (same as main webhook)
   - Response Mode: `Using 'Respond to Webhook' Node`

3. Add **Respond to Webhook** node:
   - Respond With: `Text`
   - Response Body: `={{ $json.query['hub.challenge'] }}`

4. **Activate this workflow**

### Step 4: Verify in Meta

1. Go back to Meta Webhooks page
2. Click **Verify and Save**
3. Meta will send GET request to your webhook
4. Should verify successfully! ✅

### Step 5: Subscribe to Events

After verification, subscribe to:
- ✅ `messages` (most important!)
- ✅ `messaging_postbacks`
- ✅ `messaging_optins`

### Step 6: Activate Main Workflow

1. Go to your main workflow
2. Toggle **Active** ON (top-right corner)
3. Workflow is now live! 🎉

---

## Part 5: Testing the Complete Integration

### Test 1: Send a Message

1. Send a DM to your Instagram business account:
   ```
   "Hello"
   ```

2. Expected behavior:
   - ✅ Microservice returns cached greeting
   - ✅ No OpenAI call (saves money!)
   - ✅ Instant response

### Test 2: Product Inquiry

Send:
```
"Show me blue hoodies"
```

Expected:
- ✅ Microservice searches products
- ✅ OpenAI gets product context
- ✅ Response lists available hoodies
- ✅ Conversation saved

### Test 3: Place an Order

Conversation:
```
Customer: "I want to order a blue hoodie"
Bot: "Great! What size would you like?"
Customer: "Large please"
Bot: "Perfect! Can I get your full name?"
Customer: "Ahmed Hassan"
Bot: "And your phone number?"
Customer: "+201234567890"
Bot: "Lastly, your delivery address?"
Customer: "123 Tahrir St, Cairo"
Bot: "Order confirmed! Your blue hoodie size L will be delivered to 123 Tahrir St, Cairo. Total: 599 EGP"
```

Expected:
- ✅ Order created in Supabase `orders` table
- ✅ Customer receives confirmation
- ✅ Analytics logged

### Test 4: Check Analytics

```bash
curl -X GET "https://dm-service-mpjf.onrender.com/analytics/dashboard" \
  -H "X-API-Key: your-secret-key"
```

Shows:
- Total messages
- Orders created
- Conversion rate
- Cache hit rate
- AI costs

---

## 🎯 Production Checklist

### Credentials
- [ ] Microservice API Key configured
- [ ] OpenAI API Key added
- [ ] Supabase credentials added
- [ ] Meta Page Access Token (long-lived)

### Database
- [ ] Supabase project created
- [ ] All tables created (schema.sql executed)
- [ ] Sample products added
- [ ] Database connection verified

### Microservice
- [ ] Running at https://dm-service-mpjf.onrender.com
- [ ] Environment variables configured
- [ ] Health check passes
- [ ] Products API works

### n8n Workflow
- [ ] Workflow imported
- [ ] All credentials assigned
- [ ] Test execution successful
- [ ] Workflow activated

### Instagram
- [ ] Webhook verified
- [ ] Events subscribed
- [ ] Test message successful
- [ ] Order creation works

### Monitoring
- [ ] Analytics dashboard accessible
- [ ] n8n execution logs checked
- [ ] Render service logs reviewed

---

## 📊 Expected Performance

| Metric | Expected Value |
|--------|---------------|
| Response Time (cached) | < 500ms |
| Response Time (AI) | 2-4 seconds |
| Cache Hit Rate | 60-80% |
| AI Cost per 1000 msgs | ~$0.40 |
| Order Conversion | 5-15% |

---

## 🐛 Troubleshooting

### Issue: "Authentication failed" on microservice

**Fix:**
- Verify API_KEY in Render matches n8n credential
- Check Header Auth credential has correct header name: `X-API-Key`

### Issue: OpenAI returns markdown instead of JSON

**Fix:**
- Already handled by Parse AI Response node
- Strips ```json markdown automatically

### Issue: Order not created in Supabase

**Fix:**
- Check product_id exists in products table
- Verify all required fields present
- Check Supabase credentials (service_role, not anon key)

### Issue: Instagram message not received

**Fix:**
- Verify webhook is Active (not just executed once)
- Check Meta webhook subscriptions include `messages`
- Test with curl to verify webhook responds

### Issue: "skip_ai is undefined"

**Fix:**
- Microservice not responding correctly
- Check Prepare Context node output
- Verify DATABASE_URL in Render is correct (Session Mode)

---

## 🚀 Next Steps

1. **Add More Products** - Populate Supabase with your inventory
2. **Customize AI Prompts** - Edit OpenAI node to match your brand voice
3. **Monitor Performance** - Check analytics dashboard daily
4. **Scale Up** - Upgrade Render and n8n plans for production traffic
5. **Add WhatsApp** - Duplicate workflow for WhatsApp Business API

---

## 📚 Additional Resources

- **Microservice API Docs**: https://dm-service-mpjf.onrender.com/docs
- **n8n Documentation**: https://docs.n8n.io
- **Meta Webhooks**: https://developers.facebook.com/docs/messenger-platform/webhooks
- **Supabase Docs**: https://supabase.com/docs

---

**Your Instagram DM Automation is now production-ready! 🎉**

For support, check:
- Render logs: https://dashboard.render.com
- n8n executions: Your n8n dashboard
- Microservice analytics: https://dm-service-mpjf.onrender.com/analytics/dashboard
