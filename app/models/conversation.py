"""
Conversation database model.
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class Conversation(Base):
    """Stores all conversation messages."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(255), nullable=False, index=True)
    channel = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    direction = Column(String(20), nullable=False)  # incoming or outgoing
    intent = Column(String(100))
    # Map DB column 'metadata' to Python attribute 'extra_data' (metadata is reserved in SQLAlchemy)
    extra_data = Column('metadata', JSONB, default={})
    created_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index('idx_conversations_customer_created', 'customer_id', 'created_at'),
    )
