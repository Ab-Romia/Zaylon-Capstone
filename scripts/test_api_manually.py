"""
Interactive API Testing Script
Test your API endpoints manually with pre-configured requests.
"""
import asyncio
import httpx
import json
from config import get_settings

settings = get_settings()

BASE_URL = "http://localhost:8000"
API_KEY = settings.api_key

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
RESET = '\033[0m'


def print_section(title):
    print(f"\n{BLUE}{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}{RESET}\n")


def print_request(method, endpoint, data=None):
    print(f"{YELLOW}→ {method} {endpoint}{RESET}")
    if data:
        print(f"  Payload: {json.dumps(data, indent=2, ensure_ascii=False)}")


def print_response(response):
    status_color = GREEN if response.status_code < 400 else RED
    print(f"{status_color}← {response.status_code} {response.reason_phrase}{RESET}")

    try:
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"  Response: {response.text}")


async def test_health():
    """Test health check endpoint."""
    print_section("1. HEALTH CHECK")

    async with httpx.AsyncClient() as client:
        print_request("GET", "/health")
        response = await client.get(f"{BASE_URL}/health")
        print_response(response)


async def test_product_search():
    """Test product search endpoint."""
    print_section("2. PRODUCT SEARCH")

    test_queries = [
        {"query": "shirt", "limit": 3},
        {"query": "قميص", "limit": 3},  # Arabic
        {"query": "فستان", "limit": 2},  # Arabic for dress
        {"query": "shoes", "limit": 5},
    ]

    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as client:
        for payload in test_queries:
            print_request("POST", "/products/search", payload)
            response = await client.post(
                f"{BASE_URL}/products/search",
                json=payload,
                headers=headers
            )
            print_response(response)
            print()


async def test_context_flow():
    """Test conversation context storage and retrieval."""
    print_section("3. CONTEXT STORAGE & RETRIEVAL")

    headers = {"X-API-Key": API_KEY}
    customer_id = "instagram:@test_customer_123"

    async with httpx.AsyncClient() as client:
        # Store multiple messages
        messages = [
            {"customer_id": customer_id, "channel": "instagram", "message": "مرحبا، أريد شراء قميص", "direction": "incoming"},
            {"customer_id": customer_id, "channel": "instagram", "message": "Hello! I can help you find shirts. What size are you looking for?", "direction": "outgoing"},
            {"customer_id": customer_id, "channel": "instagram", "message": "Size M, blue color", "direction": "incoming"},
        ]

        for msg in messages:
            print_request("POST", "/context/store", msg)
            response = await client.post(
                f"{BASE_URL}/context/store",
                json=msg,
                headers=headers
            )
            print_response(response)
            print()

        # Retrieve context
        print_request("GET", f"/context/retrieve?customer_id={customer_id}")
        response = await client.get(
            f"{BASE_URL}/context/retrieve",
            params={"customer_id": customer_id, "limit": 10},
            headers=headers
        )
        print_response(response)


async def test_intent_classification():
    """Test intent classification."""
    print_section("4. INTENT CLASSIFICATION")

    headers = {"X-API-Key": API_KEY}

    test_messages = [
        {"message": "How much does this cost?"},
        {"message": "I want to buy a blue shirt in size M"},
        {"message": "كم السعر؟"},  # Arabic: What's the price?
        {"message": "عايز أطلب فستان"},  # Franco-Arabic: I want to order a dress
        {"message": "What's your return policy?"},
        {"message": "Track my order"},
    ]

    async with httpx.AsyncClient() as client:
        for payload in test_messages:
            print_request("POST", "/intent/classify", payload)
            response = await client.post(
                f"{BASE_URL}/intent/classify",
                json=payload,
                headers=headers
            )
            print_response(response)
            print()


async def test_cache():
    """Test response caching."""
    print_section("5. RESPONSE CACHE")

    headers = {"X-API-Key": API_KEY}

    async with httpx.AsyncClient() as client:
        # Check cache (likely miss first time)
        payload = {"message": "What are your shipping options?"}
        print_request("POST", "/cache/check", payload)
        response = await client.post(
            f"{BASE_URL}/cache/check",
            json=payload,
            headers=headers
        )
        print_response(response)
        print()

        # Store in cache
        cache_payload = {
            "message": "What are your shipping options?",
            "response": "We offer free shipping on orders over $50. Standard delivery takes 3-5 business days.",
            "intent": "shipping_inquiry",
            "ttl_hours": 24
        }
        print_request("POST", "/cache/store", cache_payload)
        response = await client.post(
            f"{BASE_URL}/cache/store",
            json=cache_payload,
            headers=headers
        )
        print_response(response)
        print()

        # Check cache again (should be a hit now)
        print_request("POST", "/cache/check", payload)
        response = await client.post(
            f"{BASE_URL}/cache/check",
            json=payload,
            headers=headers
        )
        print_response(response)


async def test_n8n_prepare():
    """Test n8n integration endpoint."""
    print_section("6. N8N INTEGRATION - PREPARE CONTEXT")

    headers = {"X-API-Key": API_KEY}

    payload = {
        "customer_id": "instagram:@n8n_test_user",
        "message": "Show me blue shirts in size M",
        "channel": "instagram"
    }

    async with httpx.AsyncClient() as client:
        print_request("POST", "/n8n/prepare-context", payload)
        response = await client.post(
            f"{BASE_URL}/n8n/prepare-context",
            json=payload,
            headers=headers
        )
        print_response(response)


