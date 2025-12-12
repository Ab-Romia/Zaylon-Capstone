-- ============================================================================
-- Supabase Table Updates for AI Microservices
-- This file contains SQL queries to properly populate tags, categories, and
-- ensure all data is correctly structured for semantic search
-- ============================================================================

-- ============================================================================
-- PRODUCTS TABLE UPDATES
-- ============================================================================

-- Update products to add proper categories and tags based on their names/types
-- These updates ensure semantic search works properly for seasonal queries

-- Update Hoodies
UPDATE products
SET
    category = 'Hoodies',
    tags = ARRAY['winter', 'casual', 'cotton']
WHERE id = '5d0d14d0-7140-48b1-a053-bee4138e1418';  -- Essential Oversized Hoodie

UPDATE products
SET
    category = 'Hoodies',
    tags = ARRAY['winter', 'casual', 'streetwear']
WHERE id = '07cc3217-c7e0-4ef0-94c7-d735d01944bc';  -- Black Hoodie Premium

UPDATE products
SET
    category = 'Hoodies',
    tags = ARRAY['winter', 'casual', 'streetwear']
WHERE id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22';  -- Urban Street Hoodie

-- Update Jackets
UPDATE products
SET
    category = 'Outerwear',
    tags = ARRAY['jacket', 'vintage', 'casual']
WHERE id = '2722ea39-8877-4be3-bb75-1079e744ed9a';  -- Varsity Bomber Jacket

UPDATE products
SET
    category = 'Outerwear',
    tags = ARRAY['winter', 'jacket', 'warm']
WHERE id = 'c2b3ce8c-cf3a-4813-a8ff-ed377d1522aa';  -- Puffer Jacket

-- Update Pants
UPDATE products
SET
    category = 'Pants',
    tags = ARRAY['loungewear', 'sport', 'winter']
WHERE id = '3743b2b9-9b13-4548-8a72-92f72f79abdf';  -- Relaxed Fleece Joggers

UPDATE products
SET
    category = 'Pants',
    tags = ARRAY['techwear', 'utility', 'streetwear']
WHERE id = '5169023f-3536-4aba-bdbe-eb3925c3bdf6';  -- Cargo Techwear Pants

-- Update Jeans
UPDATE products
SET
    category = 'Jeans',
    tags = ARRAY['denim', 'casual']
WHERE id = '6d4fe886-d143-456c-a330-fa6b69db1393';  -- Distressed Slim-Fit Denim

UPDATE products
SET
    category = 'Jeans',
    tags = ARRAY['denim', 'casual', 'classic']
WHERE id = '03d98ea3-85df-4270-8217-ad9c779bb070';  -- Classic Blue Denim Jeans

-- Update T-Shirts
UPDATE products
SET
    category = 'T-Shirts',
    tags = ARRAY['graphic', 'vintage', 'summer']
WHERE id = '9873e3b2-9611-49f3-b554-ef4655816a0c';  -- Vintage Wash Graphic Tee

UPDATE products
SET
    category = 'T-Shirts',
    tags = ARRAY['basic', 'casual', 'summer']
WHERE id = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';  -- Classic Cotton T-Shirt

UPDATE products
SET
    category = 'T-Shirts',
    tags = ARRAY['basic', 'casual', 'summer']
WHERE id = '25bee0c2-1368-4a02-ac3d-9de6123b5ca8';  -- White Cotton T-Shirt

-- Update Sweatshirts
UPDATE products
SET
    category = 'Sweatshirts',
    tags = ARRAY['basic', 'layering', 'winter']
WHERE id = '91ca375b-1bf5-48ba-983b-7620e1b4f78c';  -- Minimalist Box Logo Crewneck

-- Update Shorts
UPDATE products
SET
    category = 'Shorts',
    tags = ARRAY['summer', 'smart-casual']
WHERE id = 'a1ef03d9-0d8e-4ca9-aeb1-c77c93500904';  -- Pleated Chino Shorts

