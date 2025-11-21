# RAG System Implementation Guide

## Overview

This E-commerce DM Microservice now includes a comprehensive **Retrieval-Augmented Generation (RAG)** system that dramatically improves the AI assistant's ability to handle customer queries with:

- **Semantic Search**: AI-powered product search using vector embeddings
- **Hybrid Search**: Combines keyword matching with semantic similarity
- **Knowledge Base**: Store and retrieve FAQs, policies, and guides
- **Multilingual Support**: Optimized for Arabic, Franco-Arabic, and English

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Customer Query                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              RAG Orchestration Service                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Generate Query Embedding                          │   │
│  │ 2. Search Vector DB (Products + Knowledge)           │   │
│  │ 3. Search SQL DB (Keywords - Fallback)               │   │
│  │ 4. Merge & Rank Results                              │   │
│  │ 5. Format Context for AI                             │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────┬────────────────────────────┬────────────────────┘
            │                            │
            ▼                            ▼
┌───────────────────────┐    ┌─────────────────────────────┐
│   Vector Database     │    │   PostgreSQL Database       │
│      (Qdrant)         │    │   (Products, Customers)     │
│                       │    │                             │
│ • Product Embeddings  │    │ • Product Details           │
│ • Knowledge Base      │    │ • Conversation History      │
│ • Semantic Search     │    │ • Analytics                 │
└───────────────────────┘    └─────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────┐
│              Embedding Service                             │
│  ┌──────────────────┐         ┌───────────────────────┐   │
│  │  OpenAI API      │   OR    │ Local Sentence        │   │
│  │  (Best Quality)  │         │ Transformers (Free)   │   │
│  └──────────────────┘         └───────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Semantic Product Search
- Uses vector embeddings to understand query meaning
- Finds products even with different wording
- Example: "عايز حاجة البس" finds "Blue Jeans", "T-Shirt", etc.
- Better than keyword matching for complex queries

### 2. Hybrid Search
- Combines semantic search with keyword matching
- Ensures both relevant AND exact matches
- Deduplicates results intelligently
- Ranks by relevance score

### 3. Knowledge Base
- Store FAQs, shipping policies, return policies
- Automatically chunked for optimal retrieval
- Retrieved based on semantic similarity
- Injected into AI context when relevant

### 4. Multilingual Embeddings
- Optimized for Arabic, Franco-Arabic, and English
- Uses multilingual models
- Handles code-switching seamlessly

## Setup Guide

### Option 1: Local Development with Docker Compose (Recommended)

1. **Clone and Configure**
   ```bash
   cd AI_Microservices
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Set Environment Variables**
   ```bash
   # Required: PostgreSQL (already configured in docker-compose)
   # Required: API Key
   API_KEY=your-secret-api-key

   # Option A: Use OpenAI Embeddings (Better Quality)
   OPENAI_API_KEY=sk-your-key-here
   USE_LOCAL_EMBEDDINGS=false

   # Option B: Use Local Embeddings (Free, No API Key)
   USE_LOCAL_EMBEDDINGS=true

   # Qdrant is auto-configured in docker-compose
   QDRANT_URL=http://qdrant:6333
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

   This starts:
   - PostgreSQL (port 5432)
   - Qdrant Vector DB (port 6333)
   - Microservice (port 8000)

4. **Verify Health**
   ```bash
   curl http://localhost:8000/health
   ```

   Expected output:
   ```json
   {
     "status": "healthy",
     "version": "2.0.0",
     "database": "connected",
     "qdrant": "connected",
     "timestamp": "2024-01-20T10:00:00"
   }
   ```

5. **Index Products**
   ```bash
   curl -X POST http://localhost:8000/rag/index/products/all \
     -H "X-API-Key: your-secret-api-key"
   ```

   This indexes all products into Qdrant for semantic search.

### Option 2: Local Development without Docker

1. **Install Qdrant Locally**
   ```bash
   # Using Docker
   docker run -p 6333:6333 qdrant/qdrant:v1.7.0

   # Or download binary from https://qdrant.tech/
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Set QDRANT_URL=http://localhost:6333
   # Set other variables as needed
   ```

4. **Run Service**
   ```bash
   python main.py
   ```

### Option 3: Production Deployment on Render

Render doesn't offer a free Qdrant instance, so you have two options:

**Option A: Use Qdrant Cloud (Free Tier)**

1. **Sign up for Qdrant Cloud**
   - Go to https://cloud.qdrant.io/
   - Create a free cluster
   - Get your cluster URL and API key

2. **Configure Render Environment**
   ```
   QDRANT_URL=https://your-cluster.qdrant.tech
   QDRANT_API_KEY=your-qdrant-api-key
   OPENAI_API_KEY=sk-your-openai-key
   USE_LOCAL_EMBEDDINGS=false
   ```

3. **Deploy as usual on Render**
   - Push to your branch
   - Render will auto-deploy
   - Run indexing via API after deployment

**Option B: Use Local Embeddings Only (No Vector DB)**

