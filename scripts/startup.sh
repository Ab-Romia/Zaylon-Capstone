#!/bin/bash
# Startup script for production deployment
# Runs knowledge base ingestion and validation before starting the server

set -e  # Exit on any error

echo "==============================================="
echo "STARTUP: AI Sales Agent System"
echo "==============================================="
echo ""

# Set Python path to include /app directory
export PYTHONPATH=/app:$PYTHONPATH

# Step 1: Populate knowledge base from DATABASE (not hardcoded docs)
echo "Step 1: Indexing knowledge base from database..."
python scripts/index_knowledge_from_db.py
if [ $? -ne 0 ]; then
    echo "⚠️  Knowledge base indexing failed, falling back to hardcoded docs"
    python scripts/populate_knowledge_base.py
    if [ $? -ne 0 ]; then
        echo "❌ Knowledge base population failed"
        exit 1
    fi
fi
echo ""

# Step 2: Validate collections
echo "Step 2: Validating Qdrant collections..."
python scripts/validate_collections.py
if [ $? -ne 0 ]; then
    echo "❌ Collection validation failed"
    exit 1
fi
echo ""

# Step 3: Start the server
echo "Step 3: Starting server..."
echo "==============================================="
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
