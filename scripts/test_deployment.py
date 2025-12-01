"""
Pre-Deployment Test Suite for E-commerce DM Microservice
Tests database connections, table schemas, and API endpoints.
"""
import asyncio
import sys
import httpx
from datetime import datetime, timedelta
from sqlalchemy import text, inspect
from database import engine, init_db, async_session, Product, Order, Conversation, Customer, ResponseCache, AnalyticsEvent
from config import get_settings

settings = get_settings()

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_test(name, status, message=""):
    symbol = f"{GREEN}[OK]{RESET}" if status else f"{RED}[FAIL]{RESET}"
    print(f"{symbol} {name}")
    if message:
        print(f"  └─ {message}")


async def test_database_connection():
    """Test basic database connectivity."""
    print_header("DATABASE CONNECTION TESTS")

    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print_test("Database connection", True, f"PostgreSQL version: {version.split(',')[0]}")
            return True
    except Exception as e:
        print_test("Database connection", False, f"Error: {str(e)}")
        return False


async def test_existing_tables():
    """Verify existing Supabase tables (products, orders)."""
    print_header("EXISTING SUPABASE TABLES")

    all_passed = True

    # Test products table
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM products"))
            count = result.scalar()
            print_test("Products table", True, f"Found {count} products")
    except Exception as e:
        print_test("Products table", False, f"Error: {str(e)}")
        all_passed = False

    # Test orders table
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM orders"))
            count = result.scalar()
            print_test("Orders table", True, f"Found {count} orders")
    except Exception as e:
        print_test("Orders table", False, f"Error: {str(e)}")
        all_passed = False

    return all_passed


async def test_new_tables():
    """Test creation and access to new microservice tables."""
    print_header("NEW MICROSERVICE TABLES")

    all_passed = True

    # Initialize tables
    try:
        await init_db()
        print_test("Table initialization", True, "Created/verified all tables")
    except Exception as e:
        print_test("Table initialization", False, f"Error: {str(e)}")
        return False

    # Check each new table
    new_tables = ['conversations', 'customers', 'response_cache', 'analytics_events']

    async with engine.connect() as conn:
        inspector = inspect(engine.sync_engine)

        for table_name in new_tables:
            try:
                # Check if table exists
                if table_name in inspector.get_table_names():
                    result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    print_test(f"{table_name} table", True, f"Exists with {count} records")
                else:
                    print_test(f"{table_name} table", False, "Table not found")
                    all_passed = False
            except Exception as e:
                print_test(f"{table_name} table", False, f"Error: {str(e)}")
                all_passed = False

    return all_passed


async def test_table_schemas():
    """Verify table schemas and indexes."""
    print_header("TABLE SCHEMA VERIFICATION")

    all_passed = True

    try:
        async with engine.connect() as conn:
            # Check conversations indexes
            result = await conn.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'conversations'
            """))
            indexes = [row[0] for row in result]

            expected_indexes = ['idx_conversations_customer_created']
            has_indexes = any(idx in str(indexes) for idx in expected_indexes)

            if has_indexes:
                print_test("Conversations indexes", True, f"Found indexes: {len(indexes)}")
            else:
                print_test("Conversations indexes", False, "Missing expected indexes")
                all_passed = False

            # Check analytics_events indexes
            result = await conn.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'analytics_events'
            """))
            indexes = [row[0] for row in result]

            expected_indexes = ['idx_analytics_type_created']
            has_indexes = any(idx in str(indexes) for idx in expected_indexes)

            if has_indexes:
                print_test("Analytics indexes", True, f"Found indexes: {len(indexes)}")
            else:
                print_test("Analytics indexes", False, "Missing expected indexes")
                all_passed = False

    except Exception as e:
        print_test("Schema verification", False, f"Error: {str(e)}")
        all_passed = False

    return all_passed


async def test_crud_operations():
    """Test basic CRUD operations on new tables."""
    print_header("DATABASE CRUD OPERATIONS")

    all_passed = True

    # Test Conversation insert
    try:
        async with async_session() as session:
            conv = Conversation(
                customer_id="test:test_user",
                channel="instagram",
                message="Test message",
                direction="incoming",
                intent="product_inquiry"
            )
            session.add(conv)
            await session.commit()

            # Verify insert
            result = await session.execute(
                text("SELECT COUNT(*) FROM conversations WHERE customer_id = 'test:test_user'")
            )
            count = result.scalar()

            if count > 0:
                print_test("Conversation INSERT", True, f"Created and verified record")

                # Test UPDATE
                await session.execute(
                    text("UPDATE conversations SET intent = 'test_updated' WHERE customer_id = 'test:test_user'")
                )
                await session.commit()
                print_test("Conversation UPDATE", True)

                # Test DELETE (cleanup)
                await session.execute(
                    text("DELETE FROM conversations WHERE customer_id = 'test:test_user'")
                )
                await session.commit()
                print_test("Conversation DELETE", True, "Cleaned up test data")
            else:
                print_test("Conversation INSERT", False, "Record not found after insert")
                all_passed = False

    except Exception as e:
        print_test("CRUD operations", False, f"Error: {str(e)}")
        all_passed = False

    return all_passed