async def test_n8n_store():
    """Test n8n store interaction endpoint."""
    print_section("7. N8N INTEGRATION - STORE INTERACTION")

    headers = {"X-API-Key": API_KEY}

    payload = {
        "customer_id": "instagram:@n8n_test_user",
        "channel": "instagram",
        "user_message": "I want to order the blue shirt in size M",
        "ai_response": "Great choice! The blue cotton shirt in size M is 299.99 EGP. Please provide your delivery address.",
        "intent": "order_placement",
        "action": "request_delivery_info",
        "response_time_ms": 245,
        "ai_tokens_used": 156
    }

    async with httpx.AsyncClient() as client:
        print_request("POST", "/n8n/store-interaction", payload)
        response = await client.post(
            f"{BASE_URL}/n8n/store-interaction",
            json=payload,
            headers=headers
        )
        print_response(response)


async def test_analytics():
    """Test analytics endpoints."""
    print_section("8. ANALYTICS")

    headers = {"X-API-Key": API_KEY}

    # Log some events
    events = [
        {
            "customer_id": "instagram:@user1",
            "event_type": "message_received",
            "event_data": {"channel": "instagram", "message_length": 45},
            "response_time_ms": 123
        },
        {
            "customer_id": "instagram:@user2",
            "event_type": "order_created",
            "event_data": {"product": "Blue Shirt", "value": 299.99},
            "response_time_ms": 567,
            "ai_tokens_used": 234
        }
    ]

    async with httpx.AsyncClient() as client:
        for event in events:
            print_request("POST", "/analytics/log", event)
            response = await client.post(
                f"{BASE_URL}/analytics/log",
                json=event,
                headers=headers
            )
            print_response(response)
            print()

        # Get dashboard
        print_request("GET", "/analytics/dashboard?days=7")
        response = await client.get(
            f"{BASE_URL}/analytics/dashboard",
            params={"days": 7},
            headers=headers
        )
        print_response(response)


async def test_auth_and_rate_limit():
    """Test authentication and rate limiting."""
    print_section("9. AUTHENTICATION & RATE LIMITING")

    async with httpx.AsyncClient() as client:
        # Test without API key
        print_request("GET", "/health (no auth)")
        response = await client.get(f"{BASE_URL}/health")
        print_response(response)
        print()

        # Test with wrong API key
        print_request("GET", "/health (wrong key)")
        response = await client.get(
            f"{BASE_URL}/health",
            headers={"X-API-Key": "wrong-key"}
        )
        print_response(response)
        print()

        # Test with correct API key
        print_request("GET", "/health (correct key)")
        response = await client.get(
            f"{BASE_URL}/health",
            headers={"X-API-Key": API_KEY}
        )
        print_response(response)


async def run_all_tests():
    """Run all API tests."""
    print(f"\n{YELLOW}{'*'*60}")
    print(f"  API MANUAL TESTING SUITE")
    print(f"  Base URL: {BASE_URL}")
    print(f"  API Key: {API_KEY[:10]}...")
    print(f"{'*'*60}{RESET}\n")

    try:
        await test_health()
        await test_product_search()
        await test_context_flow()
        await test_intent_classification()
        await test_cache()
        await test_n8n_prepare()
        await test_n8n_store()
        await test_analytics()
        await test_auth_and_rate_limit()

        print_section("✓ ALL TESTS COMPLETED")

    except httpx.ConnectError:
        print(f"\n{RED}✗ Error: Cannot connect to API server{RESET}")
        print(f"Make sure the server is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n{RED}✗ Error: {str(e)}{RESET}")


def interactive_menu():
    """Show interactive menu for testing."""
    print(f"\n{BLUE}{'='*60}")
    print("  INTERACTIVE API TESTING")
    print(f"{'='*60}{RESET}\n")

    print("Select a test to run:")
    print("  1. Health Check")
    print("  2. Product Search")
    print("  3. Context Storage & Retrieval")
    print("  4. Intent Classification")
    print("  5. Response Cache")
    print("  6. n8n Prepare Context")
    print("  7. n8n Store Interaction")
    print("  8. Analytics")
    print("  9. Auth & Rate Limiting")
    print("  0. Run All Tests")
    print("  q. Quit")

    choice = input("\nEnter your choice: ").strip()

    test_map = {
        '1': test_health,
        '2': test_product_search,
        '3': test_context_flow,
        '4': test_intent_classification,
        '5': test_cache,
        '6': test_n8n_prepare,
        '7': test_n8n_store,
        '8': test_analytics,
        '9': test_auth_and_rate_limit,
        '0': run_all_tests,
    }

    if choice in test_map:
        asyncio.run(test_map[choice]())
        input("\nPress Enter to continue...")
        interactive_menu()
    elif choice.lower() == 'q':
        print("Goodbye!")
    else:
        print("Invalid choice!")
        interactive_menu()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        asyncio.run(run_all_tests())
    else:
        interactive_menu()
