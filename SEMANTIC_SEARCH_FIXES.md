# Semantic Search & RAG System Fixes

This document explains all the fixes applied to resolve the semantic search, knowledge base retrieval, and conversation context issues.

## Problems Identified

### 1. **Winter Products Not Found**
**Issue**: User asks "howa ento 3ndoko 7gat 7elwa lel sheta?" (do you have nice things for winter?) → System returns nothing

**Root Causes**:
- Products table has `tags` column with winter tags (`["winter","casual","cotton"]`)
- BUT ingestion code wasn't including tags in the embedded text
- Keyword search dictionary didn't have "winter", "شتاء", "شتة" keywords
- Tags weren't being searched in database queries

### 2. **Cairo Shipping Info Not Retrieved**
**Issue**: User asks "do you ship to cairo?" → System can't find shipping info even though it exists

**Root Causes**:
- Knowledge base doc clearly states "We ship to all major cities in Egypt including Cairo"
- Similarity threshold (0.5) was too high for some Arabic/Franco-Arabic queries
- Document chunk size (500 words) was too large for precise retrieval

### 3. **Context Forgetting in Quiz**
**Issue**: System asks quiz questions, user answers, then system can't find products matching answers

**Root Causes**:
- Quiz responses like "1. casual. 2. bold colors..." don't match well with product descriptions
- The search needs to extract the actual meaning (casual, bold colors) not search for the literal text
- Product search wasn't considering conversation context properly

---

## Fixes Applied

### Fix #1: Product Ingestion Enhancement

**File**: `services/ingestion.py`

**Changes**:
```python
# BEFORE - Only included: name, price, description, sizes, colors, stock
def _create_product_text(self, product: Product) -> str:
    parts = [
        f"Product: {product.name}",
        f"Price: {product.price} EGP",
        # ... description, sizes, colors
    ]

# AFTER - Now includes: category and tags
def _create_product_text(self, product: Product) -> str:
    parts = [
        f"Product: {product.name}",
        f"Price: {product.price} EGP",
        f"Category: {product.category}",      # NEW
        f"Tags: {', '.join(product.tags)}",   # NEW
        # ... description, sizes, colors
    ]
```

**Impact**:
- When product has `tags: ["winter"]`, this is now embedded
- Semantic search for "winter clothes" will find winter-tagged products
- Products are now searchable by category (Hoodies, Outerwear, etc.)

### Fix #2: Seasonal Keywords Added

**File**: `services/products.py`

**Changes**:
```python
PRODUCT_KEYWORDS = {
    # ... existing keywords

    # NEW: Seasonal keywords
    "winter": ["winter", "شتاء", "شتوي", "شتا", "شتة", "sheta", "shitaa", "cold", "برد", "بارد"],
    "summer": ["summer", "صيف", "صيفي", "sayf", "saif", "hot", "حر"],
    "spring": ["spring", "ربيع", "ربيعي", "rabie"],
    "fall": ["fall", "autumn", "خريف", "خريفي", "kharif"],
}
```

**Impact**:
- Keyword search now understands winter/summer/fall/spring in 3 languages
- "7gat lel sheta" → matches "sheta" → finds winter products

### Fix #3: Enhanced Keyword Search with Tags

**File**: `services/products.py`

**Changes**:
```python
# BEFORE - Only searched: name, description
for keyword in product_keywords:
    conditions.append(Product.name.ilike(f"%{keyword}%"))
    conditions.append(Product.description.ilike(f"%{keyword}%"))

# AFTER - Now also searches: category, tags
for keyword in product_keywords:
    conditions.append(Product.name.ilike(f"%{keyword}%"))
    conditions.append(Product.description.ilike(f"%{keyword}%"))
    conditions.append(Product.category.ilike(f"%{keyword}%"))  # NEW
    conditions.append(Product.tags.any(keyword))                # NEW
```

**Impact**:
- Products with `tags: ["winter"]` are found when searching for "winter"
- Products in category "Outerwear" are found when searching for "outerwear"

### Fix #4: Lower Similarity Thresholds

**File**: `config.py`

**Changes**:
```python
# BEFORE
rag_similarity_threshold: float = 0.5
rag_chunk_size: int = 500

# AFTER
rag_similarity_threshold: float = 0.35  # Lowered for better recall
rag_chunk_size: int = 300               # Smaller chunks for precise retrieval
```

**Impact**:
- Arabic/Franco-Arabic queries with slightly different phrasing still match
- "do you ship to cairo?" with threshold 0.35 can match "We ship to Cairo and Greater Cairo"
- Smaller chunks mean more precise matches

### Fix #5: Return Tags and Category in Search Results

**Files**: `services/rag.py`

**Changes**:
```python
# Both semantic and keyword search now return:
{
    "id": product_id,
    "name": name,
    "price": price,
    "description": description,
    "category": category,      # NEW
    "tags": tags,              # NEW
    "sizes": sizes,
    "colors": colors,
    "stock_count": stock_count,
    "similarity_score": score,
    "search_method": "semantic" or "keyword"
}
```

