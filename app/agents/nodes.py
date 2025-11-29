"""
LangGraph Agent Nodes
Implements the individual nodes (functions) that make up the Flowinit agent graph.
"""

import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.agents.state import FlowinitState, AgentType, update_state
from app.tools import (
    SALES_TOOLS, SUPPORT_TOOLS, MEMORY_TOOLS,
    get_customer_facts_tool, save_customer_fact_tool
)
from config import get_settings
from services.llm_factory import get_chat_llm, get_provider_name

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize LLM for agents using provider factory (supports OpenAI and Gemini)
# The provider is configured in .env via LLM_PROVIDER
try:
    llm_base = get_chat_llm(use_mini=False)  # Main agent model (gpt-4o or gemini-1.5-pro)
    supervisor_llm = get_chat_llm(use_mini=True)  # Routing model (gpt-4o-mini or gemini-1.5-flash)
    logger.info(f"Initialized LLM provider: {get_provider_name()}")
except Exception as e:
    logger.error(f"Failed to initialize LLM provider: {e}")
    raise


def get_tool_calls(response):
    """
    Robust extraction of tool calls from AIMessage.
    Handles different LangChain versions and response formats.

    Returns:
        List of tool calls, or empty list if none found
    """
    # Debug: log response structure
    logger.debug(f"[TOOL_CALL_DETECTION] Response type: {type(response)}")
    logger.debug(f"[TOOL_CALL_DETECTION] Response dir: {[a for a in dir(response) if not a.startswith('_')]}")

    # Try direct attribute access (newer LangChain)
    if hasattr(response, 'tool_calls'):
        logger.debug(f"[TOOL_CALL_DETECTION] Has tool_calls attr, value: {response.tool_calls}")
        if response.tool_calls:
            return response.tool_calls

    # Try additional_kwargs (some versions store it here)
    if hasattr(response, 'additional_kwargs'):
        logger.debug(f"[TOOL_CALL_DETECTION] additional_kwargs: {response.additional_kwargs}")
        tool_calls = response.additional_kwargs.get('tool_calls', [])
        if tool_calls:
            logger.debug(f"[TOOL_CALL_DETECTION] Found tool_calls in additional_kwargs: {tool_calls}")
            return tool_calls

        # Try function_call (older OpenAI format)
        function_call = response.additional_kwargs.get('function_call')
        if function_call:
            logger.debug(f"[TOOL_CALL_DETECTION] Found function_call in additional_kwargs: {function_call}")
            # Convert old format to new format
            return [{
                'name': function_call.get('name'),
                'args': json.loads(function_call.get('arguments', '{}')),
                'id': 'legacy_call'
            }]

    logger.debug("[TOOL_CALL_DETECTION] No tool calls found")
    return []


# ============================================================================
# Memory Nodes
# ============================================================================

async def load_memory_node(state: FlowinitState) -> Dict[str, Any]:
    """
    Load customer long-term memory from Memory Bank.

    This node:
    1. Retrieves customer facts using get_customer_facts_tool
    2. Populates user_profile in state
    3. Logs the memory load for observability
    """
    logger.info(f"[LOAD_MEMORY] Loading memory for customer: {state['customer_id']}")

    customer_id = state["customer_id"]

    try:
        # Call memory tool to retrieve facts
        facts_json = await get_customer_facts_tool.ainvoke({"customer_id": customer_id})
        facts_data = json.loads(facts_json)

        # Build user profile dictionary
        user_profile = {}
        if facts_data.get("success") and facts_data.get("found"):
            for fact in facts_data.get("facts", []):
                user_profile[fact["fact_key"]] = {
                    "value": fact["fact_value"],
                    "confidence": fact["confidence"],
                    "source": fact["source"]
                }

            logger.info(f"[LOAD_MEMORY] Loaded {len(user_profile)} facts")
        else:
            logger.info("[LOAD_MEMORY] No previous facts found for customer")

        # Add to chain of thought
        thought = f"Loaded customer memory: {len(user_profile)} facts retrieved"

        return {
            "user_profile": user_profile,
            "chain_of_thought": [thought]
            # Don't set current_agent - preserve value from previous nodes
        }

    except Exception as e:
        logger.error(f"[LOAD_MEMORY] Error loading memory: {e}")
        return {
            "user_profile": {},
            "chain_of_thought": [f"Memory load failed: {str(e)}"]
            # Don't set current_agent - preserve value from previous nodes
        }


async def save_memory_node(state: FlowinitState) -> Dict[str, Any]:
    """
    Extract and save new facts from conversation to Memory Bank.

    This node:
    1. Analyzes the last conversation turn
    2. Extracts any new facts (preferences, constraints, personal info)
    3. Saves them using save_customer_fact_tool
    4. Logs extractions for observability
    """
    logger.info(f"[SAVE_MEMORY] Extracting facts for customer: {state['customer_id']}")

    customer_id = state["customer_id"]
    messages = state["messages"]

    # Get the last user message
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        logger.info("[SAVE_MEMORY] No user message to extract facts from")
        return {
            "chain_of_thought": ["No facts extracted - no user message found"],
            "current_agent": "memory"
        }

    try:
        # Use LLM to extract facts
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a fact extraction system. Analyze the user's message and extract any facts about them.

