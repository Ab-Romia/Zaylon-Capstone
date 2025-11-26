"""
LangGraph Agent State Schema
Defines the state structure for the Flowinit multi-agent system.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
import operator


class FlowinitState(TypedDict):
    """
    State schema for the Flowinit agentic system.

    This state is passed between all nodes in the graph and tracks:
    - Conversation history
    - Customer context
    - Routing decisions
    - Long-term memory
    """

    # Conversation messages (standard LangChain message list)
    messages: Annotated[List[BaseMessage], operator.add]

    # Customer identifier (e.g., "instagram:@username" or "whatsapp:+201234567890")
    customer_id: str

    # Communication channel
    channel: str  # "instagram" or "whatsapp"

    # Long-term memory (retrieved from Memory Bank)
    user_profile: Dict[str, Any]

    # Routing decision (which node to visit next)
    next: str  # "sales", "support", or "end"

    # Current agent handling the request
    current_agent: Optional[str]  # "supervisor", "sales", "support", "memory"

    # Chain of Thought - tracks agent reasoning for observability
    chain_of_thought: Annotated[List[str], operator.add]

    # Final response to return to user
    final_response: Optional[str]

    # Tool invocations (for logging and debugging)
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]


# Node return type helpers
def update_state(**kwargs) -> FlowinitState:
    """Helper to create state updates."""
    return kwargs  # type: ignore


# Constants for routing
class AgentType:
    """Agent identifiers for routing."""
    SUPERVISOR = "supervisor"
    SALES = "sales"
    SUPPORT = "support"
    MEMORY = "memory"
    END = "end"


# Node names (must match graph node names)
class NodeName:
    """Node identifiers in the graph."""
    LOAD_MEMORY = "load_memory"
    SUPERVISOR = "supervisor"
    SALES_AGENT = "sales_agent"
    SUPPORT_AGENT = "support_agent"
    SAVE_MEMORY = "save_memory"