async def test_api_health(base_url="http://localhost:8000"):
    """Test API health endpoint."""
    print_header("API ENDPOINT TESTS")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")

            if response.status_code == 200:
                data = response.json()
                print_test("Health endpoint", True, f"Status: {data.get('status')}")
                print(f"  └─ Version: {data.get('version')}")
                print(f"  └─ Database: {data.get('database')}")
                return True
            else:
                print_test("Health endpoint", False, f"Status code: {response.status_code}")
                return False

    except httpx.ConnectError:
        print_test("Health endpoint", False, "API not running - start with: uvicorn main:app")
        return False
    except Exception as e:
        print_test("Health endpoint", False, f"Error: {str(e)}")
        return False


async def test_api_endpoints_with_auth(base_url="http://localhost:8000"):
    """Test protected API endpoints with authentication."""

    headers = {"X-API-Key": settings.api_key}

    all_passed = True

    try:
        async with httpx.AsyncClient() as client:
            # Test product search
            try:
                response = await client.post(
                    f"{base_url}/products/search",
                    json={"query": "shirt", "limit": 3},
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print_test("Product search endpoint", True, f"Found {len(data.get('products', []))} products")
                else:
                    print_test("Product search endpoint", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                print_test("Product search endpoint", False, f"Error: {str(e)}")
                all_passed = False

            # Test context storage
            try:
                response = await client.post(
                    f"{base_url}/context/store",
                    json={
                        "customer_id": "instagram:@test_user",
                        "channel": "instagram",
                        "message": "Hello, I want to buy a shirt",
                        "direction": "incoming"
                    },
                    headers=headers
                )
                if response.status_code == 200:
                    print_test("Context store endpoint", True)
                else:
                    print_test("Context store endpoint", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                print_test("Context store endpoint", False, f"Error: {str(e)}")
                all_passed = False

            # Test intent classification
            try:
                response = await client.post(
                    f"{base_url}/intent/classify",
                    json={
                        "message": "How much does this cost?"
                    },
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    print_test("Intent classification endpoint", True, f"Intent: {data.get('intent')}")
                else:
                    print_test("Intent classification endpoint", False, f"Status: {response.status_code}")
                    all_passed = False
            except Exception as e:
                print_test("Intent classification endpoint", False, f"Error: {str(e)}")
                all_passed = False

    except Exception as e:
        print_test("API endpoint tests", False, f"Error: {str(e)}")
        all_passed = False

    return all_passed


async def test_performance():
    """Test database query performance."""
    print_header("PERFORMANCE TESTS")

    all_passed = True

    try:
        # Test query speed
        async with async_session() as session:
            start = datetime.now()
            await session.execute(text("SELECT COUNT(*) FROM products"))
            duration = (datetime.now() - start).total_seconds() * 1000

            if duration < 100:  # Should be under 100ms
                print_test("Query performance", True, f"{duration:.2f}ms")
            else:
                print_test("Query performance", False, f"{duration:.2f}ms (expected <100ms)")
                all_passed = False

    except Exception as e:
        print_test("Performance tests", False, f"Error: {str(e)}")
        all_passed = False

    return all_passed


async def run_all_tests(test_api=False, base_url="http://localhost:8000"):
    """Run all tests."""
    print(f"\n{YELLOW}{'*'*60}")
    print(f"  E-COMMERCE DM MICROSERVICE - PRE-DEPLOYMENT TESTS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'*'*60}{RESET}\n")

    results = {}

    # Database tests (always run)
    results['connection'] = await test_database_connection()
    results['existing_tables'] = await test_existing_tables()
    results['new_tables'] = await test_new_tables()
    results['schemas'] = await test_table_schemas()
    results['crud'] = await test_crud_operations()
    results['performance'] = await test_performance()

    # API tests (optional - only if server is running)
    if test_api:
        results['api_health'] = await test_api_health(base_url)
        results['api_endpoints'] = await test_api_endpoints_with_auth(base_url)

    # Summary
    print_header("TEST SUMMARY")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"\nTotal Tests: {total}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    if failed > 0:
        print(f"{RED}Failed: {failed}{RESET}")

    print(f"\n{BLUE}{'='*60}{RESET}\n")

    if failed == 0:
        print(f"{GREEN}[OK] All tests passed! Ready for deployment.{RESET}\n")
        return 0
    else:
        print(f"{RED}[FAIL] Some tests failed. Please fix issues before deployment.{RESET}\n")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Test E-commerce DM Microservice')
    parser.add_argument('--api', action='store_true', help='Include API endpoint tests (requires running server)')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for API tests')

    args = parser.parse_args()

    exit_code = asyncio.run(run_all_tests(test_api=args.api, base_url=args.url))
    sys.exit(exit_code)
