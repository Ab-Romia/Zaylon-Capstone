# Deploying RAG-Enhanced Microservice on Render

## Quick Deployment Guide

This guide covers deploying the RAG-enhanced v2.0 microservice to your existing Render deployment.

## Deployment Options

### Option 1: Full RAG with Qdrant Cloud (Recommended)

**Best for**: Maximum AI capability, semantic search, knowledge base

**Steps**:

1. **Sign up for Qdrant Cloud** (Free Tier Available)
   - Go to https://cloud.qdrant.io/
   - Sign up with GitHub or email
   - Click "Create Cluster"
   - Choose "Free" tier (1GB storage, perfect for small/medium stores)
   - Note your cluster URL and API key

2. **Update Render Environment Variables**

   Go to your Render dashboard → Your service → Environment

   **Add these new variables**:
   ```
   # Vector Database
   QDRANT_URL=https://your-cluster-id.qdrant.tech
   QDRANT_API_KEY=your-qdrant-api-key

   # Embeddings (Choose One)
   # Option A: OpenAI (Better Quality)
   OPENAI_API_KEY=sk-your-openai-key
   USE_LOCAL_EMBEDDINGS=false

   # Option B: Local (Free, No API Key)
   USE_LOCAL_EMBEDDINGS=true

   # RAG Features
   ENABLE_SEMANTIC_SEARCH=true
   ENABLE_KNOWLEDGE_BASE=true
   ENABLE_HYBRID_SEARCH=true
   RAG_TOP_K=5
   RAG_SIMILARITY_THRESHOLD=0.7

   # Update version
   APP_VERSION=2.0.0
   ```

3. **Deploy to Render**
   ```bash
   git add .
   git commit -m "Implement RAG system v2.0"
   git push origin claude/implement-rag-system-011crjbhPkGNr4gAvF3mNoH7
   ```

   Render will auto-deploy.

4. **Verify Deployment**
   ```bash
   # Check health
   curl https://dm-service-mpjf.onrender.com/health

   # Should show:
   # "qdrant": "connected"
   ```

5. **Index Your Products**
   ```bash
   curl -X POST https://dm-service-mpjf.onrender.com/rag/index/products/all \
     -H "X-API-Key: your-api-key"
   ```

   Wait 1-2 minutes for indexing to complete.

6. **Test Semantic Search**
   ```bash
   curl -X POST https://dm-service-mpjf.onrender.com/rag/search \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "عايز بنطلون",
       "limit": 5,
       "search_method": "hybrid"
     }'
   ```

**Done!** Your service now has AI-powered semantic search.

---

### Option 2: Local Embeddings Only (Free, No External Dependencies)

**Best for**: Cost-conscious, simpler deployment, still great results

**Steps**:

1. **Update Render Environment Variables**
   ```
   # Use local embeddings (no API keys needed)
   USE_LOCAL_EMBEDDINGS=true

   # Disable Qdrant (optional - for pure keyword mode)
   # Just don't set QDRANT_URL

   # Or keep hybrid mode with local embeddings
   QDRANT_URL=https://your-qdrant-cluster.tech
   ENABLE_HYBRID_SEARCH=true

   APP_VERSION=2.0.0
   ```

2. **Deploy**
   ```bash
   git push origin claude/implement-rag-system-011crjbhPkGNr4gAvF3mNoH7
   ```

3. **Index Products** (if using Qdrant)
   ```bash
   curl -X POST https://dm-service-mpjf.onrender.com/rag/index/products/all \
     -H "X-API-Key: your-api-key"
   ```

**Benefits**:
- No OpenAI API costs
- No external API dependencies
- Still multilingual keyword search
- Optional: Add Qdrant later for semantic search

---

### Option 3: Keyword-Only Mode (Backward Compatible)

**Best for**: Keeping current setup, testing before full RAG

**Steps**:

1. **Update Render Environment Variables**
   ```
   # Disable RAG features
   ENABLE_SEMANTIC_SEARCH=false
   USE_LOCAL_EMBEDDINGS=true
   APP_VERSION=2.0.0
   ```

2. **Deploy**
   ```bash
   git push origin claude/implement-rag-system-011crjbhPkGNr4gAvF3mNoH7
   ```

**Result**: Service works exactly as before with improved keyword matching.

---

## Cost Breakdown

### Option 1: Full RAG (OpenAI + Qdrant)

**Qdrant Cloud**:
- Free tier: $0/month (1GB storage)
- Paid tier: $25/month (if you exceed 1GB)

**OpenAI Embeddings**:
- text-embedding-3-small: $0.02 per 1M tokens
- Typical costs:
  - Index 1000 products: ~$0.002 (one-time)
  - 10,000 searches/month: ~$0.02/month

**Total**: ~$0.02/month (within free tiers)

### Option 2: Local Embeddings + Qdrant

**Qdrant Cloud**: $0/month (free tier)
**Embeddings**: $0/month (local)

**Total**: $0/month (completely free!)

**Trade-off**: Slightly lower search quality, higher RAM usage on Render (~1GB extra)

### Option 3: Keyword-Only

**Total**: $0/month (no changes to current costs)

---

## Post-Deployment Steps

### 1. Index Your Products

After first deployment, index all products:

```bash
curl -X POST https://dm-service-mpjf.onrender.com/rag/index/products/all \
  -H "X-API-Key: your-api-key"
```

**Expected response**:
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

### 2. Add Knowledge Base Documents

Add FAQs, policies, etc.:

