# Complete Deployment Guide - AI Microservices with n8n Automation

This guide covers the complete deployment process for the AI Microservices project using Render.com, with automated deployment via n8n workflow.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Set Up Supabase (PostgreSQL Database)](#step-1-set-up-supabase-postgresql-database)
3. [Step 2: Set Up Qdrant Cloud (Vector Database)](#step-2-set-up-qdrant-cloud-vector-database)
4. [Step 3: Get OpenAI API Key](#step-3-get-openai-api-key)
5. [Step 4: Deploy to Render.com](#step-4-deploy-to-rendercom)
6. [Step 5: Set Up n8n Workflow Automation](#step-5-set-up-n8n-workflow-automation)
7. [Step 6: Verify Deployment](#step-6-verify-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Ongoing Maintenance](#ongoing-maintenance)

---

## Prerequisites

Before starting, ensure you have:

- [ ] GitHub account with access to the repository
- [ ] Supabase account (free tier available)
- [ ] Qdrant Cloud account (free tier available)
- [ ] OpenAI API account with credits
- [ ] Render.com account (free tier available)
- [ ] n8n instance (cloud or self-hosted)
- [ ] Basic knowledge of REST APIs and environment variables

---

## Step 1: Set Up Supabase (PostgreSQL Database)

### 1.1 Create a New Supabase Project

1. Go to [Supabase](https://supabase.com)
2. Click **"New Project"**
3. Fill in the details:
   - **Project Name:** `ai-microservices` (or your preferred name)
   - **Database Password:** Generate a strong password (save this!)
   - **Region:** Choose closest to your users (e.g., `Frankfurt`, `US East`)
   - **Pricing Plan:** Free tier is sufficient for testing
4. Click **"Create New Project"** and wait ~2 minutes for provisioning

### 1.2 Get Your Database Connection String

1. In your Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **Connection String** section
3. **CRITICAL:** Select **"Session Mode"** (NOT Transaction Mode)
4. Copy the connection string, it will look like:
   ```
   postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
   ```

### 1.3 Convert to AsyncPG Format

Replace `postgresql://` with `postgresql+asyncpg://`:

```bash
# Original (from Supabase)
postgresql://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:5432/postgres

# Converted (for our app)
postgresql+asyncpg://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:5432/postgres
```

**Save this as:** `DATABASE_URL`

### 1.4 Create Required Tables (Optional - Auto-Created)

The application will automatically create these tables on first run:
- `conversations` - Message history
- `customers` - Customer profiles
- `response_cache` - Response caching
- `analytics_events` - Analytics tracking
- `customer_facts` - Memory bank

If you have existing `products` and `orders` tables from previous setup, they will be reused.

**To manually create tables:** Run the SQL from `schema.sql` and `migrations/001_add_customer_facts_table.sql` in the Supabase SQL Editor.

---

## Step 2: Set Up Qdrant Cloud (Vector Database)

### 2.1 Create a Qdrant Cloud Account

1. Go to [Qdrant Cloud](https://cloud.qdrant.io/)
2. Sign up with GitHub or email
3. Verify your email

### 2.2 Create a New Cluster

1. Click **"Create Cluster"**
2. Fill in the details:
   - **Cluster Name:** `ai-microservices-vectors`
   - **Cloud Provider:** AWS, GCP, or Azure (AWS recommended)
   - **Region:** Same as your Render/Supabase region for lower latency
   - **Cluster Size:** 1GB Free tier (sufficient for testing)
3. Click **"Create"** and wait ~1-2 minutes

### 2.3 Get Your Qdrant Credentials

1. Once cluster is ready, click on it
2. Copy the **Cluster URL**:
   ```
   https://xxxxx-xxxxx.qdrant.tech
   ```
3. Go to **"API Keys"** tab
4. Click **"Create API Key"**
5. Copy the API key (it will only be shown once!)

**Save these as:**
- `QDRANT_URL`: `https://xxxxx-xxxxx.qdrant.tech`
- `QDRANT_API_KEY`: `your-api-key-here`

### 2.4 Collections (Auto-Created)

The application will automatically create these collections:
- `products` - Product vector embeddings (1536 dimensions for OpenAI)
- `knowledge_base` - Knowledge base embeddings

---

## Step 3: Get OpenAI API Key

### 3.1 Create OpenAI Account

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Add payment method (required for API access)

### 3.2 Generate API Key

1. Go to **API Keys** section: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **"Create new secret key"**
3. Give it a name: `AI-Microservices-Production`
4. Copy the key (starts with `sk-...`)

**Save this as:** `OPENAI_API_KEY`

### 3.3 Cost Estimation

For embeddings using `text-embedding-3-small`:
- **Cost:** ~$0.02 per 1M tokens
- **Expected usage:** ~$1-5/month for moderate traffic
- Set up billing alerts in OpenAI dashboard

---

## Step 4: Deploy to Render.com

### 4.1 Create Render Account

1. Go to [Render](https://render.com/)
2. Sign up with GitHub (recommended for easy deployments)
3. Authorize Render to access your repositories

### 4.2 Create a New Web Service

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `Ab-Romia/AI_Microservices`
3. Configure the service:

   **Basic Settings:**
   - **Name:** `ai-microservices-api`
   - **Region:** Choose same as Supabase/Qdrant
   - **Branch:** `claude/optimize-production-deployment-01K3iMGqie3PbeYrrN4tAnt8`
   - **Root Directory:** (leave empty)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

   **Instance Type:**
   - **Free** (for testing) or **Starter** ($7/month for production)

4. Click **"Create Web Service"**

### 4.3 Configure Environment Variables

In the Render dashboard, go to **Environment** tab and add these variables:

#### Required Variables

```bash
# Database (from Supabase - Step 1.3)
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres

# API Security (generate a strong random string)
API_KEY=your-super-secret-api-key-here-min-32-chars

# Qdrant Vector Database (from Step 2.3)
QDRANT_URL=https://xxxxx-xxxxx.qdrant.tech
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI (from Step 3.2)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

#### Optional But Recommended Variables

```bash
# Application Settings
DEBUG=false
ALLOWED_ORIGINS=*
APP_NAME=E-commerce DM Microservice
APP_VERSION=2.0.0

# Performance Tuning
MAX_CONVERSATION_HISTORY=50
MAX_PRODUCT_SEARCH_RESULTS=5
RATE_LIMIT_PER_MINUTE=100

# RAG Configuration
ENABLE_SEMANTIC_SEARCH=true
ENABLE_KNOWLEDGE_BASE=true
ENABLE_HYBRID_SEARCH=true
USE_LOCAL_EMBEDDINGS=false
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# RAG Retrieval Settings
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_CONTEXT_LENGTH=4000
RAG_CHUNK_SIZE=500
RAG_CHUNK_OVERLAP=50

# Qdrant Collections
QDRANT_COLLECTION_PRODUCTS=products
QDRANT_COLLECTION_KNOWLEDGE=knowledge_base

# Cache Settings
DEFAULT_CACHE_TTL_HOURS=24

# Analytics
ANALYTICS_RETENTION_DAYS=90
```

### 4.4 Configure Health Check

1. In Render dashboard, go to **Settings** tab
2. Scroll to **Health Check Path**
3. Set to: `/api/v1/health`
4. **Save Changes**

### 4.5 Deploy

1. Click **"Manual Deploy"** → **"Deploy latest commit"**
2. Monitor logs in the **Logs** tab
3. Wait for deployment to complete (~2-5 minutes)

### 4.6 Get Your Service URL

Once deployed, you'll see your service URL:
```
https://ai-microservices-api.onrender.com
```

**Save this as:** `RENDER_SERVICE_URL`

---

## Step 5: Set Up n8n Workflow Automation

### 5.1 Import the Workflow

1. Open your n8n instance
2. Go to **Workflows** → **Add Workflow**
3. Click the **"⋮"** menu → **"Import from File"**
4. Upload `n8n_deployment_workflow.json`
5. The workflow will be imported with all nodes

### 5.2 Configure n8n Environment Variables

Add these to your n8n instance settings or workflow credentials:

```bash
# From Step 4.3
DATABASE_URL=postgresql+asyncpg://...
API_KEY=your-api-key
QDRANT_URL=https://...
QDRANT_API_KEY=your-qdrant-key
OPENAI_API_KEY=sk-...

# From Step 4.6
RENDER_SERVICE_URL=https://ai-microservices-api.onrender.com

# Render API (get from Render Account Settings → API Keys)
RENDER_API_KEY=rnd_xxxxxxxxxxxxx
RENDER_SERVICE_ID=srv-xxxxxxxxxxxxx

# Optional: GitHub Issue Integration
GITHUB_ISSUE_NUMBER=1
```

### 5.3 Configure GitHub OAuth2 Credentials

1. In n8n, go to **Credentials** → **Add Credential**
2. Select **GitHub OAuth2 API**
3. Follow the setup:
   - Go to GitHub → Settings → Developer settings → OAuth Apps
   - Create new OAuth App
   - Set callback URL to n8n's OAuth callback URL
   - Copy Client ID and Secret to n8n
4. Save as `github_oauth_cred`

### 5.4 Get Render Service ID

```bash
# Using Render API
curl -H "Authorization: Bearer YOUR_RENDER_API_KEY" \
  https://api.render.com/v1/services

# Find your service and copy the "id" field
# It will look like: srv-xxxxxxxxxxxxx
```

### 5.5 Test the Workflow

1. In n8n, click **"Execute Workflow"** (manual trigger)
2. Monitor the execution:
   - ✅ Environment validation
   - ✅ Database connection test
   - ✅ Qdrant connection test
   - ✅ GitHub commit fetch
   - ✅ Render deployment trigger
   - ✅ Health check
   - ✅ API endpoint test
3. Check for any errors in failed nodes

### 5.6 Set Up Automatic Triggers (Optional)

Replace the "Manual Deploy Trigger" node with:

**Option A: Webhook Trigger**
- Trigger deployment via HTTP POST
- Useful for GitHub Actions integration

**Option B: Schedule Trigger**
- Deploy on a schedule (e.g., daily at 2 AM)
- Good for regular updates

**Option C: GitHub Trigger**
- Trigger on push to specific branch
- True CI/CD automation

---

## Step 6: Verify Deployment

### 6.1 Health Check

```bash
curl https://ai-microservices-api.onrender.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "qdrant": "connected",
  "timestamp": "2025-11-28T12:00:00.000Z"
}
```

### 6.2 Test Main API Endpoint

```bash
curl -X POST https://ai-microservices-api.onrender.com/api/v1/n8n/prepare-context \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@test_user",
    "message": "I want to buy a red dress",
    "channel": "instagram"
  }'
```

Expected response:
```json
{
  "customer_id": "instagram:@test_user",
  "conversation_history": [...],
  "customer_profile": {...},
  "relevant_products": [...],
  "knowledge_base_context": "...",
  "intent": "product_inquiry",
  "cached_response": null
}
```

### 6.3 Verify Database Tables

In Supabase SQL Editor:
```sql
-- Check if tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Should see: conversations, customers, response_cache, analytics_events, customer_facts
```

### 6.4 Verify Qdrant Collections

```bash
curl -H "api-key: YOUR_QDRANT_API_KEY" \
  https://xxxxx-xxxxx.qdrant.tech/collections
```

Expected response:
```json
{
  "collections": [
    {"name": "products"},
    {"name": "knowledge_base"}
  ]
}
```

---

## Troubleshooting

### Issue 1: "Network is unreachable" (IPv6 Error)

**Cause:** Using Supabase Transaction Mode (port 6543) which only supports IPv6
**Solution:**
1. Use **Session Mode** (port 5432) in your `DATABASE_URL`
2. Verify format: `postgresql+asyncpg://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:5432/postgres`

### Issue 2: Health Check Returns "Database: disconnected"

**Diagnosis:**
```bash
# Test database connection from Render shell
python scripts/test_database_urls.py
```

**Solutions:**
1. Verify `DATABASE_URL` format is correct
2. Check Supabase dashboard shows "Healthy" status
3. Ensure password doesn't contain special characters that need URL encoding
4. Try resetting database password in Supabase

### Issue 3: Health Check Returns "Qdrant: disconnected"

**Solutions:**
1. Verify `QDRANT_URL` doesn't have trailing slash
2. Verify `QDRANT_API_KEY` is correct
3. Check Qdrant cluster status in Qdrant Cloud dashboard
4. Ensure cluster hasn't been paused (free tier pauses after 7 days inactivity)

### Issue 4: "Module not found" Errors in Logs

**Cause:** Dependencies not installed
**Solution:**
1. Verify `requirements.txt` exists in repository root
2. Check Render build command: `pip install -r requirements.txt`
3. Review build logs for any failed package installations

### Issue 5: n8n Workflow Fails at "Trigger Render Deployment"

**Solutions:**
1. Verify `RENDER_API_KEY` is valid (get from Render Account Settings)
2. Verify `RENDER_SERVICE_ID` is correct (get from Render API)
3. Check service isn't already deploying
4. Ensure Render account has permissions for API access

### Issue 6: API Returns 401 Unauthorized

**Solutions:**
1. Verify `X-API-Key` header matches `API_KEY` environment variable
2. Check API key doesn't have leading/trailing spaces
3. Ensure header name is exactly `X-API-Key` (case-sensitive)

### Issue 7: Slow Response Times

**Optimizations:**
1. Enable response caching: Check `DEFAULT_CACHE_TTL_HOURS` is set
2. Upgrade Render instance from Free to Starter ($7/month)
3. Reduce `MAX_CONVERSATION_HISTORY` (default: 50)
4. Set `USE_LOCAL_EMBEDDINGS=true` to avoid OpenAI API latency
5. Adjust `RAG_TOP_K` to reduce vector search results

### Issue 8: High OpenAI Costs

**Solutions:**
1. Set `USE_LOCAL_EMBEDDINGS=true` to use free local embeddings
2. Reduce `RAG_CHUNK_SIZE` to create fewer embeddings
3. Enable response caching to reuse AI responses
4. Set up OpenAI usage limits in OpenAI dashboard

---

## Ongoing Maintenance

### Monitoring

**Daily:**
- Check Render dashboard for service health
- Review error logs for any issues

**Weekly:**
- Monitor OpenAI API usage and costs
- Check Qdrant storage usage
- Review analytics data in Supabase

**Monthly:**
- Update dependencies: `pip install -U -r requirements.txt`
- Review and optimize database queries
- Clean up old analytics data (automatic after `ANALYTICS_RETENTION_DAYS`)

### Updating the Application

**Via n8n Workflow:**
1. Push changes to GitHub branch
2. Run n8n deployment workflow
3. Workflow automatically deploys latest commit

**Manual Deployment:**
1. Push changes to GitHub
2. Go to Render dashboard
3. Click **"Manual Deploy"** → **"Deploy latest commit"**

### Scaling Considerations

**When to upgrade Render instance:**
- Consistent response times > 2 seconds
- Frequent cold starts on free tier
- Need for custom domains or autoscaling

**Database scaling:**
- Upgrade Supabase plan when approaching 500MB storage (free tier limit)
- Consider connection pooling if seeing connection errors

**Qdrant scaling:**
- Free tier: 1GB storage (~100k products with metadata)
- Upgrade when approaching storage limits or needing higher throughput

### Backup Strategy

**Database:**
- Supabase automatic backups (free tier: 7 days retention)
- Manual exports: Use Supabase dashboard → Database → Backups

**Vector Database:**
- Qdrant Cloud automatic snapshots
- Export collections via API if needed

**Code:**
- GitHub repository (version controlled)
- Tag releases: `git tag -a v2.0.0 -m "Production release"`

---

## n8n Workflow Features

The included workflow (`n8n_deployment_workflow.json`) provides:

### ✅ Automated Checks
- Environment variable validation
- Database connectivity test
- Qdrant connectivity test
- GitHub commit verification

### 🚀 Deployment Automation
- Automatic Render deployment trigger
- Deployment status monitoring
- Configurable wait times

### 🩺 Health Verification
- Comprehensive health check
- Database connection validation
- Qdrant connection validation
- API endpoint testing

### 📊 Reporting
- Success/failure summaries
- GitHub issue comments (optional)
- Slack/Discord notifications (optional)
- Deployment metadata tracking

### 🔧 Customization Points

**Enable GitHub notifications:**
1. Enable the "Post Success Comment" and "Post Failure Comment" nodes
2. Set `GITHUB_ISSUE_NUMBER` environment variable
3. Configure GitHub OAuth2 credentials

**Enable Slack/Discord notifications:**
1. Enable the "Send Notification" node
2. Add Slack/Discord webhook URL
3. Customize notification format in Code node

**Adjust wait times:**
- Modify "Wait for Deployment" duration (default: 30 seconds)
- Adjust based on your average deployment time

**Add pre-deployment steps:**
- Run tests before deploying
- Build and push Docker images
- Update external services

---

## Summary Checklist

Before going live, ensure:

- [ ] Supabase database created and `DATABASE_URL` configured
- [ ] Qdrant cluster created and credentials configured
- [ ] OpenAI API key obtained and configured
- [ ] Render service deployed with all environment variables
- [ ] Health check endpoint returns "healthy"
- [ ] Main API endpoint responding correctly
- [ ] n8n workflow imported and tested
- [ ] All database tables created (check Supabase)
- [ ] All Qdrant collections created
- [ ] Monitoring and alerts configured
- [ ] Backup strategy in place
- [ ] Documentation reviewed

## Support

For issues or questions:
1. Check Render logs: Render Dashboard → Logs
2. Check Supabase logs: Supabase Dashboard → Logs
3. Review n8n execution logs
4. Consult `DEPLOYMENT.md` for additional troubleshooting
5. Open GitHub issue with detailed error information

---

**Deployment complete! 🎉**

Your AI Microservices API is now live and accessible at:
```
https://ai-microservices-api.onrender.com
```

Health check endpoint:
```
https://ai-microservices-api.onrender.com/api/v1/health
```

Main API endpoint:
```
POST https://ai-microservices-api.onrender.com/api/v1/n8n/prepare-context
```