1. **Configure for keyword-only mode**
   ```
   # Don't set QDRANT_URL (or set to empty)
   USE_LOCAL_EMBEDDINGS=true
   ENABLE_SEMANTIC_SEARCH=false
   ```

2. **System will gracefully fallback to keyword search**
   - Still works great with multilingual keyword matching
   - No external dependencies
   - Lower cost, slightly lower quality

## API Endpoints

### RAG Search

**POST /rag/search**

Perform semantic search across products and knowledge base.

```bash
curl -X POST http://localhost:8000/rag/search \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "عايز جينز ازرق",
    "limit": 5,
    "search_method": "hybrid",
    "include_knowledge": true
  }'
```

Response:
```json
{
  "products": [
    {
      "id": "123",
      "name": "Blue Denim Jeans",
      "price": 599.0,
      "description": "Classic blue jeans",
      "sizes": ["30", "32", "34"],
      "colors": ["blue"],
      "stock_count": 50,
      "similarity_score": 0.92,
      "search_method": "semantic"
    }
  ],
  "products_formatted": "RELEVANT PRODUCTS (Retrieved using AI-powered semantic search):\n\nProduct 1: Blue Denim Jeans\n  Price: 599.00 EGP\n  ...",
  "knowledge_items": [],
  "knowledge_formatted": "",
  "metadata": {
    "detected_language": "ar",
    "total_found": 3,
    "semantic_count": 2,
    "keyword_count": 3,
    "hybrid_enabled": true
  },
  "rag_enabled": true
}
```

### Index Product

**POST /rag/index/product**

Index a single product for semantic search.

```bash
curl -X POST http://localhost:8000/rag/index/product \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "123"
  }'
```

### Index All Products

**POST /rag/index/products/all**

Bulk index all products (rate limited: 5/hour).

```bash
curl -X POST http://localhost:8000/rag/index/products/all \
  -H "X-API-Key: your-key"
```

Response:
```json
{
  "success": true,
  "total": 150,
  "indexed": 148,
  "failed": 2,
  "start_time": "2024-01-20T10:00:00",
  "end_time": "2024-01-20T10:02:30"
}
```

### Index Knowledge Base Document

**POST /rag/index/knowledge**

Add FAQ, policy, or guide to knowledge base.

```bash
curl -X POST http://localhost:8000/rag/index/knowledge \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "shipping-policy",
    "title": "Shipping Policy",
    "category": "policies",
    "content": "We offer free shipping on orders over 500 EGP. Delivery takes 2-5 business days within Cairo. For other governorates, delivery takes 3-7 business days. Express shipping is available for an additional 50 EGP."
  }'
```

### RAG System Status

**GET /rag/status**

Check RAG system health and configuration.

```bash
curl http://localhost:8000/rag/status \
  -H "X-API-Key: your-key"
```

Response:
```json
{
  "connected": true,
  "products_collection": {
    "name": "products",
    "vectors_count": 150,
    "points_count": 150,
    "status": "green"
  },
  "knowledge_collection": {
    "name": "knowledge_base",
    "vectors_count": 45,
    "points_count": 15,
    "status": "green"
  },
  "embedding_dimension": 1536,
  "embedding_model": "text-embedding-3-small"
}
```

## Integration with n8n Workflow

The existing `/n8n/prepare-context` endpoint automatically uses RAG when enabled:

```javascript
// n8n HTTP Request Node
{
  "method": "POST",
  "url": "https://your-service.onrender.com/n8n/prepare-context",
  "headers": {
    "X-API-Key": "your-key"
  },
  "body": {
    "customer_id": "instagram:@ahmed",
    "message": "عايز جينز ازرق",
    "channel": "instagram"
  }
}
```

The response now includes RAG-enhanced product results:
- Better semantic matching
- Knowledge base information when relevant
- Improved multilingual understanding

No changes needed to your existing n8n workflow!

## Configuration Options

### Embedding Models

**OpenAI Models** (Requires API Key)
- `text-embedding-3-small`: Best price/performance (1536 dimensions)
- `text-embedding-3-large`: Highest quality (3072 dimensions)
- `text-embedding-ada-002`: Legacy model (1536 dimensions)

**Local Models** (Free, Offline)
- `paraphrase-multilingual-MiniLM-L12-v2`: Good for Arabic/English (384 dimensions)
- `distiluse-base-multilingual-cased-v2`: Alternative (512 dimensions)

### Search Methods

**Semantic Search**
- Pure vector similarity
- Best for understanding intent
- Requires vector DB

**Keyword Search**
- Traditional SQL matching
- Fast and reliable
- No vector DB needed
- Multilingual keyword mappings

**Hybrid Search** (Recommended)
- Combines both methods
- Best of both worlds
- Deduplicates intelligently

### RAG Features Toggle

```bash
# Enable/disable features in .env
ENABLE_SEMANTIC_SEARCH=true    # Use vector search
ENABLE_KNOWLEDGE_BASE=true     # Include KB in responses
ENABLE_HYBRID_SEARCH=true      # Combine methods
```

## Performance & Cost

