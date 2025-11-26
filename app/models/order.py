"""
Order database model.
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base


class Order(Base):
    """Orders table from existing Supabase schema."""
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    product_name = Column(String(255))
    size = Column(String(50))
    color = Column(String(50))
    quantity = Column(Integer, default=1)
    total_price = Column(Float)
    customer_name = Column(String(255))
    customer_phone = Column(String(50))
    delivery_address = Column(Text)
    status = Column(String(50), default="pending")
    instagram_user = Column(String(255))
    created_at = Column(DateTime, default=func.now())