```bash
# Shipping Policy
curl -X POST https://dm-service-mpjf.onrender.com/rag/index/knowledge \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "shipping-policy",
    "title": "Shipping Policy",
    "category": "policies",
    "content": "نوفر شحن مجاني للطلبات فوق 500 جنيه. التوصيل يستغرق 2-5 أيام عمل في القاهرة."
  }'

# Return Policy
curl -X POST https://dm-service-mpjf.onrender.com/rag/index/knowledge \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "return-policy",
    "title": "Return Policy",
    "category": "policies",
    "content": "يمكنك إرجاع أي منتج خلال 14 يوم من تاريخ الشراء. المنتج يجب أن يكون في حالته الأصلية."
  }'

# Common FAQ
curl -X POST https://dm-service-mpjf.onrender.com/rag/index/knowledge \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": "faq-sizes",
    "title": "Size Guide",
    "category": "faq",
    "content": "مقاسات الجينز: مقاس 30 (محيط خصر 76-78 سم), مقاس 32 (80-82 سم), مقاس 34 (84-86 سم)"
  }'
```

### 3. Test the Integration

```bash
# Test semantic search
curl -X POST https://dm-service-mpjf.onrender.com/rag/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ايه سياسة الشحن؟",
    "include_knowledge": true
  }'

# Should return shipping policy from knowledge base
```

### 4. Monitor Performance

```bash
# Check RAG status
curl https://dm-service-mpjf.onrender.com/rag/status \
  -H "X-API-Key: your-api-key"

# View logs in Render dashboard
# Look for:
# - "Embedding service initialized"
# - "Vector database (Qdrant) initialized"
# - "Semantic search found X products"
```

---

## Updating Your n8n Workflow

**Good news**: No changes required! Your existing n8n workflow automatically benefits from RAG.

The `/n8n/prepare-context` endpoint now:
- Uses semantic search for products
- Includes knowledge base when relevant
- Falls back to keyword search if needed

**Optional improvement** - Use the new `/rag/search` endpoint directly:

```javascript
// New n8n HTTP Request Node (Optional)
{
  "method": "POST",
  "url": "https://dm-service-mpjf.onrender.com/rag/search",
  "headers": {
    "X-API-Key": "{{ $credentials.api_key }}"
  },
  "body": {
    "query": "{{ $json.message_text }}",
    "limit": 5,
    "search_method": "hybrid",
    "include_knowledge": true
  }
}
```

Then format the response:
```javascript
// Code node to format RAG response
const ragResponse = $input.item.json;

return {
  json: {
    products_context: ragResponse.products_formatted,
    knowledge_context: ragResponse.knowledge_formatted,
    search_quality: ragResponse.metadata.semantic_count > 0 ? "high" : "medium"
  }
};
```

---

## Troubleshooting

### "qdrant": "disconnected" in /health

**Cause**: Qdrant URL or API key incorrect

**Fix**:
1. Double-check Qdrant Cloud URL
2. Verify API key is correct
3. Check Qdrant Cloud cluster is running

### "OpenAI embedding failed" in logs

**Cause**: Invalid OpenAI API key or rate limit

**Fix**:
```bash
# Switch to local embeddings
USE_LOCAL_EMBEDDINGS=true

# Or fix API key
OPENAI_API_KEY=sk-correct-key-here
```

### Products not showing in semantic search

**Cause**: Products not indexed yet

**Fix**:
```bash
# Index all products
curl -X POST https://dm-service-mpjf.onrender.com/rag/index/products/all \
  -H "X-API-Key: your-api-key"
```

### High memory usage on Render

**Cause**: Local embedding model loaded in memory

**Options**:
1. Switch to OpenAI embeddings: `USE_LOCAL_EMBEDDINGS=false`
2. Upgrade Render plan to 1GB+ RAM
3. Use keyword-only mode temporarily

---

## Rollback Plan

If you encounter issues, easy rollback:

1. **Revert to previous branch**:
   ```bash
   git checkout claude/fix-render-deployment-01UMdivpCptUegkSPAT2HNLb
   git push -f origin claude/implement-rag-system-011crjbhPkGNr4gAvF3mNoH7
   ```

2. **Or disable RAG features**:
   ```
   ENABLE_SEMANTIC_SEARCH=false
   ENABLE_KNOWLEDGE_BASE=false
   ```

   Service will work exactly as before.

---

## Support & Next Steps

### Immediate Actions
1. ✅ Deploy to Render
2. ✅ Set environment variables
3. ✅ Index products
4. ✅ Test endpoints
5. ✅ Monitor logs

### Within 24 Hours
1. Add knowledge base documents
2. Test semantic search quality
3. Monitor API costs
4. Fine-tune settings

### Within 1 Week
1. Collect user feedback
2. Adjust similarity thresholds
3. Add more FAQs
4. Optimize performance

### Resources
- Full documentation: `RAG_IMPLEMENTATION_GUIDE.md`
- API docs: https://dm-service-mpjf.onrender.com/docs
- Qdrant docs: https://qdrant.tech/documentation/
- OpenAI docs: https://platform.openai.com/docs/

---

## Summary

**Recommended Path**: Start with **Option 1** (Full RAG with Qdrant Cloud free tier)

**Why**:
- Best search quality
- Free tier sufficient for most stores
- Easy to upgrade later
- Full knowledge base support

**Timeline**:
- Setup: 15 minutes
- Initial indexing: 2-5 minutes
- Testing: 10 minutes
- **Total**: ~30 minutes to full RAG deployment 🚀

Happy deploying!