Extract facts in these categories:
1. **preference**: Things they like/prefer (size, color, style, etc.)
2. **constraint**: Limitations or requirements (budget, location, delivery time)
3. **personal_info**: Personal details (name, address, phone updates)

For each fact, determine:
- fact_type: preference, constraint, or personal_info
- fact_key: Short identifier (e.g., "preferred_size", "budget_max", "delivery_address")
- fact_value: The actual value
- confidence: 100 if explicitly stated, 70-90 if inferred
- source: "explicit" if directly stated, "inferred" if you deduced it

Return JSON array of facts. If no facts, return empty array.

Examples:
- "I wear size M" → {{"fact_type": "preference", "fact_key": "preferred_size", "fact_value": "M", "confidence": 100, "source": "explicit"}}
- "I love blue" → {{"fact_type": "preference", "fact_key": "favorite_color", "fact_value": "blue", "confidence": 100, "source": "explicit"}}
- "I moved to Cairo" → {{"fact_type": "personal_info", "fact_key": "city", "fact_value": "Cairo", "confidence": 100, "source": "explicit"}}

Return ONLY valid JSON array, no other text."""),
            ("human", "{message}")
        ])

        extraction_chain = extraction_prompt | llm_base
        response = await extraction_chain.ainvoke({"message": last_user_message})

        # Parse extracted facts
        try:
            extracted_text = response.content.strip()
            # Remove markdown code blocks if present
            if extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1]
                if extracted_text.startswith("json"):
                    extracted_text = extracted_text[4:]
                extracted_text = extracted_text.strip()

            facts = json.loads(extracted_text)

            if not isinstance(facts, list):
                facts = []

            # Save each fact
            saved_count = 0
            for fact in facts:
                try:
                    result_json = await save_customer_fact_tool.ainvoke({
                        "customer_id": customer_id,
                        "fact_type": fact.get("fact_type", "preference"),
                        "fact_key": fact.get("fact_key"),
                        "fact_value": fact.get("fact_value"),
                        "confidence": fact.get("confidence", 100),
                        "source": fact.get("source", "explicit")
                    })
                    result = json.loads(result_json)
                    if result.get("success"):
                        saved_count += 1
                        logger.info(f"[SAVE_MEMORY] Saved fact: {fact['fact_key']} = {fact['fact_value']}")
                except Exception as e:
                    logger.error(f"[SAVE_MEMORY] Failed to save fact: {e}")

            thought = f"Extracted and saved {saved_count} new facts from conversation"
            logger.info(f"[SAVE_MEMORY] {thought}")

            return {
                "chain_of_thought": [thought]
                # Don't set current_agent - preserve the agent that handled the request
            }

        except json.JSONDecodeError as e:
            logger.error(f"[SAVE_MEMORY] Failed to parse extracted facts: {e}")
            return {
                "chain_of_thought": ["Fact extraction parsing failed"]
                # Don't set current_agent - preserve the agent that handled the request
            }

    except Exception as e:
        logger.error(f"[SAVE_MEMORY] Error extracting facts: {e}")
        return {
            "chain_of_thought": [f"Fact extraction failed: {str(e)}"]
            # Don't set current_agent - preserve the agent that handled the request
        }


# ============================================================================
# Supervisor Node (Router)
# ============================================================================

async def supervisor_node(state: FlowinitState) -> Dict[str, Any]:
    """
    Supervisor agent that routes to Sales or Support.

    This node:
    1. Analyzes the conversation and user profile
    2. Decides which specialist agent should handle the request
    3. Sets the 'next' field to route accordingly
    4. Logs reasoning for observability
    """
    logger.info("[SUPERVISOR] Analyzing request and routing...")

    messages = state["messages"]
    user_profile = state.get("user_profile", {})

    # Build user profile summary for context
    profile_summary = "No previous history."
    if user_profile:
        profile_items = []
        for key, data in user_profile.items():
            profile_items.append(f"- {key}: {data['value']}")
        profile_summary = "User profile:\n" + "\n".join(profile_items)

    # Get last user message
    last_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    if not last_message:
        logger.warning("[SUPERVISOR] No user message found, defaulting to Support")
        return {
            "next": "support",
            "chain_of_thought": ["No message found - defaulting to Support"],
            "current_agent": AgentType.SUPERVISOR
        }

    # Supervisor routing prompt
    routing_prompt = f"""You are a routing supervisor for an e-commerce chatbot. Your job is to analyze the customer's message and decide which specialist should handle it.

**Customer Message**: "{last_message}"

**Customer Profile**:
{profile_summary}

**Available Agents**:
1. **Sales Agent**: Handles product searches, purchases, ordering, product availability, order history
2. **Support Agent**: Handles FAQs, policies, general inquiries, order tracking, complaints, order modifications, cancellations