### Indexing Performance
- **Single product**: ~100ms
- **100 products**: ~10-15 seconds
- **1000 products**: ~2-3 minutes

### Search Performance
- **Semantic search**: ~50-100ms
- **Keyword search**: ~20-50ms
- **Hybrid search**: ~80-150ms

### OpenAI API Costs

**Embeddings** (text-embedding-3-small)
- $0.02 per 1M tokens
- Average product: ~100 tokens
- **Cost to index 1000 products**: ~$0.002 (negligible)
- **Cost per search**: ~$0.000002 per query

**Local Embeddings**: FREE
- No API costs
- Slightly lower quality
- Requires more RAM (~1GB for model)

### Qdrant Costs

**Qdrant Cloud**
- Free tier: 1GB storage (enough for ~100K products)
- Paid: $25/month for 4GB

**Self-hosted**
- Free
- RAM usage: ~500MB-2GB depending on collection size

## Monitoring

### Health Checks

```bash
# Check overall health
curl http://localhost:8000/health

# Check RAG status
curl http://localhost:8000/rag/status \
  -H "X-API-Key: your-key"
```

### Logs

Watch for:
- `Embedding service initialized (dimension: 1536)`
- `Vector database (Qdrant) initialized`
- `Indexed product: Blue Jeans (ID: 123)`
- `Semantic search found 5 products`
- `Hybrid search: 3 semantic + 2 keyword = 5 final`

## Troubleshooting

### "Vector database not connected"

**Cause**: Qdrant not running or misconfigured

**Solution**:
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check Qdrant health
curl http://localhost:6333/healthz

# Restart Qdrant
docker-compose restart qdrant
```

### "OpenAI embedding failed"

**Cause**: Invalid API key or rate limit

**Solution**:
```bash
# Verify API key
echo $OPENAI_API_KEY

# Fallback to local embeddings
USE_LOCAL_EMBEDDINGS=true
```

### "No products found"

**Cause**: Products not indexed yet

**Solution**:
```bash
# Index all products
curl -X POST http://localhost:8000/rag/index/products/all \
  -H "X-API-Key: your-key"
```

### High Memory Usage

**Cause**: Local embedding model loaded

**Solution**:
- Use OpenAI embeddings instead: `USE_LOCAL_EMBEDDINGS=false`
- Or allocate more RAM to container:
  ```yaml
  # docker-compose.yml
  services:
    app:
      deploy:
        resources:
          limits:
            memory: 2G
  ```

## Best Practices

### 1. Indexing Strategy

**Initial Setup**:
```bash
# Index all products once
POST /rag/index/products/all
```

**Ongoing**:
```bash
# Index new/updated products individually
POST /rag/index/product {"product_id": "123"}

# Re-index all products daily/weekly (automated)
```

### 2. Knowledge Base Organization

**Categories**:
- `faq`: Frequently asked questions
- `policies`: Shipping, return, privacy policies
- `guides`: Size guides, care instructions
- `promotions`: Current sales and offers

**Example**:
```bash
# Add shipping FAQ
POST /rag/index/knowledge {
  "doc_id": "faq-shipping-001",
  "title": "How long does shipping take?",
  "category": "faq",
  "content": "Shipping takes 2-5 business days within Cairo..."
}
```

### 3. Embedding Model Selection

**For Production**:
- Use OpenAI `text-embedding-3-small` (best quality/cost)
- Enable hybrid search for reliability
- Cache embeddings when possible

**For Development**:
- Use local embeddings (faster iteration)
- No API costs
- Good enough for testing

### 4. Search Optimization

**Use semantic search when**:
- Query is complex or conversational
- Multiple languages in query
- Understanding intent matters

**Use keyword search when**:
- Exact product name known
- Simple queries
- Speed is critical

**Use hybrid search (recommended)**:
- General purpose
- Best results
- Slight performance cost

## Migration from v1.0

The RAG system is **fully backward compatible**. Existing endpoints work as before, but now automatically benefit from semantic search when enabled.

**No changes required**:
- Existing n8n workflows continue to work
- `/products/search` still available
- `/n8n/prepare-context` enhanced with RAG

**Optional improvements**:
1. Index your products: `POST /rag/index/products/all`
2. Add knowledge base documents
3. Enable RAG features in .env
4. Monitor with `/rag/status`

## Next Steps

1. **Deploy and Index**
   - Deploy service with RAG support
   - Index all products
   - Test semantic search

2. **Add Knowledge Base**
   - Create FAQ documents
   - Add policies
   - Index using `/rag/index/knowledge`

3. **Monitor Performance**
   - Check `/health` for status
   - Review logs for issues
   - Monitor API costs

4. **Optimize**
   - Adjust similarity thresholds
   - Fine-tune chunk sizes
   - Test different embedding models

5. **Scale**
   - Add more products
   - Expand knowledge base
   - Enable caching for popular queries

## Support

For questions or issues:
1. Check logs: `docker-compose logs -f app`
2. Verify health: `GET /health` and `GET /rag/status`
3. Test endpoints with provided examples
4. Review this guide's troubleshooting section

Happy building! 🚀
