"""
Customer database model.
"""
import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class Customer(Base):
    """Customer profiles with cross-channel linking."""
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_id = Column(String(255), unique=True, nullable=False, index=True)
    linked_ids = Column(JSONB, default=[])
    # Map DB column 'metadata' to Python attribute 'extra_data' (metadata is reserved in SQLAlchemy)
    extra_data = Column('metadata', JSONB, default={})
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
