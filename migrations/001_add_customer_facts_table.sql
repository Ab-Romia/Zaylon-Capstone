-- Migration: Add customer_facts table for Memory Bank
-- This table stores long-term customer preferences and facts for the agentic system

CREATE TABLE IF NOT EXISTS customer_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(255) NOT NULL,
    fact_type VARCHAR(100) NOT NULL, -- preference, constraint, personal_info
    fact_key VARCHAR(255) NOT NULL, -- e.g., "preferred_size", "favorite_color"
    fact_value TEXT NOT NULL, -- The actual value
    confidence INTEGER DEFAULT 100, -- 0-100, how confident we are
    source VARCHAR(50), -- 'explicit' (user stated) or 'inferred' (agent deduced)
    metadata JSONB DEFAULT '{}', -- Additional context
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_customer_facts_customer ON customer_facts(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_facts_key ON customer_facts(customer_id, fact_key);
CREATE INDEX IF NOT EXISTS idx_customer_facts_type ON customer_facts(fact_type);

-- Create trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_customer_facts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_customer_facts_updated_at
    BEFORE UPDATE ON customer_facts
    FOR EACH ROW
    EXECUTE FUNCTION update_customer_facts_updated_at();

-- Add comments for documentation
COMMENT ON TABLE customer_facts IS 'Memory Bank: Long-term storage of customer preferences and learned facts';
COMMENT ON COLUMN customer_facts.fact_type IS 'Type of fact: preference, constraint, personal_info';
COMMENT ON COLUMN customer_facts.fact_key IS 'Unique identifier for the fact (e.g., preferred_size, favorite_color)';
COMMENT ON COLUMN customer_facts.confidence IS 'Confidence level (0-100): 100 for explicit, lower for inferred';
COMMENT ON COLUMN customer_facts.source IS 'Origin of fact: explicit (user stated) or inferred (agent deduced)';