**CRITICAL ROUTING RULES** (Follow Strictly):

**Route to SUPPORT if asking about** (HIGH PRIORITY - These ALWAYS go to support):
- **Complaints and Issues**: "I received a damaged item", "Wrong product", "Product is broken", "Item doesn't work"
- **Order Tracking**: "Where is my order?", "Order status?", "فين طلبي؟", "Track my order"
- **Order Modifications**: "Can I change my order?", "Cancel my order", "Modify my order"
- **General Policies ONLY** (without product interest): "What's your return policy?", "What payment methods?", "How do I cancel?"
- **Shipping Information ONLY** (without ordering): "Do you ship to Cairo?", "How long is shipping?", "Shipping times?"
- **Account/Help Requests**: "I need help with my purchase", "Help with my order", "Customer support"
- **Anything related to PROBLEMS, ISSUES, or COMPLAINTS**

**Route to SALES if asking about** (Product-focused queries):
- Product searches ("Show me hoodies", "عايز بنطلون", "I want a shirt", "blue shirt")
- Product availability ("Do you have this in stock?", "What sizes?", "What colors?")
- Prices ("How much is?", "Show me cheap products", "price of hoodie")
- Making purchases ("I want to buy", "3ayz a3ml order", "I want to purchase")
- Product recommendations ("Best sellers", "For winter", "comfortable clothes")
- Saving preferences ("I prefer red", "I like size M")
- Viewing order history for reordering purposes ("I want to reorder my last purchase")

**Mixed Intent Handling**:
- If complaint/problem + product interest → Route to **SUPPORT** (Handle problem first)
- If policy question + product interest → Route to **SALES** (Sales can search KB if needed)
- If returns/refunds + new purchase → Route to **SALES** (Sales can handle both)
- If unclear whether problem or product inquiry → Route to **SUPPORT** (Better for ambiguous help requests)

**Decision Logic**:
1. Check for complaints/problems/issues → SUPPORT
2. Check for order tracking/modifications → SUPPORT
3. Check for pure policy questions (no products) → SUPPORT
4. Check for product searches/purchases → SALES
5. If completely unclear → SUPPORT (safer default)

**Your Decision**:
Respond with ONLY one word: "sales" or "support"
"""

    try:
        # Get routing decision from LLM
        response = await supervisor_llm.ainvoke([
            SystemMessage(content="You are a routing supervisor. Respond with only 'sales' or 'support'."),
            HumanMessage(content=routing_prompt)
        ])

        decision = response.content.strip().lower()

        # Validate decision
        if decision not in ["sales", "support"]:
            logger.warning(f"[SUPERVISOR] Invalid decision '{decision}', defaulting to support")
            decision = "support"

        thought = f"Routing decision: {decision.upper()} (reason: {last_message[:50]}...)"
        logger.info(f"[SUPERVISOR] {thought}")

        return {
            "next": decision,
            "chain_of_thought": [thought],
            "current_agent": AgentType.SUPERVISOR
        }

    except Exception as e:
        logger.error(f"[SUPERVISOR] Error during routing: {e}")
        return {
            "next": "support",  # Safe default
            "chain_of_thought": [f"Routing failed: {str(e)} - defaulting to Support"],
            "current_agent": AgentType.SUPERVISOR
        }


# ============================================================================
# Specialist Agent Nodes
# ============================================================================

async def sales_agent_node(state: FlowinitState) -> Dict[str, Any]:
    """
    Sales specialist agent with product and order tools.

    This node:
    1. Acts as a sales representative
    2. Has access to product search, availability, and order creation tools
    3. Uses user profile to personalize responses
    4. Generates final customer-facing response
    """
    logger.info("[SALES AGENT] Handling sales request...")

    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    customer_id = state.get("customer_id", "unknown")

    # Build system message with profile context
    profile_context = ""
    if user_profile:
        profile_items = []
        for key, data in user_profile.items():
            profile_items.append(f"- {key}: {data['value']}")
        profile_context = "\n**Customer Preferences**:\n" + "\n".join(profile_items)

    system_message = f"""You are a sales specialist for an e-commerce clothing store. You MUST use tools to help customers.

**Customer Context**:
- Customer ID: {customer_id}

{profile_context}

**MANDATORY TOOL USAGE RULES**:
You have NO product information in your memory. You MUST call tools for ANY product-related query.

**PERSONALIZATION - PROACTIVE MEMORY USAGE**:
- ALWAYS consider the customer's profile above when making recommendations
- If customer asks "in my size" or "my favorite color" → Their preferences are ALREADY shown in the profile above, use them directly
- If no preferences shown but customer refers to "my size/color" → Ask them to specify
- Use preferences to enhance search queries (e.g., if they prefer red, prioritize red items)
- If customer states a NEW preference ("I prefer red", "I like size M") → call save_customer_fact_tool FIRST

