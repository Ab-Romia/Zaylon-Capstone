"""
LangGraph Agent Nodes
Implements the individual nodes (functions) that make up the Zaylon agent graph.
"""

import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.agents.state import ZaylonState, AgentType, update_state
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


def sanitize_message_history(messages: List[AIMessage]) -> List[AIMessage]:
    """
    Sanitize message history to ensure all tool_calls have corresponding tool responses.

    This prevents OpenAI API errors when an AIMessage with tool_calls is not followed
    by the required ToolMessages.

    Args:
        messages: List of conversation messages

    Returns:
        Cleaned list of messages with proper tool_call/response pairing
    """
    from langchain_core.messages import ToolMessage

    # Track which tool_call_ids have responses
    tool_call_ids_with_responses = set()

    # First pass: collect all tool_call_ids that have responses
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_call_ids_with_responses.add(msg.tool_call_id)

    # Second pass: clean messages
    cleaned_messages = []
    for msg in messages:
        # Check if this is an AIMessage with tool_calls
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            # Filter out tool_calls that don't have responses
            valid_tool_calls = []
            orphaned_tool_calls = []

            for tc in msg.tool_calls:
                tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                if tc_id and tc_id in tool_call_ids_with_responses:
                    valid_tool_calls.append(tc)
                else:
                    orphaned_tool_calls.append(tc_id)

            if orphaned_tool_calls:
                logger.warning(f"[MESSAGE_SANITIZER] Found {len(orphaned_tool_calls)} orphaned tool_calls: {orphaned_tool_calls}")

            # If all tool_calls are orphaned, create a new message without tool_calls
            if not valid_tool_calls and msg.tool_calls:
                # Create a new AIMessage without tool_calls
                from langchain_core.messages import AIMessage
                cleaned_msg = AIMessage(
                    content=msg.content if msg.content else "Continuing with the conversation...",
                    id=msg.id if hasattr(msg, 'id') else None
                )
                cleaned_messages.append(cleaned_msg)
                logger.info(f"[MESSAGE_SANITIZER] Removed all orphaned tool_calls from AIMessage")
            elif valid_tool_calls != msg.tool_calls:
                # Some tool_calls are valid, create new message with only valid ones
                from langchain_core.messages import AIMessage
                cleaned_msg = AIMessage(
                    content=msg.content,
                    tool_calls=valid_tool_calls,
                    id=msg.id if hasattr(msg, 'id') else None
                )
                cleaned_messages.append(cleaned_msg)
                logger.info(f"[MESSAGE_SANITIZER] Kept {len(valid_tool_calls)}/{len(msg.tool_calls)} tool_calls")
            else:
                # All tool_calls are valid
                cleaned_messages.append(msg)
        else:
            # Not an AIMessage with tool_calls, keep as-is
            cleaned_messages.append(msg)

    logger.info(f"[MESSAGE_SANITIZER] Processed {len(messages)} messages, output {len(cleaned_messages)} messages")
    return cleaned_messages


# ============================================================================
# Memory Nodes
# ============================================================================

async def load_memory_node(state: ZaylonState) -> Dict[str, Any]:
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


async def save_memory_node(state: ZaylonState) -> Dict[str, Any]:
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

async def supervisor_node(state: ZaylonState) -> Dict[str, Any]:
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
    routing_prompt = f"""You are a routing supervisor for an e-commerce chatbot. Analyze the customer's message and route to the correct specialist.

**Customer Message**: "{last_message}"

**Customer Profile**:
{profile_summary}

**Available Specialists**:
1. **Sales Agent**: Product searches, recommendations, purchases, availability, colors, sizes, prices
2. **Support Agent**: Problems, complaints, order tracking, cancellations, policies, FAQs

**ROUTING RULES** (Strict Priority Order):

**ALWAYS Route to SALES if**:
- Asking about PRODUCTS: "show me", "I want", "عايز", "looking for", "do you have", "عندك"
- Asking about COLORS/SIZES: "what colors", "what sizes", "sizes available"
- Asking about PRICES: "how much", "cheap", "expensive", "price"
- PRODUCT TYPES mentioned: hoodies, shirts, pants, t-shirts, sweaters, jackets, etc.
- Product recommendations or browsing: "best", "recommend", "popular", "new"

**Route to SUPPORT if**:
- PROBLEMS/COMPLAINTS: "damaged", "broken", "wrong item", "not working", "issue"
- ORDER TRACKING: "where is my order", "order status", "فين طلبي", "track"
- MODIFICATIONS: "cancel order", "change order", "modify", "refund"
- PURE POLICIES (no products): "return policy", "shipping policy", "payment methods"

**Examples**:
- "Show me hoodies" → **SALES** (product search)
- "What colors do you have in hoodies?" → **SALES** (product availability)
- "I received a damaged item" → **SUPPORT** (complaint)
- "Where is my order?" → **SUPPORT** (tracking)
- "عايز بنطلون" (I want pants) → **SALES** (product request)

**Decision**: Respond with ONLY one word: "sales" or "support"
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

async def sales_agent_node(state: ZaylonState) -> Dict[str, Any]:
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

    system_message = f"""You are a professional sales specialist for Zaylon, an e-commerce clothing store.

