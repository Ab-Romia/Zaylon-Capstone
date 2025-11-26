"""
Memory Tools for LangChain Agents
Manages long-term memory (Memory Bank) for customer preferences and facts.
"""

import json
from datetime import datetime
from typing import Optional
from langchain.tools import tool
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, CustomerFact


@tool
async def get_customer_facts_tool(customer_id: str, fact_type: Optional[str] = None) -> str:
    """
    Retrieve stored facts about a customer from the Memory Bank.

    Args:
        customer_id: Customer identifier to lookup facts for
        fact_type: Optional filter by fact type ("preference", "constraint", "personal_info")

    Returns:
        JSON string containing all stored facts about the customer

    Use this tool:
    - At the START of every conversation to load customer context
    - When the customer references past preferences ("my usual size")
    - Before making recommendations

    Example facts:
    - preferred_size: "M"
    - favorite_color: "blue"
    - style_preference: "casual"
    - budget_range: "100-200 EGP"
    """
    async for db in get_db():
        try:
            # Build query
            if fact_type:
                stmt = select(CustomerFact).where(
                    and_(
                        CustomerFact.customer_id == customer_id,
                        CustomerFact.fact_type == fact_type
                    )
                ).order_by(CustomerFact.updated_at.desc())
            else:
                stmt = select(CustomerFact).where(
                    CustomerFact.customer_id == customer_id
                ).order_by(CustomerFact.updated_at.desc())

            result = await db.execute(stmt)
            facts = result.scalars().all()

            if not facts:
                return json.dumps({
                    "success": True,
                    "found": False,
                    "message": "No facts found for this customer"
                })

            # Format facts
            facts_data = [
                {
                    "fact_type": fact.fact_type,
                    "fact_key": fact.fact_key,
                    "fact_value": fact.fact_value,
                    "confidence": fact.confidence,
                    "source": fact.source,
                    "created_at": fact.created_at.isoformat() if fact.created_at else None,
                    "updated_at": fact.updated_at.isoformat() if fact.updated_at else None
                }
                for fact in facts
            ]

            return json.dumps({
                "success": True,
                "found": True,
                "customer_id": customer_id,
                "facts": facts_data,
                "total_facts": len(facts_data)
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


@tool
async def save_customer_fact_tool(
    customer_id: str,
    fact_type: str,
    fact_key: str,
    fact_value: str,
    confidence: int = 100,
    source: str = "explicit"
) -> str:
    """
    Save a fact about a customer to the Memory Bank for future recall.

    Args:
        customer_id: Customer identifier
        fact_type: Type of fact ("preference", "constraint", "personal_info")
        fact_key: Key identifier (e.g., "preferred_size", "favorite_color")
        fact_value: The actual value (e.g., "M", "blue")
        confidence: Confidence level 0-100 (default: 100 for explicit statements)
        source: "explicit" if customer directly stated, "inferred" if agent deduced (default: "explicit")

    Returns:
        JSON string confirming the fact was saved

    Use this tool when:
    - Customer states a preference ("I wear size M")
    - You learn something important about them
    - After successful orders (to remember what they bought)

    Example usage:
    - Customer says "I always wear size M" → save fact_type="preference", fact_key="preferred_size", fact_value="M"
    - Customer says "I love blue" → save fact_type="preference", fact_key="favorite_color", fact_value="blue"
    - You infer they prefer casual wear → save source="inferred", confidence=70
    """
    async for db in get_db():
        try:
            # Check if fact already exists
            stmt = select(CustomerFact).where(
                and_(
                    CustomerFact.customer_id == customer_id,
                    CustomerFact.fact_key == fact_key
                )
            )
            result = await db.execute(stmt)
            existing_fact = result.scalar_one_or_none()

            if existing_fact:
                # Update existing fact
                existing_fact.fact_value = fact_value
                existing_fact.fact_type = fact_type
                existing_fact.confidence = confidence
                existing_fact.source = source
                existing_fact.updated_at = datetime.utcnow()
                await db.commit()

                return json.dumps({
                    "success": True,
                    "action": "updated",
                    "message": f"Updated existing fact: {fact_key} = {fact_value}"
                })
            else:
                # Create new fact
                new_fact = CustomerFact(
                    customer_id=customer_id,
                    fact_type=fact_type,
                    fact_key=fact_key,
                    fact_value=fact_value,
                    confidence=confidence,
                    source=source
                )
                db.add(new_fact)
                await db.commit()

                return json.dumps({
                    "success": True,
                    "action": "created",
                    "message": f"Saved new fact: {fact_key} = {fact_value}"
                })
        except Exception as e:
            await db.rollback()
            return json.dumps({"success": False, "error": str(e)})
