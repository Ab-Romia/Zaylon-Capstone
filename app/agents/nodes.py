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

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize LLM for agents - use gpt-4o for reliable tool calling
llm = ChatOpenAI(
    model="gpt-4o",  # Better function calling than mini
    temperature=0,
    api_key=settings.openai_api_key
)

# Initialize LLM for supervisor with structured output
supervisor_llm = ChatOpenAI(
    model="gpt-4o-mini",  # Mini is fine for simple routing
    temperature=0,
    api_key=settings.openai_api_key
)


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

        extraction_chain = extraction_prompt | llm
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
1. **Sales Agent**: Handles buying, product inquiries, orders, purchases, checkout, availability checks
2. **Support Agent**: Handles FAQs, policies, returns, exchanges, order tracking, general questions

**Routing Rules**:
- If the message is about BUYING, ORDERING, PRODUCTS, AVAILABILITY → Route to **Sales**
- If the message is about POLICIES, RETURNS, TRACKING, QUESTIONS, HELP → Route to **Support**
- If mixed intent (e.g., "return old order and buy new one") → Route to **Sales** (they can handle both)
- If unclear → Route to **Support** (safer default)

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

    # Build system message with profile context
    profile_context = ""
    if user_profile:
        profile_items = []
        for key, data in user_profile.items():
            profile_items.append(f"- {key}: {data['value']}")
        profile_context = "\n**Customer Preferences**:\n" + "\n".join(profile_items)

    system_message = f"""You are a friendly sales representative for an e-commerce clothing store.

**Your Role**:
- Help customers find products
- Check availability and stock
- Process orders
- Provide product recommendations
- Answer pricing questions

{profile_context}

**Available Tools** (YOU MUST USE THESE):
- search_products_tool: Search for products by description
- check_product_availability_tool: Check if product is in stock
- create_order_tool: Create an order for the customer

**CRITICAL INSTRUCTIONS**:
1. **ALWAYS use search_products_tool when customer asks about products** - You do NOT have product information without calling tools
2. **ALWAYS use check_product_availability_tool to verify stock** before recommending products
3. **ALWAYS use create_order_tool when customer wants to buy** - Never tell them to "visit the website"
4. If customer preferences are known, use them in tool calls (e.g., search for their preferred size/color)
5. Be friendly and helpful
6. If creating an order, ensure you have all required info (name, phone, address, size, color)
7. Speak in a mix of English and Arabic if appropriate for the customer

**IMPORTANT**: You CANNOT answer questions about products without using tools. Always call the appropriate tool first, then respond based on the results.

Provide a complete, helpful response."""

    try:
        # Create agent with tools
        sales_agent = llm.bind_tools(SALES_TOOLS)

        # Invoke agent
        agent_messages = [SystemMessage(content=system_message)] + messages
        response = await sales_agent.ainvoke(agent_messages)

        # Execute tools if requested
        tool_calls_info = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            from langchain_core.messages import ToolMessage

            # First, add the assistant's message with tool calls to maintain conversation order
            agent_messages.append(response)

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", str(len(tool_calls_info)))

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
                agent_messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id
                ))

            # Call agent again with tool results to get final response
            final_response = await sales_agent.ainvoke(agent_messages)
            response_text = final_response.content
        else:
            # No tools called, use response directly
            response_text = response.content if response.content else "I'm processing your request..."

        thought = f"Sales agent processed request (used {len(tool_calls_info)} tools)"

        return {
            "messages": [response],
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

    # Build system message
    profile_context = ""
    if user_profile:
        profile_items = []
        for key, data in user_profile.items():
            profile_items.append(f"- {key}: {data['value']}")
        profile_context = "\n**Customer Profile**:\n" + "\n".join(profile_items)

    system_message = f"""You are a helpful customer support representative for an e-commerce clothing store.

**Your Role**:
- Answer questions about policies (returns, shipping, refunds)
- Help track orders
- Provide general information
- Resolve customer concerns

{profile_context}

**Available Tools** (YOU MUST USE THESE):
- search_knowledge_base_tool: Search FAQs and policies
- get_order_history_tool: Retrieve customer's order history
- check_order_status_tool: Check status of specific orders
- semantic_product_search_tool: Search products semantically (includes auto-retry if needed)

**CRITICAL INSTRUCTIONS**:
1. **ALWAYS use search_knowledge_base_tool for policy questions** - You do NOT have policy information without calling this tool
2. **ALWAYS use get_order_history_tool when customer asks about their orders** - Never guess or make up order information
3. **ALWAYS use check_order_status_tool to track specific orders** - Call this whenever customer mentions tracking or status
4. **Use semantic_product_search_tool for product searches** - This tool has self-correction built-in
5. Be empathetic and helpful
6. Provide clear, concise answers

**IMPORTANT**: You CANNOT answer questions about policies, orders, or tracking without using tools. Always call the appropriate tool first, then respond based on the results.

Provide a complete, helpful response."""

    try:
        # Create agent with tools
        support_agent = llm.bind_tools(SUPPORT_TOOLS)

        # Invoke agent
        agent_messages = [SystemMessage(content=system_message)] + messages
        response = await support_agent.ainvoke(agent_messages)

        # Execute tools if requested
        tool_calls_info = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            from langchain_core.messages import ToolMessage

            # First, add the assistant's message with tool calls to maintain conversation order
            agent_messages.append(response)

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", str(len(tool_calls_info)))

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
                agent_messages.append(ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_id
                ))

            # Call agent again with tool results to get final response
            final_response = await support_agent.ainvoke(agent_messages)
            response_text = final_response.content
        else:
            # No tools called, use response directly
            response_text = response.content if response.content else "I'm here to help you."

        thought = f"Support agent processed request (used {len(tool_calls_info)} tools)"

        return {
            "messages": [response],
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