**Customer Context**:
- Customer ID: {customer_id}

{profile_context}

**CORE PRINCIPLE**: You MUST use tools for ALL operations. NEVER simulate actions mentally.

**MANDATORY TOOL USAGE**:

**When customer asks about products** → IMMEDIATELY call search_products_tool:
- "I want a hoodie" → call search_products_tool(query="hoodie")
- "عايز بنطلون" → call search_products_tool(query="بنطلون")
- "Show me blue shirts" → call search_products_tool(query="blue shirts")

**When customer states preferences** → call save_customer_fact_tool:
- "I prefer size M" → call save_customer_fact_tool(fact_key="preferred_size", fact_value="M", ...)
- "My name is Ahmad" → call save_customer_fact_tool(fact_key="customer_name", fact_value="Ahmad", ...)

**When customer asks about policies** → call search_knowledge_base_tool:
- "What's your return policy?" → call search_knowledge_base_tool(query="return policy")

**SIZE CONVERSION SUPPORT**:
The system automatically handles EU/US/UK size conversions for shoes. Examples:
- Customer asks for "EU size 47" → System finds matching "US 13" or "UK 12"
- Customer asks for "size 12" → System finds matching "EU 46" or "UK 11"
You don't need to do manual conversions - just use check_product_availability_tool with the size the customer mentioned.

**CRITICAL - ORDER PLACEMENT WORKFLOW (MUST FOLLOW EXACTLY)**:

**Step 1: Customer Expresses Intent to Buy**
- Examples: "I want to buy this", "3ayz a3ml order", "I'll take 3 of these"
- Action: Move to Step 2

**Step 2: Verify Product Information**
- Required: product_id, product_name, size, color, quantity, total_price
- If missing: call search_products_tool or check_product_availability_tool
- Get product_id from tool response (NEVER make it up)

**Step 3: Verify Customer Information**
- Required: customer_name, phone, address
- Check Customer Profile above for saved data
- If ANY missing: ASK customer directly
  - "To complete your order, I need your full name, phone number, and delivery address."
- When customer provides: call save_customer_fact_tool for each piece FIRST
- NEVER use fake data: NO "John Doe", NO "+201234567890", NO "123 Main Street"

**Step 4: CREATE THE ORDER (MANDATORY - THIS IS THE ACTUAL ORDER PLACEMENT)**
- Once ALL info from Step 2 and Step 3 is collected
- You MUST call: create_order_tool(customer_id, product_id, product_name, size, color, quantity, total_price, customer_name, phone, address, channel)
- This is the ONLY way to create an order in the database
- WITHOUT calling this tool, NO ORDER EXISTS

**Step 5: Confirm Based on Tool Response**
- Parse the JSON response from create_order_tool
- If success: true and order_id exists → Tell customer their order is placed with the order ID
- If success: false or error → Tell customer there was an issue, ask them to try again
- Use order_details from response to confirm specifics

**FORBIDDEN - NEVER DO THIS**:
DO NOT: Claim an order is placed without calling create_order_tool
DO NOT: Say "I've placed your order" when you only checked stock
DO NOT: Make up order IDs
DO NOT: Assume an order exists because you have the information
DO NOT: Use phrases like "I have successfully searched", "I found", "Let me process" - just do it
DO NOT: Be verbose - be concise and professional

**REQUIRED - ALWAYS DO THIS**:
MUST: Call create_order_tool when customer wants to buy AND all info is ready
MUST: Wait for create_order_tool response before confirming to customer
MUST: Use real order_id from tool response
MUST: Only confirm order if create_order_tool returns success: true
MUST: Be direct and professional - no unnecessary explanations

**After Order Creation**:
- DO NOT call check_order_status_tool immediately (causes race conditions)
- The create_order_tool response contains all details
- Use those details to confirm with customer

**Order Tracking**:
- "Where is my order?" → call get_order_history_tool(customer_id="{customer_id}")
- "Order status #12345" → call check_order_status_tool(order_id="12345")

**COMMUNICATION STYLE**:
- Be professional and concise
- Match customer's language (English/Arabic/Franco-Arabic)
- NO phrases like "I have successfully...", "Let me help you find...", "I've searched and found..."
- Just state results directly: "Here are the blue shirts:", "Your order 12345 is confirmed.", "I need your delivery address."
- Act like a professional sales person, not an AI

