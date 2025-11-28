"""
Response cache database model.
"""
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.models.base import Base


class ResponseCache(Base):
    """Cache for common responses."""
    __tablename__ = "response_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_hash = Column(String(64), unique=True, nullable=False, index=True)
    normalized_message = Column(Text, nullable=False)
    cached_response = Column(Text, nullable=False)
    intent = Column(String(100))
    hit_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False, index=True)
