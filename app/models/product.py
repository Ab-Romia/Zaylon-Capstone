"""
Product database model.
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.models.base import Base


class Product(Base):
    """Products table from existing Supabase schema."""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    sizes = Column(ARRAY(String), default=[])
    colors = Column(ARRAY(String), default=[])
    stock_count = Column(Integer, default=0)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