**When customer asks about products/prices/stock → IMMEDIATELY call search_products_tool**
Examples:
- "I want a red hoodie" → call search_products_tool(query="red hoodie")
- "عايز بنطلون اسود" → call search_products_tool(query="بنطلون اسود")
- "3ayez jeans azra2" → call search_products_tool(query="jeans azra2")
- "Show me hoodies" → call search_products_tool(query="hoodies")
- "What's the price of the red hoodie?" → call search_products_tool(query="red hoodie")
- "Do you have that hoodie in my size?" → Check customer profile above for preferred_size, then search with that size

**When customer states preferences → call save_customer_fact_tool**
Examples:
- "I prefer red colors and size M" → call save_customer_fact_tool twice (once for color, once for size)
- "I like large sizes" → call save_customer_fact_tool(fact_key="preferred_size", fact_value="L", ...)

**When customer asks about policies/FAQs in addition to products → call search_knowledge_base_tool**
Examples:
- "Tell me about shipping times, and also I want a black jacket" → call search_knowledge_base_tool(query="shipping times") AND search_products_tool(query="black jacket")
- "What's your return policy and show me blue shirts" → call both tools

**When customer wants to buy/order → STRICT SLOT-FILLING REQUIRED**

**CRITICAL - ORDER CREATION RULES (MUST FOLLOW)**:
Before calling create_order_tool, you MUST verify ALL required information is available:

1. **Product Information**: product_id, product_name, size, color, quantity, total_price
   - Get from search_products_tool results
   - NEVER guess or make up product IDs

2. **Customer Information**: customer_name, phone, address
   - Check the Customer Profile above for saved contact info
   - If ANY of these are missing → ASK the customer for them
   - NEVER use placeholder data like "John Doe", "+201234567890", "123 Main Street"
   - NEVER guess or make up customer information
   - If customer says "my name is X" or "my address is Y" → FIRST call save_customer_fact_tool to save it, THEN proceed with order

3. **Slot-Filling Example**:
   - Customer: "I want to buy 3 Medium blue shirts"
   - You: search_products_tool(query="blue shirts") → get product_id, price
   - Check profile for customer_name, phone, address
   - If missing: "Great! To complete your order, I need your full name, phone number, and delivery address."
   - Wait for customer to provide
   - Customer provides info → save_customer_fact_tool for each piece
   - Then: create_order_tool(...) with REAL data only

4. **After Order Creation - DO NOT call check_order_status_tool immediately**:
   - The create_order_tool response contains ALL order details
   - Use the order_id and details from the creation response to confirm with customer
   - NEVER check status of a just-created order (causes race conditions)

**When customer asks about order status/history → call get_order_history_tool or check_order_status_tool**
Examples:
- "Where is my order?" → call get_order_history_tool(customer_id="{customer_id}")
- "Order status?" → call get_order_history_tool(customer_id="{customer_id}")
- "I want to reorder my last purchase" → call get_order_history_tool(customer_id="{customer_id}") first

**CRITICAL RULES**:
1. NEVER respond without calling a tool first for product/order queries
2. NEVER say "I'm processing your request" - call the tool immediately
3. NEVER make up product information - use tools only
4. **NEVER HALLUCINATE ERRORS**: If a tool returns success: true, TRUST IT and confirm to customer
   - Example: create_order_tool returns {{"success": true, "order_id": "ABC123"}}
   - You MUST say: "Your order ABC123 has been placed successfully!"
   - DO NOT say: "There was an issue" or "I couldn't create the order" when success=true
5. **NEVER USE FAKE/PLACEHOLDER DATA**: ALWAYS ask customer for missing info, NEVER guess
   - FORBIDDEN: "John Doe", "Jane Smith", "+201234567890", "123 Main Street", "Cairo, Egypt" as defaults
   - REQUIRED: Real customer data provided by the actual customer
6. **LANGUAGE MATCHING**: ALWAYS respond in the SAME language as the customer:
   - English input → English response
   - Arabic input (عربي) → Arabic response (عربي)
   - Franco-Arabic input (3ayez, 7aga, etc.) → Franco-Arabic response
   - Detect Franco-Arabic by numbers in text: 3=ع, 7=ح, 2=أ, 5=خ, 8=ق, 9=ص
7. After getting tool results, provide a natural, helpful response in the customer's EXACT language
8. ALWAYS use customer preferences from profile when available
9. **RESPECT TOOL OUTPUTS**: Parse the JSON response from tools carefully and respond based on actual success/failure, not assumptions

**Available Tools**:
- search_products_tool(query, limit=5) - Search products by keyword
- check_product_availability_tool(product_name, size, color) - Check stock
- create_order_tool(customer_id, product_id, quantity, size, color, name, phone, address) - Create order
- get_order_history_tool(customer_id) - Get customer's past orders
- check_order_status_tool(order_id) - Check specific order status
- save_customer_fact_tool(customer_id, fact_type, fact_key, fact_value, confidence, source) - Save customer preferences