-- Update Shirts
UPDATE products
SET
    category = 'Shirts',
    tags = ARRAY['summer', 'luxury', 'formal']
WHERE id = 'c4ab8cc7-3a35-4d7c-af38-c401c2a2b495';  -- Silk Button-Up Resort Shirt

-- Update Footwear
UPDATE products
SET
    category = 'Footwear',
    tags = ARRAY['sneakers', 'sport']
WHERE id = 'ad3eaf17-bd25-4a1d-9d40-50b24ed20361';  -- Street Runner Sneakers

UPDATE products
SET
    category = 'Footwear',
    tags = ARRAY['sneakers', 'classic']
WHERE id = 'e5827ef2-a78b-4caf-9218-ea3c74659ce4';  -- Canvas High-Tops

UPDATE products
SET
    category = 'Footwear',
    tags = ARRAY['shoes', 'leather', 'casual']
WHERE id = '30f0fcf1-33a5-4316-a91d-7f209053ea45';  -- Leather Sneakers

-- Update Accessories
UPDATE products
SET
    category = 'Accessories',
    tags = ARRAY['basics']
WHERE id = '4744b505-a520-417a-b10a-c99187898f70';  -- 3-Pack Crew Socks

UPDATE products
SET
    category = 'Accessories',
    tags = ARRAY['winter', 'hats']
WHERE id = 'b312e4aa-e2a8-4b1d-9ec8-aeb3e2bec409';  -- Ribbed Beanie

UPDATE products
SET
    category = 'Accessories',
    tags = ARRAY['bag', 'utility']
WHERE id = '9e04a26f-c08e-4c6c-9440-bada7ff08487';  -- Leather Crossbody Bag

UPDATE products
SET
    category = 'Accessories',
    tags = ARRAY['hat', 'casual', 'summer']
WHERE id = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33';  -- Vintage Dad Hat

-- Update Dresses
UPDATE products
SET
    category = 'Dresses',
    tags = ARRAY['summer', 'casual', 'floral']
WHERE id = '46ce5070-27ec-4767-bad1-7528796686c0';  -- Summer Dress Floral

-- ============================================================================
-- VERIFY PRODUCTS HAVE PROPER STRUCTURE
-- ============================================================================

-- Query to see all products with their tags and categories
-- Run this to verify updates
SELECT
    id,
    name,
    category,
    tags,
    colors,
    sizes,
    stock_count,
    is_active
FROM products
ORDER BY category, name;

-- Query to find products missing tags or categories
SELECT
    id,
    name,
    category,
    tags
FROM products
WHERE tags IS NULL OR tags = '{}' OR category IS NULL OR category = '';

-- ============================================================================
-- KNOWLEDGE BASE TABLE VERIFICATION
-- ============================================================================

-- Verify knowledge base documents have proper tags and metadata
SELECT
    id,
    doc_id,
    title,
    category,
    tags,
    metadata,
    is_active,
    LEFT(content, 100) as content_preview
FROM knowledge_base
WHERE is_active = true
ORDER BY category, title;

-- Check for knowledge base docs without proper metadata
SELECT
    id,
    doc_id,
    title,
    category,
    tags
FROM knowledge_base
WHERE (tags IS NULL OR tags = '{}' OR category IS NULL OR category = '')
  AND is_active = true;

-- ============================================================================
-- UPDATE KNOWLEDGE BASE FOR BETTER SEMANTIC SEARCH
-- ============================================================================

-- Update shipping policy to ensure Cairo is clearly associated
UPDATE knowledge_base
SET
    tags = ARRAY['shipping', 'delivery', 'cairo', 'egypt', 'locations'],
    metadata = jsonb_build_object(
        'tags', ARRAY['shipping', 'delivery', 'cairo', 'egypt', 'locations'],
        'title', 'Shipping Policy',
        'category', 'policies',
        'cities', ARRAY['Cairo', 'Alexandria', 'Giza', 'Luxor', 'Aswan', 'Hurghada', 'Sharm El-Sheikh']
    )
