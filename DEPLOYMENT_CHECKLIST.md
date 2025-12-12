# Deployment Checklist - Complete System Fixes

## ⚠️ CRITICAL: You MUST follow these steps in order!

---

## Step 1: Update Database Tables in Supabase

### 1.1 Run SQL Updates
```sql
-- In Supabase SQL Editor, copy and paste ALL queries from:
-- supabase_table_updates.sql
-- This adds tags and categories to all products
```

**What this does**:
- Adds `tags: ["winter","casual","cotton"]` to winter products
- Adds `category: "Hoodies"` to hoodies
- Updates knowledge base metadata with location info
- Makes products searchable by season and category

**Verify**:
```sql
-- Check products have tags
SELECT name, category, tags FROM products WHERE tags IS NOT NULL;

-- Should see:
-- Essential Oversized Hoodie | Hoodies | ["winter","casual","cotton"]
-- Puffer Jacket | Outerwear | ["winter","jacket","warm"]
-- etc.
```

---

## Step 2: Index Products in Qdrant

### 2.1 Re-index ALL Products

**Option A - Via API** (Recommended):
```bash
curl -X POST https://your-api-url/api/v1/rag/index/products/all \
  -H "Content-Type: application/json"
```

**Option B - Via Script** (If server running locally):
```bash
cd /home/romia/PycharmProjects/AI_Microservices
python scripts/populate_knowledge_base.py
```

**What this does**:
- Fetches all active products from database (with NEW tags and categories)
- Creates embeddings including tags/category text
- Upserts to Qdrant vector database
- Takes 1-2 minutes for ~20 products

**Verify**:
```bash
# Check Qdrant collection status
curl -X GET https://your-api-url/api/v1/rag/status
# Should show:
# {
#   "products_collection": {
#     "points_count": 20,  # Should match number of active products
#     ...
#   }
# }
```

---

## Step 3: Index Knowledge Base from Database

### 3.1 Run NEW Indexing Script

**CRITICAL**: The old `populate_knowledge_base.py` only indexes 7 hardcoded documents. The new script indexes ALL 17 documents from your database!

```bash
cd /home/romia/PycharmProjects/AI_Microservices
python scripts/index_knowledge_from_db.py
```

**What this does**:
- Pulls ALL active docs from `knowledge_base` table in Supabase
- Includes `shipping_policy` with Cairo details
- Indexes all 17 documents into Qdrant
- Creates chunks with proper metadata

**Expected Output**:
```
========================================================================
INDEXING KNOWLEDGE BASE FROM DATABASE
========================================================================
✅ Qdrant connected
📚 Found 17 active knowledge base documents in database

[1/17] Indexing: shipping_policy - Shipping Policy
  ✅ Successfully indexed

[2/17] Indexing: return_policy - Return Policy
  ✅ Successfully indexed

...

========================================================================
INDEXING COMPLETE
========================================================================
Total documents: 17
Successfully indexed: 17
Failed: 0

📊 Knowledge Base Collection Status:
   Points count: 51  # Multiple chunks per document
   Vectors dimension: 1536
```

**Verify**:
```bash
# Test shipping query
curl -X POST https://your-api-url/api/v1/rag/search/knowledge \
  -H "Content-Type: application/json" \
  -d '{"query": "do you ship to cairo?"}'

# Should return shipping_policy with Cairo mentioned
```

---

## Step 4: Restart Services

### 4.1 Restart Application

**If using Docker**:
```bash
docker-compose restart
```

**If using systemd**:
```bash
systemctl restart zaylon-api
```

**If using PM2**:
```bash
pm2 restart zaylon-api
```

**Why**: Ensures new code is loaded and connections are refreshed

---

## Step 5: Test All Fixes

### 5.1 Test Winter Products
```bash
# Query 1: English
"do you have winter clothes?"

# Expected: Returns 5-6 winter items
# - Essential Oversized Hoodie
# - Puffer Jacket
# - Ribbed Beanie
# - etc.

# Query 2: Franco-Arabic
"howa ento 3ndoko 7gat 7elwa lel sheta?"

# Expected: Same winter products

# Query 3: Arabic
"عندكم حاجات للشتاء؟"

# Expected: Same winter products
```