Remember: TOOL FIRST, RESPONSE SECOND. Always call tools before responding."""

    try:
        # Create agent with tools - simple binding without forcing
        sales_agent = llm_base.bind_tools(SALES_TOOLS)

        # Build agent messages
        agent_messages = [SystemMessage(content=system_message)] + messages

        logger.info(f"[SALES AGENT] Invoking with {len(agent_messages)} messages")
        logger.info(f"[SALES AGENT] Last message: {messages[-1].content[:100] if messages else 'None'}")

        # First attempt - ask nicely
        response = await sales_agent.ainvoke(agent_messages)

        # Check if tools were called - robust checking using helper function
        tool_calls_list = get_tool_calls(response)
        tools_called = len(tool_calls_list) > 0

        logger.info(f"[SALES AGENT] Response type: {type(response)}")
        logger.info(f"[SALES AGENT] Tool calls found: {len(tool_calls_list)}")
        logger.info(f"[SALES AGENT] Tool calls: {tool_calls_list[:100] if tool_calls_list else 'None'}")
        logger.info(f"[SALES AGENT] Tools called on first attempt: {tools_called}")

        # If NO tools called, force a retry with stronger prompting
        if not tools_called:
            logger.warning("[SALES AGENT] No tools called - forcing retry with stronger prompt")

            # CRITICAL: Do NOT append the first response to avoid OpenAI 400 errors
            # The response without tool calls is useless anyway, and may have internal
            # state that causes "tool_calls must be followed by tool messages" errors

            # Add a strong forcing message directly
            agent_messages.append(HumanMessage(
                content="STOP. You MUST call a tool before responding. Call search_products_tool, check_product_availability_tool, create_order_tool, get_order_history_tool, or check_order_status_tool now. Do NOT respond with text - call a tool first."
            ))

            # Retry
            response = await sales_agent.ainvoke(agent_messages)
            tool_calls_list = get_tool_calls(response)
            tools_called = len(tool_calls_list) > 0
            logger.info(f"[SALES AGENT] Tools called on second attempt: {tools_called}")

        # Execute tools if requested
        tool_calls_info = []
        new_messages = []  # Track ALL new messages to return to state

        if tools_called:
            from langchain_core.messages import ToolMessage

            # First, add the assistant's message with tool calls to maintain conversation order
            agent_messages.append(response)
            new_messages.append(response)  # CRITICAL: Track this for state update

            # Execute each tool call
            for tool_call in tool_calls_list:
                # Handle multiple formats: OpenAI function format, LangChain dict, or LangChain object
                if isinstance(tool_call, dict):
                    # OpenAI format: {'id': '...', 'function': {'name': '...', 'arguments': '...'}, 'type': 'function'}
                    if 'function' in tool_call:
                        tool_name = tool_call['function'].get('name')
                        args_str = tool_call['function'].get('arguments', '{}')
                        tool_args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        tool_id = tool_call.get('id', str(len(tool_calls_info)))
                    # LangChain format: {'name': '...', 'args': {...}, 'id': '...'}
                    else:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", str(len(tool_calls_info)))
                else:
                    # Object format (has attributes)
                    tool_name = getattr(tool_call, "name", None)
                    tool_args = getattr(tool_call, "args", {})
                    tool_id = getattr(tool_call, "id", str(len(tool_calls_info)))

                # Skip invalid tool calls
                if not tool_name:
                    logger.warning(f"[SALES AGENT] Skipping tool call with no name: {tool_call}")
                    continue

                logger.info(f"[SALES AGENT] Executing tool: {tool_name} with args: {tool_args}")

                # Find and execute the tool
                tool_result = None
                for tool in SALES_TOOLS:
                    if tool.name == tool_name:
                        try:
                            tool_result = await tool.ainvoke(tool_args)
                            logger.info(f"[SALES AGENT] Tool {tool_name} succeeded: {str(tool_result)[:100]}")
                        except Exception as e:
                            tool_result = f"Tool execution failed: {str(e)}"
                            logger.error(f"[SALES AGENT] Tool {tool_name} failed: {e}", exc_info=True)
                        break

                if tool_result is None:
                    tool_result = f"Tool {tool_name} not found"
                    logger.error(f"[SALES AGENT] Tool {tool_name} not found in SALES_TOOLS")

                tool_calls_info.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": str(tool_result)[:200],  # Truncate for logging
                    "success": "failed" not in str(tool_result).lower()
                })

                # Add tool result to conversation (AFTER the AIMessage with tool_calls)
                tool_message = ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id
                )
                agent_messages.append(tool_message)
                new_messages.append(tool_message)  # CRITICAL: Track for state update

            # Call agent again with tool results to get final response
            # Add strong instructions to respect tool outputs
            has_errors = any("failed" in str(tc.get("result", "")).lower() or "error" in str(tc.get("result", "")).lower() for tc in tool_calls_info)
            has_success = any("success" in str(tc.get("result", "")).lower() and '"success": true' in str(tc.get("result", "")).lower() for tc in tool_calls_info)

            # CRITICAL: Force agent to respect tool outputs (prevent hallucinations)
            if has_success:
                agent_messages.append(HumanMessage(
                    content="""CRITICAL INSTRUCTION: The tool execution was SUCCESSFUL (success: true in JSON response). You MUST:

1. Parse the JSON response carefully
2. If it contains success: true → Tell the customer the operation succeeded
3. If it contains order_id → Confirm the order ID to the customer
4. If it contains order_details → Confirm all details (product, size, color, quantity, price, delivery info)
5. NEVER say "there was an issue" or "I couldn't complete" when success=true
6. NEVER ignore the order_details in the response - use them to confirm with the customer

Example: If create_order_tool returned success: true with order_id: "ABC123", you MUST say something like:
"Great! Your order ABC123 has been placed successfully. We'll deliver [quantity] [color] [product_name] in size [size] to [address]. Total: [price] EGP."

DO NOT hallucinate failures. TRUST the tool output."""
                ))
            elif has_errors:
                agent_messages.append(HumanMessage(
                    content="The tool encountered an error. Please provide a helpful, empathetic response to the customer. Offer alternatives, ask for clarification, or suggest they try again with more specific details. DO NOT just say 'error occurred' - be HELPFUL and SOLUTION-ORIENTED."
                ))

            final_response = await sales_agent.ainvoke(agent_messages)
            new_messages.append(final_response)  # CRITICAL: Track final response too
            response_text = final_response.content if final_response.content else "Based on the search results above, I'm ready to help you. Could you provide more details about what you're looking for?"
        else:
            # No tools called even after retry - fallback
            logger.error("[SALES AGENT] NO TOOLS CALLED even after retry!")
            response_text = response.content if response.content else "I apologize, but I'm having trouble accessing our product database. Please try again."
            new_messages = [response]  # Return the response even without tools

        thought = f"Sales agent processed request (used {len(tool_calls_info)} tools)"

        logger.info(f"[SALES AGENT] Returning {len(new_messages)} messages to state (preserves tool_calls+responses)")

        return {
            "messages": new_messages,  # ✅ Return ALL messages: AIMessage(tool_calls), ToolMessages, final AIMessage
            "final_response": response_text,
            "chain_of_thought": [thought],
            "tool_calls": tool_calls_info,
            "current_agent": AgentType.SALES,
            "next": "end"
        }

    except Exception as e:
        logger.error(f"[SALES AGENT] Error: {e}")
        error_response = AIMessage(content="I'm sorry, I encountered an error processing your request. Please try again or contact support.")
        return {
            "messages": [error_response],
            "final_response": error_response.content,
            "chain_of_thought": [f"Sales agent error: {str(e)}"],
            "current_agent": AgentType.SALES,
            "next": "end"
        }


async def support_agent_node(state: FlowinitState) -> Dict[str, Any]:
    """
    Support specialist agent with knowledge base and order tracking tools.

    This node:
    1. Acts as customer support
    2. Has access to knowledge base search and order history tools
    3. Handles FAQs, policies, and general inquiries
    4. Uses RAG tool with self-correction for better answers
    """
    logger.info("[SUPPORT AGENT] Handling support request...")

    messages = state["messages"]
    user_profile = state.get("user_profile", {})
    customer_id = state.get("customer_id", "unknown")

    # Build system message
    profile_context = ""
    if user_profile:
        profile_items = []
        for key, data in user_profile.items():
            profile_items.append(f"- {key}: {data['value']}")
        profile_context = "\n**Customer Profile**:\n" + "\n".join(profile_items)

    system_message = f"""You are a support specialist for an e-commerce clothing store. You MUST use tools to help customers.

**Customer Context**:
- Customer ID: {customer_id} (use this when calling order tools)

{profile_context}

**MANDATORY TOOL USAGE RULES**:
You have NO policy information or order data in your memory. You MUST call tools for ANY support query.

**When customer asks about policies/returns/shipping/payment → IMMEDIATELY call search_knowledge_base_tool**
Examples:
- "What are your return policies?" → call search_knowledge_base_tool(query="return policy")
- "How long does shipping take?" → call search_knowledge_base_tool(query="shipping time")
- "Do you ship to Cairo?" → call search_knowledge_base_tool(query="shipping locations")
- "What payment methods do you accept?" → call search_knowledge_base_tool(query="payment methods")
- "Can I get a refund?" → call search_knowledge_base_tool(query="refund policy")
- "How do I cancel my order?" → call search_knowledge_base_tool(query="order cancellation")
- "I received a damaged item" → call search_knowledge_base_tool(query="damaged item policy")

**IMPORTANT - Order Tracking Tool Selection**:
FOR GENERAL ORDER TRACKING (most common):
- "Where is my order?" → call check_order_status_tool(order_id="{customer_id}_latest") to check their most recent order status
- "فين طلبي؟" → call check_order_status_tool(order_id="{customer_id}_latest")
- "Order status?" → call check_order_status_tool(order_id="{customer_id}_latest")
- "What's the status of my order?" → call check_order_status_tool(order_id="{customer_id}_latest")

