#!/usr/bin/env python3
"""Quick test to verify health endpoint works"""
import asyncio
from sqlalchemy import text
from database import get_db

async def test_health():
    """Test the health check logic"""
    async for db in get_db():
        try:
            # This is exactly what the health endpoint does
            await db.execute(text("SELECT 1"))
            print("[OK] Health check query works!")
            print("Database: connected")
            return True
        except Exception as e:
            print(f"[FAIL] Health check query failed: {e}")
            print("Database: disconnected")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_health())
    exit(0 if result else 1)