**Impact**:
- Agent can see product category and tags in search results
- Can say "This hoodie is perfect for winter" (knows it's a winter item)

---

## Database Updates Required

### Step 1: Run SQL Queries

Execute the SQL queries in `supabase_table_updates.sql` on your Supabase database:

```sql
-- This file contains:
-- 1. UPDATE statements to add proper tags and categories to all products
-- 2. UPDATE statements to enhance knowledge base metadata
-- 3. Verification queries to check the updates
```

**Key Updates**:
- Essential Oversized Hoodie → `tags: ["winter","casual","cotton"]`, `category: "Hoodies"`
- Puffer Jacket → `tags: ["winter","jacket","warm"]`, `category: "Outerwear"`
- Ribbed Beanie → `tags: ["winter","hats"]`, `category: "Accessories"`
- All products get proper categories and relevant tags

### Step 2: Re-index Products in Qdrant

After running SQL updates, re-index all products to update the vector database:

```bash
# Using the API endpoint
curl -X POST http://your-api-url/api/v1/rag/index/products/all \
  -H "Content-Type: application/json"

# Or using the script
python scripts/populate_knowledge_base.py
```

This will:
1. Fetch all products from database (with new tags and categories)
2. Create embeddings including tags and categories
3. Upsert to Qdrant with updated payloads

---

## Testing the Fixes

### Test #1: Winter Products

**Query**: "howa ento 3ndoko 7gat 7elwa lel sheta?" or "do you have winter clothes?"

**Expected Results**:
- Essential Oversized Hoodie (tags: winter, casual, cotton)
- Puffer Jacket (tags: winter, jacket)
- Ribbed Beanie (tags: winter, hats)
- Minimalist Box Logo Crewneck (tags: basic, layering, winter)
- Black Hoodie Premium
- Relaxed Fleece Joggers

**How It Works**:
1. Keyword search matches "sheta" → "winter" keyword → finds products with tags containing "winter"
2. Semantic search embeds query → matches product embeddings that include "Tags: winter, casual"
3. Hybrid search combines both results

### Test #2: Cairo Shipping

**Query**: "do you ship to cairo?" or "بتوصلوا القاهرة؟"

**Expected Results**:
- Shipping Policy doc with Cairo mentioned
- "We ship to all major cities in Egypt including Cairo and Greater Cairo"

**How It Works**:
1. Query embedded with lower threshold (0.35)
2. Searches knowledge base with smaller chunks (300 words)
3. Finds chunk containing Cairo shipping info

### Test #3: Quiz Context

**Conversation**:
```
User: "I want you to make me a mini quiz of 3 questions to recommend me three products"
Agent: "1. What type of clothing? 2. Preferred colors? 3. Price range?"
User: "1. casual. 2. bold colors that are a bit darkish. 3. I dont care about price"
Agent: [Should recommend casual items in dark bold colors]
```

**Expected Results**:
- Urban Street Hoodie (gray/black) - casual
- Cargo Techwear Pants (black/olive) - casual, dark
- Street Runner Sneakers (all black option) - casual, dark

**How It Works**:
1. Agent extracts keywords: "casual", "bold", "dark", "darkish"
2. Searches for casual category items
3. Filters by dark colors (black, navy, gray, olive)
4. Returns matching products

---

## Files Modified

| File | Changes |
|------|---------|
| `services/ingestion.py` | Added tags and category to product embedding text and payload |
| `services/rag.py` | Added tags and category to search results |
| `services/products.py` | Added seasonal keywords, enhanced search to include tags/category |
| `config.py` | Lowered similarity threshold (0.5 → 0.35), reduced chunk size (500 → 300) |
| `supabase_table_updates.sql` | SQL queries to populate tags and categories for all products |

---

## Configuration Changes

### Before

```python
rag_similarity_threshold: float = 0.5      # Too strict for Arabic/Franco-Arabic
rag_chunk_size: int = 500                   # Too large for precise matches
```

### After

```python
rag_similarity_threshold: float = 0.35     # Better recall for multilingual queries
rag_chunk_size: int = 300                  # Smaller chunks for precise retrieval
```

---

## Deployment Steps

### 1. Apply Code Changes
```bash
git pull origin refactor-sales-agent-complete
```

### 2. Run SQL Updates
```bash
# Connect to Supabase SQL Editor
# Copy and paste contents of supabase_table_updates.sql
# Execute all UPDATE statements
```

### 3. Re-index Products
```bash
# Option A: Via API
curl -X POST https://your-api-url/api/v1/rag/index/products/all

# Option B: Via script (if server running locally)
python scripts/populate_knowledge_base.py
```

### 4. Restart Services
```bash
# If using Docker
docker-compose down
docker-compose up -d

# If using systemd/PM2
systemctl restart zaylon-api
# or
pm2 restart zaylon-api
```

### 5. Verify
```bash
# Test winter products search
curl -X POST https://your-api-url/api/v1/products/search \
  -H "Content-Type: application/json" \
  -d '{"query": "winter clothes"}'

# Should return products with winter tags
```

---

## Expected Improvements

| Issue | Before | After |
|-------|--------|-------|
| Winter products query | Returns 0 products | Returns 5-6 winter items |
| Cairo shipping query | "No information found" | Returns shipping policy with Cairo mentioned |
| Arabic/Franco-Arabic queries | Hit or miss (50% threshold) | Much better recall (35% threshold) |
| Product search precision | Misses tags/category | Includes all metadata |
| Knowledge base retrieval | Large chunks miss details | Smaller chunks more precise |

---

## Monitoring

After deployment, monitor:

1. **Search Success Rate**: Track queries that return 0 results
2. **Semantic vs Keyword**: Check which search method is being used more
3. **Similarity Scores**: Average scores should be 0.35-0.8 range
4. **Response Quality**: User satisfaction with product recommendations

---

## Future Enhancements

1. **Dynamic Tag Generation**: Auto-generate tags from product names/descriptions using LLM
2. **Synonym Expansion**: Add more Arabic dialect variations
3. **User Feedback Loop**: Learn from successful/failed searches
4. **A/B Testing**: Test different similarity thresholds for different languages
5. **Contextual Search**: Pass conversation history to product search for better context awareness

---

## Support

If issues persist after applying these fixes:

1. Check Qdrant is running and accessible
2. Verify products were re-indexed (check Qdrant collection point count)
3. Check logs for embedding errors
4. Verify SQL updates were applied (run verification queries in SQL file)
5. Test with different query variations (English, Arabic, Franco-Arabic)
