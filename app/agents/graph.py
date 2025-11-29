"""
LangGraph Agent Graph Assembly
Constructs the Zaylon multi-agent state graph.
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import ZaylonState, NodeName, AgentType
from app.agents.nodes import (
    load_memory_node,
    supervisor_node,
    sales_agent_node,
    support_agent_node,
    save_memory_node
)

logger = logging.getLogger(__name__)


def create_zaylon_graph():
    """
    Create and compile the Zaylon agent graph.

    Graph Flow:
    START → Load Memory → Supervisor → [Sales | Support] → Save Memory → END

    Returns:
        Compiled StateGraph ready for invocation
    """
    logger.info("Building Zaylon agent graph...")

    # Initialize the graph with our state schema
    workflow = StateGraph(ZaylonState)

    # Add nodes
    workflow.add_node(NodeName.LOAD_MEMORY, load_memory_node)
    workflow.add_node(NodeName.SUPERVISOR, supervisor_node)
    workflow.add_node(NodeName.SALES_AGENT, sales_agent_node)
    workflow.add_node(NodeName.SUPPORT_AGENT, support_agent_node)
    workflow.add_node(NodeName.SAVE_MEMORY, save_memory_node)

    # Set entry point
    workflow.set_entry_point(NodeName.LOAD_MEMORY)

    # Add edges
    # 1. Load Memory → Supervisor
    workflow.add_edge(NodeName.LOAD_MEMORY, NodeName.SUPERVISOR)

    # 2. Supervisor → [Sales | Support] (conditional based on routing decision)
    workflow.add_conditional_edges(
        NodeName.SUPERVISOR,
        route_after_supervisor,
        {
            "sales": NodeName.SALES_AGENT,
            "support": NodeName.SUPPORT_AGENT,
        }
    )

    # 3. Sales Agent → Save Memory
    workflow.add_edge(NodeName.SALES_AGENT, NodeName.SAVE_MEMORY)

    # 4. Support Agent → Save Memory
    workflow.add_edge(NodeName.SUPPORT_AGENT, NodeName.SAVE_MEMORY)

    # 5. Save Memory → END
    workflow.add_edge(NodeName.SAVE_MEMORY, END)

    # Compile the graph
    # Use MemorySaver for checkpointing (allows conversation persistence)
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    logger.info("Zaylon graph compiled successfully!")

    return app


def route_after_supervisor(state: ZaylonState) -> Literal["sales", "support"]:
    """
    Routing function for supervisor conditional edge.

    Args:
        state: Current graph state

    Returns:
        "sales" or "support" based on supervisor's decision
    """
    next_agent = state.get("next", "support")

    # Validate routing decision
    if next_agent not in ["sales", "support"]:
        logger.warning(f"Invalid routing decision '{next_agent}', defaulting to support")
        return "support"

    logger.info(f"Routing to: {next_agent}")
    return next_agent  # type: ignore


# Create singleton instance
zaylon_graph = create_zaylon_graph()


async def invoke_agent(
    customer_id: str,
    message: str,
    channel: str = "instagram",
    conversation_history: list = None
) -> dict:
    """
    Convenient wrapper to invoke the Zaylon agent.

    Args:
        customer_id: Customer identifier
        message: User message
        channel: Communication channel
        conversation_history: Optional previous messages

    Returns:
        Dictionary with final_response and metadata
    """
    from langchain_core.messages import HumanMessage

    # Prepare initial state
    initial_state = {
        "messages": conversation_history or [],
        "customer_id": customer_id,
        "channel": channel,
        "user_profile": {},
        "next": "",
        "current_agent": None,
        "chain_of_thought": [],
        "final_response": None,
        "tool_calls": []
    }

    # Add new message
    initial_state["messages"].append(HumanMessage(content=message))

    # Configure for streaming/checkpointing
    config = {"configurable": {"thread_id": customer_id}}

    try:
        # Invoke the graph
        logger.info(f"Invoking agent for customer: {customer_id}")
        result = await zaylon_graph.ainvoke(initial_state, config=config)

        # Extract relevant information
        return {
            "success": True,
            "final_response": result.get("final_response"),
            "chain_of_thought": result.get("chain_of_thought", []),
            "tool_calls": result.get("tool_calls", []),
            "user_profile": result.get("user_profile", {}),
            "current_agent": result.get("current_agent"),
            "messages": result.get("messages", [])
        }

    except Exception as e:
        logger.error(f"Error invoking agent: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "final_response": "I apologize, but I encountered an error. Please try again or contact support."
        }


async def stream_agent(
    customer_id: str,
    message: str,
    channel: str = "instagram",
    conversation_history: list = None
):
    """
    Stream agent execution for real-time updates.

    Args:
        customer_id: Customer identifier
        message: User message
        channel: Communication channel
        conversation_history: Optional previous messages

    Yields:
        State updates as they occur
    """
    from langchain_core.messages import HumanMessage

    # Prepare initial state
    initial_state = {
        "messages": conversation_history or [],
        "customer_id": customer_id,
        "channel": channel,
        "user_profile": {},
        "next": "",
        "current_agent": None,
        "chain_of_thought": [],
        "final_response": None,
        "tool_calls": []
    }

    # Add new message
    initial_state["messages"].append(HumanMessage(content=message))

    # Configure
    config = {"configurable": {"thread_id": customer_id}}

    try:
        # Stream the graph execution
        async for event in zaylon_graph.astream(initial_state, config=config):
            yield event

    except Exception as e:
        logger.error(f"Error streaming agent: {e}", exc_info=True)
        yield {"error": str(e)}
