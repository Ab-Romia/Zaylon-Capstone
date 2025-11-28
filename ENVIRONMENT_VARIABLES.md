# Environment Variables Quick Reference

Complete list of environment variables needed for deployment.

## 🔴 Critical - Required for Deployment

These MUST be set or the application will fail to start:

```bash
# PostgreSQL Database (from Supabase)
# Format: postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
# IMPORTANT: Use Session Mode (port 5432) NOT Transaction Mode (port 6543)
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:5432/postgres

# API Security Key
# Generate a strong random string (min 32 characters)
# Example: openssl rand -hex 32
API_KEY=your-super-secret-api-key-here-min-32-chars

# Qdrant Vector Database URL (from Qdrant Cloud)
# Format: https://xxxxx-xxxxx.qdrant.tech (no trailing slash)
QDRANT_URL=https://xxxxx-xxxxx.qdrant.tech

# Qdrant API Key (from Qdrant Cloud dashboard)
QDRANT_API_KEY=your-qdrant-api-key-from-cloud-dashboard

# OpenAI API Key (for embeddings and AI features)
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🟡 Recommended - Improves Performance & Features

These are optional but highly recommended for production:

```bash
# Application Metadata
APP_NAME=E-commerce DM Microservice
APP_VERSION=2.0.0
DEBUG=false

# CORS Configuration
# Use * for all origins, or comma-separated list: https://example.com,https://app.example.com
ALLOWED_ORIGINS=*

# Rate Limiting (requests per minute per API key/IP)
RATE_LIMIT_PER_MINUTE=100

# Performance Tuning
MAX_CONVERSATION_HISTORY=50          # Number of previous messages to include in context
MAX_PRODUCT_SEARCH_RESULTS=5         # Max products returned in searches

# Cache Settings
DEFAULT_CACHE_TTL_HOURS=24           # How long to cache responses (in hours)

# Analytics
ANALYTICS_RETENTION_DAYS=90          # Auto-delete analytics older than this
```

---

## 🟢 Optional - RAG & AI Configuration

Fine-tune RAG (Retrieval-Augmented Generation) behavior:

```bash
# RAG Feature Toggles
ENABLE_SEMANTIC_SEARCH=true          # Use vector similarity for product search
ENABLE_KNOWLEDGE_BASE=true           # Include knowledge base in AI responses
ENABLE_HYBRID_SEARCH=true            # Combine keyword + vector search

# Embedding Configuration
USE_LOCAL_EMBEDDINGS=false           # true = free but lower quality, false = OpenAI (costs money)
EMBEDDING_MODEL=text-embedding-3-small    # OpenAI model (if USE_LOCAL_EMBEDDINGS=false)
LOCAL_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=1536             # OpenAI: 1536, Local: 384 (auto-detected)

# RAG Retrieval Settings
RAG_TOP_K=5                          # Number of similar items to retrieve from vector DB
RAG_SIMILARITY_THRESHOLD=0.7         # Minimum similarity score (0-1, higher = more strict)
RAG_MAX_CONTEXT_LENGTH=4000          # Maximum tokens for RAG context
RAG_CHUNK_SIZE=500                   # Document chunk size when indexing
RAG_CHUNK_OVERLAP=50                 # Overlap between chunks for better context

# Qdrant Collection Names (custom names if needed)
QDRANT_COLLECTION_PRODUCTS=products
QDRANT_COLLECTION_KNOWLEDGE=knowledge_base
```

---

## 🔵 n8n Workflow Variables

Additional variables needed for n8n automation workflow:

```bash
# Render Configuration
RENDER_API_KEY=rnd_xxxxxxxxxxxxxxxxxxxxx       # From Render Account Settings → API Keys
RENDER_SERVICE_ID=srv-xxxxxxxxxxxxx            # Get via Render API or dashboard URL
RENDER_SERVICE_URL=https://ai-microservices-api.onrender.com  # Your deployed service URL

# GitHub Integration (optional, for automated comments)
GITHUB_ISSUE_NUMBER=1                          # Issue number to post deployment updates
GITHUB_OAUTH_TOKEN=ghp_xxxxxxxxxxxx           # GitHub personal access token
```

---

## 🐳 Docker Compose Only

These are ONLY needed when running with `docker-compose up` (local development):

```bash
# PostgreSQL Container Configuration
POSTGRES_USER=ecommerce
POSTGRES_PASSWORD=ecommerce_password
POSTGRES_DB=ecommerce_dm

# Note: When using Docker Compose, DATABASE_URL becomes:
# DATABASE_URL=postgresql+asyncpg://ecommerce:ecommerce_password@postgres:5432/ecommerce_dm