FOR SPECIFIC ORDER TRACKING:
- "Track order #12345" → call check_order_status_tool(order_id="12345")
- "Order status #12345" → call check_order_status_tool(order_id="12345")

FOR ORDER HISTORY/MODIFICATIONS:
- "Can I change my order?" → call get_order_history_tool(customer_id="{customer_id}") first to find orders
- "Show me my order history" → call get_order_history_tool(customer_id="{customer_id}")
- "I want to reorder" → call get_order_history_tool(customer_id="{customer_id}")

RULE: Use check_order_status_tool for ANY order tracking query, use get_order_history_tool only for history/reordering purposes

**When customer asks about products → call semantic_product_search_tool**
Examples:
- "Do you have blue shirts?" → call semantic_product_search_tool(query="blue shirts")
- "Show me hoodies" → call semantic_product_search_tool(query="hoodies")

**CRITICAL RULES**:
1. NEVER respond without calling a tool first for policy/order/product queries
2. NEVER say "I'm here to help" without actually calling tools
3. NEVER ask for customer ID - you already have it: {customer_id}
4. **LANGUAGE MATCHING**: ALWAYS respond in the SAME language as the customer:
   - English input → English response
   - Arabic input (عربي) → Arabic response (عربي)
   - Franco-Arabic input (3ayez, 7aga, etc.) → Franco-Arabic response
   - Detect Franco-Arabic by numbers in text: 3=ع, 7=ح, 2=أ, 5=خ, 8=ق, 9=ص
5. After getting tool results, provide a natural, empathetic response in the customer's EXACT language
6. For FAQs, ALWAYS call search_knowledge_base_tool first

**Available Tools**:
- search_knowledge_base_tool(query) - Search FAQs and policies (USE FOR ALL POLICY QUESTIONS)
- get_order_history_tool(customer_id) - Get all customer orders (for "Where is my order?")
- check_order_status_tool(order_id) - Check specific order by ID (only when customer provides order number)
- semantic_product_search_tool(query) - Search products with self-correction

Remember: TOOL FIRST, RESPONSE SECOND. Always call tools before responding."""

    try:
        # Create agent with tools - simple binding without forcing
        support_agent = llm_base.bind_tools(SUPPORT_TOOLS)

        # Build agent messages
        agent_messages = [SystemMessage(content=system_message)] + messages

        logger.info(f"[SUPPORT AGENT] Invoking with {len(agent_messages)} messages")
        logger.info(f"[SUPPORT AGENT] Last message: {messages[-1].content[:100] if messages else 'None'}")

        # First attempt - ask nicely
        response = await support_agent.ainvoke(agent_messages)

        # Check if tools were called - robust checking using helper function
        tool_calls_list = get_tool_calls(response)
        tools_called = len(tool_calls_list) > 0

        logger.info(f"[SUPPORT AGENT] Response type: {type(response)}")
        logger.info(f"[SUPPORT AGENT] Tool calls found: {len(tool_calls_list)}")
        logger.info(f"[SUPPORT AGENT] Tool calls: {tool_calls_list[:100] if tool_calls_list else 'None'}")
        logger.info(f"[SUPPORT AGENT] Tools called on first attempt: {tools_called}")

        # If NO tools called, force a retry with stronger prompting
        if not tools_called:
            logger.warning("[SUPPORT AGENT] No tools called - forcing retry with stronger prompt")

            # CRITICAL: Do NOT append the first response to avoid OpenAI 400 errors
            # The response without tool calls is useless anyway, and may have internal
            # state that causes "tool_calls must be followed by tool messages" errors

            # Add a strong forcing message directly
            agent_messages.append(HumanMessage(
                content="STOP. You MUST call a tool before responding. Call search_knowledge_base_tool, get_order_history_tool, check_order_status_tool, or semantic_product_search_tool now. Do NOT respond with text - call a tool first."
            ))

            # Retry
            response = await support_agent.ainvoke(agent_messages)
            tool_calls_list = get_tool_calls(response)
            tools_called = len(tool_calls_list) > 0
            logger.info(f"[SUPPORT AGENT] Tools called on second attempt: {tools_called}")

        # Execute tools if requested
        tool_calls_info = []
        new_messages = []  # Track ALL new messages to return to state

        if tools_called:
            from langchain_core.messages import ToolMessage

            # First, add the assistant's message with tool calls to maintain conversation order
            agent_messages.append(response)
            new_messages.append(response)  # CRITICAL: Track this for state update

            # Execute each tool call
            for tool_call in tool_calls_list:
                # Handle multiple formats: OpenAI function format, LangChain dict, or LangChain object
                if isinstance(tool_call, dict):
                    # OpenAI format: {'id': '...', 'function': {'name': '...', 'arguments': '...'}, 'type': 'function'}
                    if 'function' in tool_call:
                        tool_name = tool_call['function'].get('name')
                        args_str = tool_call['function'].get('arguments', '{}')
                        tool_args = json.loads(args_str) if isinstance(args_str, str) else args_str
                        tool_id = tool_call.get('id', str(len(tool_calls_info)))
                    # LangChain format: {'name': '...', 'args': {...}, 'id': '...'}
                    else:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", str(len(tool_calls_info)))
                else:
                    # Object format (has attributes)
                    tool_name = getattr(tool_call, "name", None)
                    tool_args = getattr(tool_call, "args", {})
                    tool_id = getattr(tool_call, "id", str(len(tool_calls_info)))

                # Skip invalid tool calls
                if not tool_name:
                    logger.warning(f"[SUPPORT AGENT] Skipping tool call with no name: {tool_call}")
                    continue

                logger.info(f"[SUPPORT AGENT] Executing tool: {tool_name} with args: {tool_args}")

                # Find and execute the tool
                tool_result = None
                for tool in SUPPORT_TOOLS:
                    if tool.name == tool_name:
                        try:
                            tool_result = await tool.ainvoke(tool_args)
                            logger.info(f"[SUPPORT AGENT] Tool {tool_name} succeeded: {str(tool_result)[:100]}")
                        except Exception as e:
                            tool_result = f"Tool execution failed: {str(e)}"
                            logger.error(f"[SUPPORT AGENT] Tool {tool_name} failed: {e}", exc_info=True)
                        break

                if tool_result is None:
                    tool_result = f"Tool {tool_name} not found"
                    logger.error(f"[SUPPORT AGENT] Tool {tool_name} not found in SUPPORT_TOOLS")

                tool_calls_info.append({
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "result": str(tool_result)[:200],  # Truncate for logging
                    "success": "failed" not in str(tool_result).lower()
                })

                # Add tool result to conversation (AFTER the AIMessage with tool_calls)
                tool_message = ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id
                )
                agent_messages.append(tool_message)
                new_messages.append(tool_message)  # CRITICAL: Track for state update

            # Call agent again with tool results to get final response
            # Add strong instructions to respect tool outputs
            has_errors = any("failed" in str(tc.get("result", "")).lower() or "error" in str(tc.get("result", "")).lower() or "not found" in str(tc.get("result", "")).lower() for tc in tool_calls_info)
            has_success = any("success" in str(tc.get("result", "")).lower() and '"success": true' in str(tc.get("result", "")).lower() for tc in tool_calls_info)

            # CRITICAL: Force agent to respect tool outputs (prevent hallucinations)
            if has_success:
                agent_messages.append(HumanMessage(
                    content="""CRITICAL INSTRUCTION: The tool execution was SUCCESSFUL (success: true in JSON response). You MUST:

1. Parse the JSON response carefully
2. If it contains success: true → Tell the customer the operation succeeded
3. If it contains order information → Provide the order details to the customer
4. If it contains policy/FAQ information → Share that information clearly
5. NEVER say "I couldn't find" or "there was an issue" when success=true
6. NEVER ignore successful results - use them to help the customer

DO NOT hallucinate failures. TRUST the tool output."""
                ))
            elif has_errors:
                agent_messages.append(HumanMessage(
                    content="The tool didn't find the information or encountered an error. Please provide a helpful, empathetic response to the customer. Acknowledge the issue, offer alternatives, suggest contacting support, or ask for more details. DO NOT just say 'no information found' - be HELPFUL and provide NEXT STEPS."
                ))

            final_response = await support_agent.ainvoke(agent_messages)
            new_messages.append(final_response)  # CRITICAL: Track final response too
            response_text = final_response.content if final_response.content else "Based on the information I found, how can I assist you further?"
        else:
            # No tools called even after retry - fallback
            logger.error("[SUPPORT AGENT] NO TOOLS CALLED even after retry!")
            response_text = response.content if response.content else "I apologize, but I'm having trouble accessing our support systems. Please try again or contact our support team directly."
            new_messages = [response]  # Return the response even without tools

        thought = f"Support agent processed request (used {len(tool_calls_info)} tools)"

        logger.info(f"[SUPPORT AGENT] Returning {len(new_messages)} messages to state (preserves tool_calls+responses)")

        return {
            "messages": new_messages,  # ✅ Return ALL messages: AIMessage(tool_calls), ToolMessages, final AIMessage
            "final_response": response_text,
            "chain_of_thought": [thought],
            "tool_calls": tool_calls_info,
            "current_agent": AgentType.SUPPORT,
            "next": "end"
        }

    except Exception as e:
        logger.error(f"[SUPPORT AGENT] Error: {e}")
        error_response = AIMessage(content="I apologize for the inconvenience. Let me connect you with a human agent for assistance.")
        return {
            "messages": [error_response],
            "final_response": error_response.content,
            "chain_of_thought": [f"Support agent error: {str(e)}"],
            "current_agent": AgentType.SUPPORT,
            "next": "end"
        }