### 5.2 Test Cairo Shipping
```bash
# Query 1: English
"do you ship to cairo?"

# Expected:
# "Yes! We ship to all major cities in Egypt including Cairo and Greater Cairo.
# Shipping to Cairo typically takes 1-2 business days. Orders over 500 EGP
# get FREE shipping!"

# Query 2: Arabic
"بتوصلوا القاهرة؟"

# Expected: Same shipping info in Arabic
```

### 5.3 Test Sales Agent Persistence
```bash
# Query 1:
"recommend me 2 shirts and 2 pants for casual bold dark colors"

# Expected: Agent makes multiple searches and ALWAYS shows products
# Should return 2 shirts + 2 pants recommendations
# NEVER says "I couldn't find anything"

# Query 2: Intentionally vague
"show me products"

# Expected: Agent shows top products enthusiastically
# NEVER gives up
```

### 5.4 Test Return Policy (Should Still Work)
```bash
# Query:
"what's your return policy?"

# Expected: Return policy details (30-day return, etc.)
```

---

## Troubleshooting

### Problem: "Winter clothes" returns 0 products

**Cause**: Products not re-indexed after SQL updates

**Fix**:
```bash
# Re-run product indexing
python scripts/populate_knowledge_base.py
# OR
curl -X POST https://your-api-url/api/v1/rag/index/products/all
```

---

### Problem: "Ship to Cairo" returns "I don't know"

**Cause**: Knowledge base not indexed from database

**Fix**:
```bash
# Run the NEW script (not the old one)
python scripts/index_knowledge_from_db.py

# Verify it indexed shipping_policy
curl -X GET https://your-api-url/api/v1/rag/status
# Check knowledge_base collection has 50+ points
```

---

### Problem: Agent still says "I couldn't find..."

**Cause**: Old code still running

**Fix**:
```bash
# Fully restart services
docker-compose down
docker-compose up -d

# OR force reload
systemctl restart zaylon-api

# Verify new code is running by checking logs
tail -f /var/log/zaylon-api.log | grep "NEVER GIVE UP"
```

---

### Problem: Qdrant connection errors

**Check**:
```bash
# Is Qdrant running?
docker ps | grep qdrant

# Can you connect?
curl http://localhost:6333/collections
```

**Fix**:
```bash
# Start Qdrant
docker-compose up -d qdrant

# Check it's accessible
curl http://localhost:6333/collections
```

---

## Verification Checklist

- [ ] SQL updates applied to Supabase products table
- [ ] Products re-indexed in Qdrant (POST /rag/index/products/all)
- [ ] Knowledge base indexed from database (python scripts/index_knowledge_from_db.py)
- [ ] Services restarted
- [ ] Winter products query returns results
- [ ] Cairo shipping query returns policy
- [ ] Sales agent never gives up
- [ ] Return policy still works

---

## Files Modified in Latest Commits

| File | Purpose |
|------|---------|
| `services/ingestion.py` | Include tags/category in product embeddings |
| `services/rag.py` | Return tags/category + fallback threshold for KB |
| `services/products.py` | Seasonal keywords + never return 0 products |
| `config.py` | Lower thresholds (0.5→0.35), smaller chunks (500→300) |
| `app/agents/nodes.py` | Proactive sales behavior + missing import fix |
| `supabase_table_updates.sql` | Database update queries |
| `scripts/index_knowledge_from_db.py` | NEW - Index ALL KB docs from database |
| `SEMANTIC_SEARCH_FIXES.md` | Complete documentation |
| `DEPLOYMENT_CHECKLIST.md` | This file |

---

## Expected Results After Deployment

### Before:
- ❌ "Winter clothes" → 0 results
- ❌ "Ship to Cairo" → "I don't know"
- ❌ "Recommend products" → "I couldn't find anything"
- ❌ Agent gives up easily

### After:
- ✅ "Winter clothes" → 5-6 winter items
- ✅ "Ship to Cairo" → Shipping policy with Cairo details
- ✅ "Recommend products" → Always shows products
- ✅ Agent NEVER gives up, always closes sales

---

## Support

If issues persist:

1. Check logs: `tail -f logs/app.log`
2. Verify Qdrant collections: `curl http://localhost:6333/collections`
3. Test search directly: `curl -X POST .../rag/search/products -d '{"query":"winter"}'`
4. Check database: `SELECT * FROM products WHERE tags @> ARRAY['winter']`

All fixes are committed and pushed to `refactor-sales-agent-complete` branch.
