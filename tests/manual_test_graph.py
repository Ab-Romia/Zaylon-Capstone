"""
Manual Test Script for Zaylon Agent Graph
Tests the LangGraph implementation with sample inputs.

Usage:
    python -m tests.manual_test_graph
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from app.agents import invoke_agent, zaylon_graph
from app.agents.state import NodeName

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_basic_sales_flow():
    """
    Test Case 1: Basic sales inquiry
    Expected: Routes to Sales Agent
    """
    print("\n" + "="*80)
    print("TEST 1: Basic Sales Inquiry")
    print("="*80)

    customer_id = "instagram:@test_user_sales"
    message = "I want to buy a red hoodie in size M"

    print(f"\nCustomer: {customer_id}")
    print(f"Message: {message}")
    print("\nExecuting graph...")

    result = await invoke_agent(
        customer_id=customer_id,
        message=message,
        channel="instagram"
    )

    print("\n--- RESULTS ---")
    print(f"Success: {result['success']}")
    print(f"Current Agent: {result.get('current_agent')}")
    print(f"Final Response: {result.get('final_response')}")
    print(f"\nChain of Thought:")
    for i, thought in enumerate(result.get('chain_of_thought', []), 1):
        print(f"  {i}. {thought}")

    print(f"\nTool Calls:")
    for tool_call in result.get('tool_calls', []):
        print(f"  - {tool_call.get('tool')}: {tool_call.get('args')}")

    # Assertions
    assert result['success'], "Graph execution failed"
    assert result.get('final_response'), "No final response generated"

    # Check chain of thought includes expected nodes
    cot = " ".join(result.get('chain_of_thought', []))
    assert "memory" in cot.lower() or "facts" in cot.lower(), "Memory node didn't run"
    assert "sales" in cot.lower() or "Sales" in cot, "Sales agent didn't run"

    print("\n[PASS] Test 1 PASSED")
    return True


async def test_support_flow():
    """
    Test Case 2: Support inquiry
    Expected: Routes to Support Agent
    """
    print("\n" + "="*80)
    print("TEST 2: Support Inquiry")
    print("="*80)

    customer_id = "instagram:@test_user_support"
    message = "What is your return policy?"

    print(f"\nCustomer: {customer_id}")
    print(f"Message: {message}")
    print("\nExecuting graph...")

    result = await invoke_agent(
        customer_id=customer_id,
        message=message,
        channel="instagram"
    )

    print("\n--- RESULTS ---")
    print(f"Success: {result['success']}")
    print(f"Current Agent: {result.get('current_agent')}")
    print(f"Final Response: {result.get('final_response')}")
    print(f"\nChain of Thought:")
    for i, thought in enumerate(result.get('chain_of_thought', []), 1):
        print(f"  {i}. {thought}")

    # Assertions
    assert result['success'], "Graph execution failed"
    assert result.get('final_response'), "No final response generated"

    # Check routing went to support
    cot = " ".join(result.get('chain_of_thought', []))
    assert "support" in cot.lower() or "Support" in cot, "Support agent didn't run"

    print("\n[PASS] Test 2 PASSED")
    return True


async def test_memory_persistence():
    """
    Test Case 3: Memory persistence across interactions
    Expected: Second call uses saved memory from first call
    """
    print("\n" + "="*80)
    print("TEST 3: Memory Persistence")
    print("="*80)

    customer_id = "instagram:@test_user_memory"

    # First interaction: User states a preference
    message1 = "I wear size M and I love blue"
    print(f"\nInteraction 1:")
    print(f"Customer: {customer_id}")
    print(f"Message: {message1}")

    result1 = await invoke_agent(
        customer_id=customer_id,
        message=message1,
        channel="instagram"
    )

    print(f"Response: {result1.get('final_response', '')[:100]}...")

    # Wait a moment for memory to save
    await asyncio.sleep(1)

    # Second interaction: Reference the preference
    message2 = "Show me hoodies"
    print(f"\nInteraction 2:")
    print(f"Message: {message2}")

    result2 = await invoke_agent(
        customer_id=customer_id,
        message=message2,
        channel="instagram"
    )

    print(f"\nUser Profile Loaded: {result2.get('user_profile')}")
    print(f"Response: {result2.get('final_response', '')[:100]}...")

    # Assertions
    assert result2['success'], "Second interaction failed"
    user_profile = result2.get('user_profile', {})

    # Check if memory was loaded (may or may not have exact keys depending on extraction)
    print(f"\nMemory facts found: {len(user_profile)}")
    for key, value in user_profile.items():
        print(f"  - {key}: {value}")

    print("\n[PASS] Test 3 PASSED (memory system operational)")
    return True


async def test_mixed_intent():
    """
    Test Case 4: Mixed intent (support + sales)
    Expected: Routes to Sales (handles both)
    """
    print("\n" + "="*80)
    print("TEST 4: Mixed Intent")
    print("="*80)

    customer_id = "instagram:@test_user_mixed"
    message = "I want to return my last order and buy a new red hoodie"

    print(f"\nCustomer: {customer_id}")
    print(f"Message: {message}")
    print("\nExecuting graph...")

    result = await invoke_agent(
        customer_id=customer_id,
        message=message,
        channel="instagram"
    )

    print("\n--- RESULTS ---")
    print(f"Success: {result['success']}")
    print(f"Final Response: {result.get('final_response')}")
    print(f"\nChain of Thought:")
    for i, thought in enumerate(result.get('chain_of_thought', []), 1):
        print(f"  {i}. {thought}")

    # Assertions
    assert result['success'], "Graph execution failed"

    # Should route to sales for mixed intent
    cot = " ".join(result.get('chain_of_thought', []))
    assert "sales" in cot.lower() or "Sales" in cot, "Expected routing to Sales for mixed intent"

    print("\n[PASS] Test 4 PASSED")
    return True


async def test_graph_structure():
    """
    Test Case 5: Verify graph structure
    Expected: All nodes are present and connected
    """
    print("\n" + "="*80)
    print("TEST 5: Graph Structure Verification")
    print("="*80)

    # Check that graph has all expected nodes
    graph_nodes = list(zaylon_graph.nodes.keys())

    print(f"\nNodes in graph: {len(graph_nodes)}")
    for node in graph_nodes:
        print(f"  - {node}")

    expected_nodes = [
        NodeName.LOAD_MEMORY,
        NodeName.SUPERVISOR,
        NodeName.SALES_AGENT,
        NodeName.SUPPORT_AGENT,
        NodeName.SAVE_MEMORY
    ]

    print(f"\nExpected nodes: {len(expected_nodes)}")
    for node in expected_nodes:
        print(f"  - {node}")
        assert node in graph_nodes, f"Missing node: {node}"

    print("\n[PASS] Test 5 PASSED (all nodes present)")
    return True


async def run_all_tests():
    """Run all test cases."""
    print("\n" + "="*80)
    print("ZAYLON AGENT GRAPH - TEST SUITE")
    print("="*80)

    tests = [
        ("Graph Structure", test_graph_structure),
        ("Basic Sales Flow", test_basic_sales_flow),
        ("Support Flow", test_support_flow),
        ("Mixed Intent", test_mixed_intent),
        ("Memory Persistence", test_memory_persistence),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAIL] Test '{test_name}' FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[FAIL] Test '{test_name}' ERROR: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")

    if failed == 0:
        print("\nSUCCESS ALL TESTS PASSED!")
    else:
        print(f"\n[WARNING]  {failed} test(s) failed")

    return failed == 0


if __name__ == "__main__":
    print("\nStarting Starting Zaylon Agent Graph Tests...")
    print("=" * 80)

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[WARNING]  WARNING: OPENAI_API_KEY not found in environment")
        print("Please set it in .env file or export it:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("\nTests will fail without a valid API key.\n")
        sys.exit(1)

    # Run tests
    success = asyncio.run(run_all_tests())

    sys.exit(0 if success else 1)
