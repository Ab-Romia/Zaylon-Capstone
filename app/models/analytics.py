"""
Analytics event database model.
"""
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class AnalyticsEvent(Base):
    """Analytics and metrics tracking."""
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSONB, nullable=False)
    response_time_ms = Column(Integer)
    ai_tokens_used = Column(Integer)
    created_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        Index('idx_analytics_type_created', 'event_type', 'created_at'),
    )