**CRITICAL RULES**:
1. NEVER confirm order without calling create_order_tool first
2. NEVER say order is placed if create_order_tool wasn't called
3. NEVER make up product_id, order_id, or customer data
4. NEVER use placeholder data for orders
5. ALWAYS call create_order_tool when customer wants to buy and all info is ready
6. ALWAYS trust tool outputs - if success: true, order IS placed; if success: false, order is NOT placed
7. Be concise - no "I have successfully..." or "Let me search..."

**Available Tools**:
- search_products_tool(query, limit=5)
- check_product_availability_tool(product_name, size, color)
- create_order_tool(customer_id, product_id, product_name, size, color, quantity, total_price, customer_name, phone, address, channel)
- get_order_history_tool(customer_id)
- check_order_status_tool(order_id)
- save_customer_fact_tool(customer_id, fact_type, fact_key, fact_value, confidence, source)
- search_knowledge_base_tool(query)

You work for Zaylon. Be professional. Use tools. Confirm only what tools confirm."""

    try:
        # Create agent with tools - simple binding without forcing
        sales_agent = llm_base.bind_tools(SALES_TOOLS)

        # Sanitize message history to ensure tool_calls have corresponding responses
        sanitized_messages = sanitize_message_history(messages)

        # Build agent messages
        agent_messages = [SystemMessage(content=system_message)] + sanitized_messages

        logger.info(f"[SALES AGENT] Invoking with {len(agent_messages)} messages (sanitized from {len(messages) + 1})")
        logger.info(f"[SALES AGENT] Last message: {sanitized_messages[-1].content[:100] if sanitized_messages else 'None'}")

        # Invoke agent - let it decide whether to use tools
        response = await sales_agent.ainvoke(agent_messages)

        # Check if tools were called - robust checking using helper function
        tool_calls_list = get_tool_calls(response)
        tools_called = len(tool_calls_list) > 0

        logger.info(f"[SALES AGENT] Response type: {type(response)}")
        logger.info(f"[SALES AGENT] Tool calls found: {len(tool_calls_list)}")
        logger.info(f"[SALES AGENT] Tools called: {tools_called}")

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
            final_response = await sales_agent.ainvoke(agent_messages)
            new_messages.append(final_response)  # CRITICAL: Track final response too
            response_text = final_response.content if final_response.content else "Based on the search results above, I'm ready to help you. Could you provide more details about what you're looking for?"
        else:
            # No tools called - use direct response (e.g., for greetings, confirmations)
            logger.info("[SALES AGENT] No tools called - using direct response")
            response_text = response.content if response.content else "How can I help you today?"
            new_messages = [response]

        thought = f"Sales agent processed request (used {len(tool_calls_info)} tools)"

        logger.info(f"[SALES AGENT] Returning {len(new_messages)} messages to state (preserves tool_calls+responses)")

        return {
            "messages": new_messages,  # MUST: Return ALL messages: AIMessage(tool_calls), ToolMessages, final AIMessage
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


async def support_agent_node(state: ZaylonState) -> Dict[str, Any]:
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

        # Sanitize message history to ensure tool_calls have corresponding responses
        sanitized_messages = sanitize_message_history(messages)

        # Build agent messages
        agent_messages = [SystemMessage(content=system_message)] + sanitized_messages

        logger.info(f"[SUPPORT AGENT] Invoking with {len(agent_messages)} messages (sanitized from {len(messages) + 1})")
        logger.info(f"[SUPPORT AGENT] Last message: {sanitized_messages[-1].content[:100] if sanitized_messages else 'None'}")

        # Invoke agent - let it decide whether to use tools
        response = await support_agent.ainvoke(agent_messages)

        # Check if tools were called - robust checking using helper function
        tool_calls_list = get_tool_calls(response)
        tools_called = len(tool_calls_list) > 0

        logger.info(f"[SUPPORT AGENT] Response type: {type(response)}")
        logger.info(f"[SUPPORT AGENT] Tool calls found: {len(tool_calls_list)}")
        logger.info(f"[SUPPORT AGENT] Tools called: {tools_called}")

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
            final_response = await support_agent.ainvoke(agent_messages)
            new_messages.append(final_response)  # CRITICAL: Track final response too
            response_text = final_response.content if final_response.content else "Based on the information I found, how can I assist you further?"
        else:
            # No tools called - use direct response (e.g., for greetings, acknowledgments)
            logger.info("[SUPPORT AGENT] No tools called - using direct response")
            response_text = response.content if response.content else "How can I help you today?"
            new_messages = [response]

        thought = f"Support agent processed request (used {len(tool_calls_info)} tools)"

        logger.info(f"[SUPPORT AGENT] Returning {len(new_messages)} messages to state (preserves tool_calls+responses)")

        return {
            "messages": new_messages,  # MUST: Return ALL messages: AIMessage(tool_calls), ToolMessages, final AIMessage
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
