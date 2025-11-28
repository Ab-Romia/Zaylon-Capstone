"""
Test script for the Flowinit v2 Agent API.
Tests the /api/v2/agent/invoke endpoint.
"""

import asyncio
import json
from datetime import datetime

# We'll use httpx for async HTTP requests
try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.run(["pip", "install", "httpx"], check=True)
    import httpx


# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "test-api-key-123"  # Replace with actual API key from env


async def test_agent_invoke():
    """Test the /api/v2/agent/invoke endpoint."""
    print("=" * 80)
    print("TEST: Agent Invoke Endpoint")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Sales flow
        print("\n[Test 1] Sales Flow - Product Inquiry")
        print("-" * 80)

        request_data = {
            "customer_id": "instagram:@testuser",
            "message": "I want to buy a red hoodie in size L",
            "channel": "instagram"
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v2/agent/invoke",
                json=request_data,
                headers={"X-API-Key": API_KEY}
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success: {data['success']}")
                print(f"✓ Agent Used: {data['agent_used']}")
                print(f"✓ Execution Time: {data['execution_time_ms']}ms")
                print(f"✓ Response Preview: {data['response'][:200]}...")
                print(f"✓ Chain of Thought Steps: {len(data['chain_of_thought'])}")
                print(f"✓ Tool Calls: {len(data['tool_calls'])}")

                # Print chain of thought
                if data['chain_of_thought']:
                    print("\nChain of Thought:")
                    for i, thought in enumerate(data['chain_of_thought'], 1):
                        print(f"  {i}. [{thought['node']}] {thought['reasoning'][:100]}...")

                # Print tool calls
                if data['tool_calls']:
                    print("\nTool Calls:")
                    for i, tool in enumerate(data['tool_calls'], 1):
                        print(f"  {i}. {tool['tool_name']} - Success: {tool['success']}")

            else:
                print(f"✗ Error: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"✗ Exception: {e}")

        # Test 2: Support flow
        print("\n\n[Test 2] Support Flow - Order Status Inquiry")
        print("-" * 80)

        request_data = {
            "customer_id": "instagram:@testuser",
            "message": "Where is my order? I ordered last week",
            "channel": "instagram"
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v2/agent/invoke",
                json=request_data,
                headers={"X-API-Key": API_KEY}
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success: {data['success']}")
                print(f"✓ Agent Used: {data['agent_used']}")
                print(f"✓ Execution Time: {data['execution_time_ms']}ms")
                print(f"✓ Response Preview: {data['response'][:200]}...")

            else:
                print(f"✗ Error: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"✗ Exception: {e}")

        # Test 3: Memory persistence
        print("\n\n[Test 3] Memory Persistence - Follow-up Message")
        print("-" * 80)

        # First message: State a preference
        request_data_1 = {
            "customer_id": "instagram:@memorytest",
            "message": "I love red colors and I only wear size M",
            "channel": "instagram"
        }

        print("First message: Stating preferences...")
        response_1 = await client.post(
            f"{BASE_URL}/api/v2/agent/invoke",
            json=request_data_1,
            headers={"X-API-Key": API_KEY}
        )

        if response_1.status_code == 200:
            data_1 = response_1.json()
            print(f"✓ First response: {data_1['response'][:150]}...")
            print(f"✓ Memory saved: {len(data_1.get('user_profile', {}))} facts")

        # Wait a moment
        await asyncio.sleep(2)

        # Second message: Ask for recommendation (should use memory)
        request_data_2 = {
            "customer_id": "instagram:@memorytest",
            "message": "Show me some hoodies",
            "channel": "instagram"
        }

        print("\nSecond message: Asking for recommendations...")
        response_2 = await client.post(
            f"{BASE_URL}/api/v2/agent/invoke",
            json=request_data_2,
            headers={"X-API-Key": API_KEY}
        )

        if response_2.status_code == 200:
            data_2 = response_2.json()
            print(f"✓ Second response: {data_2['response'][:150]}...")
            print(f"✓ Memory loaded: {len(data_2.get('user_profile', {}))} facts")

            # Check if memory was used
            response_text = data_2['response'].lower()
            if 'red' in response_text or 'medium' in response_text or 'm' in response_text:
                print("✓ Memory appears to be working (response mentions preferences)")
            else:
                print("⚠ Memory may not be fully integrated")

        print("\n" + "=" * 80)
        print("Testing Complete")
        print("=" * 80)


async def test_streaming():
    """Test the streaming endpoint (if server supports it)."""
    print("\n\n" + "=" * 80)
    print("TEST: Agent Streaming Endpoint")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        request_data = {
            "customer_id": "instagram:@streamtest",
            "message": "Tell me about your hoodies",
            "channel": "instagram"
        }

        try:
            print("Opening stream connection...")
            async with client.stream(
                "POST",
                f"{BASE_URL}/api/v2/agent/stream",
                json=request_data,
                headers={"X-API-Key": API_KEY}
            ) as response:
                print(f"Status Code: {response.status_code}")

                if response.status_code == 200:
                    print("\nStreaming events:")
                    print("-" * 80)

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            try:
                                chunk = json.loads(data_str)
                                chunk_type = chunk.get("type")
                                content = chunk.get("content", "")

                                if chunk_type == "thought":
                                    print(f"💭 Thought: {content[:100]}...")
                                elif chunk_type == "tool_call":
                                    print(f"🔧 Tool: {chunk.get('tool_name')}")
                                elif chunk_type == "response":
                                    print(f"💬 Response: {content[:100]}...")
                                elif chunk_type == "final":
                                    print(f"✓ {content}")
                                    break
                                elif chunk_type == "error":
                                    print(f"✗ Error: {content}")
                                    break

                            except json.JSONDecodeError:
                                print(f"⚠ Could not parse: {data_str}")

                else:
                    print(f"✗ Error: {response.status_code}")

        except Exception as e:
            print(f"✗ Exception during streaming: {e}")


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("FLOWINIT V2 AGENT API TESTS")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    try:
        # Test basic invoke endpoint
        await test_agent_invoke()

        # Test streaming endpoint
        await test_streaming()

    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    print("\nStarting Flowinit v2 API tests...")
    print("Make sure the server is running on http://localhost:8000")
    print("Press Ctrl+C to cancel\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✗ Tests cancelled by user")