WHERE doc_id = 'shipping_policy';

-- Update return policy tags
UPDATE knowledge_base
SET
    tags = ARRAY['return', 'refund', 'exchange', 'policy'],
    metadata = jsonb_build_object(
        'tags', ARRAY['return', 'refund', 'exchange', 'policy'],
        'title', 'Return Policy',
        'category', 'policies'
    )
WHERE doc_id = 'return_policy';

-- Update payment methods tags
UPDATE knowledge_base
SET
    tags = ARRAY['payment', 'credit card', 'cash', 'vodafone', 'fawry'],
    metadata = jsonb_build_object(
        'tags', ARRAY['payment', 'credit card', 'cash', 'vodafone', 'fawry'],
        'title', 'Payment Methods',
        'category', 'policies'
    )
WHERE doc_id = 'payment_methods';

-- Update order cancellation tags
UPDATE knowledge_base
SET
    tags = ARRAY['cancel', 'cancellation', 'order', 'refund'],
    metadata = jsonb_build_object(
        'tags', ARRAY['cancel', 'cancellation', 'order', 'refund'],
        'title', 'Order Cancellation',
        'category', 'policies'
    )
WHERE doc_id = 'order_cancellation';

-- Update order modification tags
UPDATE knowledge_base
SET
    tags = ARRAY['change order', 'modify', 'update order', 'size change'],
    metadata = jsonb_build_object(
        'tags', ARRAY['change order', 'modify', 'update order', 'size change'],
        'title', 'Order Modification',
        'category', 'policies'
    )
WHERE doc_id = 'order_modification';

-- Update sizing guide tags
UPDATE knowledge_base
SET
    tags = ARRAY['size', 'sizing', 'measurements', 'fit'],
    metadata = jsonb_build_object(
        'tags', ARRAY['size', 'sizing', 'measurements', 'fit'],
        'title', 'Sizing Guide',
        'category', 'guides'
    )
WHERE doc_id = 'sizing_guide';

-- Update damaged items policy tags
UPDATE knowledge_base
SET
    tags = ARRAY['damaged', 'defective', 'broken', 'complaint', 'quality'],
    metadata = jsonb_build_object(
        'tags', ARRAY['damaged', 'defective', 'broken', 'complaint', 'quality'],
        'title', 'Damaged Items Policy',
        'category', 'policies'
    )
WHERE doc_id = 'damaged_items';

-- ============================================================================
-- FINAL VERIFICATION QUERIES
-- ============================================================================

-- Count products by category
SELECT
    category,
    COUNT(*) as product_count,
    SUM(stock_count) as total_stock
FROM products
WHERE is_active = true
GROUP BY category
ORDER BY product_count DESC;

-- Count winter products (should show all winter items)
SELECT COUNT(*) as winter_product_count
FROM products
WHERE is_active = true
  AND ('winter' = ANY(tags) OR
       category ILIKE '%winter%' OR
       name ILIKE '%winter%' OR
       description ILIKE '%winter%');

-- Show all winter products
SELECT
    name,
    category,
    tags,
    stock_count
FROM products
WHERE is_active = true
  AND ('winter' = ANY(tags) OR
       category ILIKE '%winter%' OR
       name ILIKE '%winter%' OR
       description ILIKE '%winter%')
ORDER BY stock_count DESC;

-- ============================================================================
-- NOTES FOR RUNNING THESE QUERIES:
-- ============================================================================
-- 1. Run all UPDATE statements first to populate tags and categories
-- 2. Run verification queries to confirm updates
-- 3. After running these updates, re-index all products using:
--    POST /api/v1/rag/index/products/all
-- 4. This will ensure the vector database (Qdrant) has the updated information
-- ============================================================================
