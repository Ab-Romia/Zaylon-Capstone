# Deployment Guide - AI Microservices

## Quick Start

The application has been reorganized with a new structure. Make sure to use the updated commands.

### Running Locally

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using Docker Compose

```bash
# Start all services (Postgres, Qdrant, App)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Render Deployment

### Prerequisites

1. **Supabase Database** - PostgreSQL database URL
2. **Qdrant Cloud** - Vector database URL and API key
3. **OpenAI API Key** - For embeddings and AI features

### Render Configuration

#### Build Command
```bash
pip install -r requirements.txt
```

#### Start Command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

Set these in Render's environment variables:

#### Required Variables
```bash
# Database (from Supabase)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# API Security
API_KEY=your-secret-api-key-here

# Qdrant Vector Database
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI API
OPENAI_API_KEY=sk-...your-openai-key
```

#### Optional Variables
```bash
# App Settings
DEBUG=false
ALLOWED_ORIGINS=*

# RAG Features (all default to true)
ENABLE_SEMANTIC_SEARCH=true
ENABLE_KNOWLEDGE_BASE=true
ENABLE_HYBRID_SEARCH=true
USE_LOCAL_EMBEDDINGS=false

# Performance
MAX_PRODUCT_SEARCH_RESULTS=5
```

## API Endpoints

All endpoints are now under `/api/v1/`:

### Health Check
```bash
GET /api/v1/health
```

### Main Endpoints
- `/api/v1/n8n/*` - n8n integration
- `/api/v1/products/*` - Product management
- `/api/v1/context/*` - Conversation context
- `/api/v1/intent/*` - Intent classification
- `/api/v1/cache/*` - Response caching
- `/api/v1/analytics/*` - Analytics
- `/api/v1/rag/*` - RAG system

## Testing Deployment

### 1. Health Check
```bash
curl https://your-app.onrender.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "database": "connected",
  "qdrant": "connected",
  "timestamp": "2025-11-26T..."
}
```

### 2. Test Main Endpoint
```bash
curl -X POST https://your-app.onrender.com/api/v1/n8n/prepare-context \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@test",
    "message": "hello",
    "channel": "instagram"
  }'
```

## Database Setup

### Supabase Tables

The application requires these tables:

1. **products** - Product catalog (pre-existing)
2. **orders** - Order management (pre-existing)
3. **conversations** - Message history (created automatically)
4. **customers** - Customer profiles (created automatically)
5. **response_cache** - Response caching (created automatically)
6. **analytics_events** - Analytics tracking (created automatically)

The app will automatically create the new tables on first run.

### Qdrant Collections

The application will automatically create:
- `products` - Product embeddings
- `knowledge_base` - Knowledge base embeddings

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're using `app.main:app` not `main:app`
   - Check all environment variables are set

2. **Database Connection**
   - Verify DATABASE_URL format: `postgresql+asyncpg://...`
   - Check Supabase IP whitelist includes Render IPs

3. **Qdrant Connection**
   - Verify QDRANT_URL and QDRANT_API_KEY
   - Check Qdrant cluster is running

4. **Health Check Failures**
   - Endpoint is now `/api/v1/health` (not `/health`)
   - Update any monitoring tools

## Monitoring

### Logs
```bash
# Render dashboard - view real-time logs
# Or use Render CLI:
render logs -s your-service-name
```

### Health Check
Configure Render health check:
- Path: `/api/v1/health`
- Interval: 30s

## Rollback

If issues occur:
```bash
# Previous commit
git revert HEAD
git push origin main

# Specific commit
git reset --hard <commit-hash>
git push --force origin main
```

## Performance Tips

1. **Use production ASGI server**: Already using Uvicorn
2. **Database connection pooling**: Configured (pool_size=20)
3. **Response caching**: Built-in for common queries
4. **Background tasks**: Analytics logged asynchronously

## Security

- API key authentication on all endpoints
- Rate limiting configured (5 requests/second)
- CORS properly configured
- Environment variables for secrets
- Non-root user in Docker

## Support

For issues:
1. Check logs in Render dashboard
2. Verify all environment variables
3. Test database connections
4. Check Qdrant status

## Changelog

### v2.0.0 - Reorganization
- Restructured to modular architecture
- API versioning (`/api/v1/`)
- Separated models from schemas
- Improved scalability
- Updated deployment configuration
