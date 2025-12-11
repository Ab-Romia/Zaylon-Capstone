-- Migration: Add Full-Text Search indexes for performance optimization
-- Phase 1.2: Database Query Optimization
-- Target: -500ms on product searches

-- ============================================================================
-- Full-Text Search for Products
-- ============================================================================

-- Add tsvector column for full-text search (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'products' AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE products ADD COLUMN search_vector tsvector;
    END IF;
END $$;

-- Create GIN index on search_vector for fast full-text search
CREATE INDEX IF NOT EXISTS idx_products_search_vector
ON products USING GIN(search_vector);

-- Create function to update search_vector
CREATE OR REPLACE FUNCTION products_search_vector_trigger() RETURNS trigger AS $$
BEGIN
    -- Build search vector with weighted fields:
    -- A = highest weight (name)
    -- B = high weight (description)
    -- C = medium weight (tags, category)
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.tags, ' '), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.category, '')), 'C');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update search_vector
DROP TRIGGER IF EXISTS products_search_vector_update ON products;
CREATE TRIGGER products_search_vector_update
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION products_search_vector_trigger();

-- Update existing products to populate search_vector
UPDATE products
SET search_vector =
    setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
    setweight(to_tsvector('simple', COALESCE(array_to_string(tags, ' '), '')), 'C') ||
    setweight(to_tsvector('simple', COALESCE(category, '')), 'C')
WHERE search_vector IS NULL;

-- ============================================================================
-- Additional Performance Indexes
-- ============================================================================

-- Index for active products filtering (most common query)
CREATE INDEX IF NOT EXISTS idx_products_is_active_stock
ON products(is_active, stock_count DESC)
WHERE is_active = true AND stock_count > 0;

-- Index for category filtering
CREATE INDEX IF NOT EXISTS idx_products_category_active
ON products(category, is_active)
WHERE is_active = true;

-- Index for bestsellers
CREATE INDEX IF NOT EXISTS idx_products_bestseller
ON products(is_bestseller, is_active)
WHERE is_bestseller = true AND is_active = true;

-- Partial index for out-of-stock products
CREATE INDEX IF NOT EXISTS idx_products_out_of_stock
ON products(id)
WHERE is_active = true AND stock_count = 0;

-- ============================================================================
-- Customer Facts Optimization
-- ============================================================================

-- Composite index for customer facts lookup
CREATE INDEX IF NOT EXISTS idx_customer_facts_customer_key
ON customer_facts(customer_id, fact_key);

-- Index for recent facts (for batch loading)
CREATE INDEX IF NOT EXISTS idx_customer_facts_customer_updated
ON customer_facts(customer_id, updated_at DESC);

-- ============================================================================
-- Orders Optimization
-- ============================================================================

-- Composite index for order history queries
CREATE INDEX IF NOT EXISTS idx_orders_customer_created
ON orders(customer_id, created_at DESC);

-- Index for order status filtering
CREATE INDEX IF NOT EXISTS idx_orders_customer_status
ON orders(customer_id, status, created_at DESC);

-- ============================================================================
-- Analytics & Monitoring
-- ============================================================================

-- Track migration execution
INSERT INTO analytics_events (
    customer_id,
    event_type,
    event_data,
    created_at
) VALUES (
    'system',
    'migration_executed',
    jsonb_build_object(
        'migration', '002_add_fulltext_search_indexes',
        'phase', '1.2',
        'description', 'Added full-text search indexes for performance optimization'
    ),
    NOW()
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- Verification Queries (for testing)
-- ============================================================================

-- Test full-text search (uncomment to test)
-- SELECT name, description, ts_rank(search_vector, query) AS rank
-- FROM products, to_tsquery('english', 'hoodie') query
-- WHERE search_vector @@ query
-- ORDER BY rank DESC
-- LIMIT 5;

-- Verify indexes created
-- SELECT schemaname, tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'products'
-- ORDER BY indexname;

COMMIT;