# Qdrant Container URL (when using local Qdrant)
# QDRANT_URL=http://qdrant:6333
```

---

## 📝 How to Get Each Value

### DATABASE_URL
1. Go to [Supabase](https://supabase.com)
2. Create or open your project
3. Settings → Database → Connection String → **Session Mode**
4. Replace `postgresql://` with `postgresql+asyncpg://`

### API_KEY
Generate a secure random key:
```bash
# macOS/Linux
openssl rand -hex 32

# Or use any password generator (minimum 32 characters)
```

### QDRANT_URL & QDRANT_API_KEY
1. Go to [Qdrant Cloud](https://cloud.qdrant.io)
2. Create a cluster
3. Copy the cluster URL (e.g., `https://xxxxx.qdrant.tech`)
4. Go to API Keys → Create API Key → Copy the key

### OPENAI_API_KEY
1. Go to [OpenAI Platform](https://platform.openai.com)
2. Navigate to [API Keys](https://platform.openai.com/api-keys)
3. Create new secret key → Copy it (starts with `sk-`)

### RENDER_API_KEY
1. Log in to [Render](https://render.com)
2. Account Settings → API Keys
3. Create new API key → Copy it

### RENDER_SERVICE_ID
```bash
# Using Render API
curl -H "Authorization: Bearer YOUR_RENDER_API_KEY" \
  https://api.render.com/v1/services

# Find your service in the JSON response and copy the "id" field
```

### RENDER_SERVICE_URL
This is your deployed service URL, e.g.:
```
https://your-service-name.onrender.com
```

---

## 🎯 Minimal Production Setup

The absolute minimum for production deployment:

```bash
DATABASE_URL=postgresql+asyncpg://...  # From Supabase Session Mode
API_KEY=...                            # Strong random string (32+ chars)
QDRANT_URL=https://...                 # From Qdrant Cloud
QDRANT_API_KEY=...                     # From Qdrant Cloud
OPENAI_API_KEY=sk-...                  # From OpenAI Platform
```

Everything else has sensible defaults and can be added later.

---

## 🔍 Validation Checklist

Use this to verify your environment variables:

- [ ] `DATABASE_URL` starts with `postgresql+asyncpg://`
- [ ] `DATABASE_URL` uses port `5432` (Session Mode)
- [ ] `API_KEY` is at least 32 characters long
- [ ] `QDRANT_URL` starts with `https://` (no trailing slash)
- [ ] `QDRANT_API_KEY` is not empty
- [ ] `OPENAI_API_KEY` starts with `sk-`
- [ ] `DEBUG=false` in production
- [ ] `ALLOWED_ORIGINS` is configured (not `*` in production if possible)

---

## 🐛 Common Mistakes

**❌ Wrong:**
```bash
DATABASE_URL=postgresql://...          # Missing +asyncpg driver
DATABASE_URL=...@host:6543/...         # Wrong port (Transaction Mode)
QDRANT_URL=https://xxx.qdrant.tech/    # Trailing slash
API_KEY=test                           # Too weak
```

**✅ Correct:**
```bash
DATABASE_URL=postgresql+asyncpg://...@host:5432/...
QDRANT_URL=https://xxx.qdrant.tech
API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## 💰 Cost Breakdown

| Service | Free Tier | Estimated Monthly Cost |
|---------|-----------|----------------------|
| **Supabase** | 500MB DB, 2GB bandwidth | $0 (free tier sufficient) |
| **Qdrant Cloud** | 1GB storage | $0 (free tier sufficient) |
| **Render** | 750 hours/month | $0 (free) or $7 (Starter) |
| **OpenAI API** | Pay-as-you-go | $1-10 (depends on usage) |
| **n8n** | Self-hosted or Cloud | $0 (self-hosted) or $20 (cloud) |
| **Total** | | **$1-37/month** |

**💡 To minimize costs:**
- Set `USE_LOCAL_EMBEDDINGS=true` (saves OpenAI costs)
- Use Render free tier for testing
- Enable response caching (`DEFAULT_CACHE_TTL_HOURS=24`)
- Set OpenAI usage limits in platform settings

---

## 📚 References

- [Supabase Connection Strings](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [Qdrant Cloud Documentation](https://qdrant.tech/documentation/cloud/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [n8n Environment Variables](https://docs.n8n.io/hosting/environment-variables/)

---

## 🆘 Need Help?

If a variable isn't working:
1. Check for typos and extra spaces
2. Verify the format matches examples above
3. Test each service individually (database, Qdrant, OpenAI)
4. Check Render logs for specific error messages
5. Review the main deployment guide: `N8N_DEPLOYMENT_GUIDE.md`
