-- E-commerce DM Microservice Database Schema
-- PostgreSQL migration file
-- Run this to create all required tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- NOTE: Products and Orders tables already exist in Supabase
-- These are here for reference only - DO NOT recreate if they already exist
-- ============================================================================

-- Products table (reference - likely already exists)
-- CREATE TABLE IF NOT EXISTS products (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(255) NOT NULL,
--     price FLOAT NOT NULL,
--     sizes TEXT[] DEFAULT '{}',
--     colors TEXT[] DEFAULT '{}',
--     stock_count INT DEFAULT 0,
--     description TEXT DEFAULT '',
--     is_active BOOLEAN DEFAULT TRUE
-- );

-- Orders table (reference - likely already exists)
-- CREATE TABLE IF NOT EXISTS orders (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     product_id UUID REFERENCES products(id),
--     product_name VARCHAR(255),
--     size VARCHAR(50),
--     color VARCHAR(50),
--     quantity INT DEFAULT 1,
--     total_price FLOAT,
--     customer_name VARCHAR(255),
--     customer_phone VARCHAR(50),
--     delivery_address TEXT,
--     status VARCHAR(50) DEFAULT 'pending',
--     instagram_user VARCHAR(255),
--     created_at TIMESTAMP DEFAULT NOW()
-- );

-- ============================================================================
-- NEW TABLES FOR MICROSERVICE
-- ============================================================================

-- Conversations table - stores all messages
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL CHECK (channel IN ('instagram', 'whatsapp')),
    message TEXT NOT NULL,
    direction VARCHAR(20) NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    intent VARCHAR(100),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_customer_created ON conversations(customer_id, created_at);
CREATE INDEX IF NOT EXISTS idx_conversations_intent ON conversations(intent);

-- Customers table - customer profiles with cross-channel linking
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    primary_id VARCHAR(255) UNIQUE NOT NULL,
    linked_ids JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for customers
CREATE INDEX IF NOT EXISTS idx_customers_primary ON customers(primary_id);
CREATE INDEX IF NOT EXISTS idx_customers_linked ON customers USING GIN (linked_ids);

-- Response cache table
CREATE TABLE IF NOT EXISTS response_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_hash VARCHAR(64) UNIQUE NOT NULL,
    normalized_message TEXT NOT NULL,
    cached_response TEXT NOT NULL,
    intent VARCHAR(100),
    hit_count INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

-- Indexes for response cache
CREATE INDEX IF NOT EXISTS idx_cache_hash ON response_cache(message_hash);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON response_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_intent ON response_cache(intent);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    response_time_ms INT,
    ai_tokens_used INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for analytics
CREATE INDEX IF NOT EXISTS idx_analytics_customer ON analytics_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_created ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_type_created ON analytics_events(event_type, created_at);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for customers table
DROP TRIGGER IF EXISTS update_customers_updated_at ON customers;
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DATA CLEANUP FUNCTIONS
-- ============================================================================

-- Function to cleanup expired cache entries
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM response_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup old analytics (older than retention period)
CREATE OR REPLACE FUNCTION cleanup_old_analytics(retention_days INT DEFAULT 90)
RETURNS INT AS $$
DECLARE
    deleted_count INT;
BEGIN
    DELETE FROM analytics_events
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Uncomment to add sample products for testing
-- INSERT INTO products (name, price, sizes, colors, stock_count, description, is_active) VALUES
-- ('Classic Blue Denim Jeans', 599.00, ARRAY['30', '32', '34', '36'], ARRAY['blue', 'navy'], 25, 'High-quality denim jeans, perfect fit', TRUE),
-- ('Black Hoodie Premium', 450.00, ARRAY['S', 'M', 'L', 'XL'], ARRAY['black', 'gray'], 30, 'Comfortable cotton blend hoodie', TRUE),
-- ('White Cotton T-Shirt', 199.00, ARRAY['S', 'M', 'L', 'XL', 'XXL'], ARRAY['white', 'black', 'gray'], 50, 'Basic cotton t-shirt', TRUE),
-- ('Leather Sneakers', 899.00, ARRAY['40', '41', '42', '43', '44'], ARRAY['white', 'black'], 15, 'Premium leather sneakers', TRUE),
-- ('Summer Dress Floral', 750.00, ARRAY['S', 'M', 'L'], ARRAY['pink', 'blue', 'yellow'], 20, 'Light floral summer dress', TRUE);

-- ============================================================================
-- GRANTS (adjust according to your user)
-- ============================================================================

-- Grant permissions to your database user
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_user;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these to verify the schema was created correctly:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- SELECT indexname FROM pg_indexes WHERE schemaname = 'public';
