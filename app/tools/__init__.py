"""
LangChain Tools Package
Wraps existing services into LLM-compatible tools for agent use.
"""

from .products_tools import (
    search_products_tool,
    get_product_details_tool,
    check_product_availability_tool
)
from .orders_tools import (
    create_order_tool,
    get_order_history_tool,
    check_order_status_tool
)
from .rag_tools import (
    search_knowledge_base_tool,
    semantic_product_search_tool
)
from .memory_tools import (
    get_customer_facts_tool,
    save_customer_fact_tool
)

# Tool collections for different agents
SALES_TOOLS = [
    search_products_tool,
    get_product_details_tool,
    check_product_availability_tool,
    create_order_tool,
    get_order_history_tool,
    check_order_status_tool,
    get_customer_facts_tool,  # Allow sales agent to retrieve customer preferences
    save_customer_fact_tool,  # Allow sales agent to save preferences
    search_knowledge_base_tool,  # Allow sales agent to handle FAQ questions in mixed queries
]

SUPPORT_TOOLS = [
    search_knowledge_base_tool,
    semantic_product_search_tool,
    get_order_history_tool,
    check_order_status_tool,
]

MEMORY_TOOLS = [
    get_customer_facts_tool,
    save_customer_fact_tool,
]

__all__ = [
    # Individual tools
    "search_products_tool",
    "get_product_details_tool",
    "check_product_availability_tool",
    "create_order_tool",
    "get_order_history_tool",
    "check_order_status_tool",
    "search_knowledge_base_tool",
    "semantic_product_search_tool",
    "get_customer_facts_tool",
    "save_customer_fact_tool",
    # Tool collections
    "SALES_TOOLS",
    "SUPPORT_TOOLS",
    "MEMORY_TOOLS",
]
