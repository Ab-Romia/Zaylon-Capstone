"""
Prompt Template database model.
Phase 3: Zero Hard-Coding - Store all agent prompts in database.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.models.base import Base


class PromptTypeEnum(str, enum.Enum):
    """Prompt type enumeration."""
    SYSTEM = "system"
    TOOL_INSTRUCTION = "tool_instruction"
    SYNTHESIS = "synthesis"
    EXTRACTION = "extraction"
    ROUTING = "routing"


class AgentTypeEnum(str, enum.Enum):
    """Agent type enumeration."""
    SALES = "sales"
    SUPPORT = "support"
    SUPERVISOR = "supervisor"
    MEMORY = "memory"


class PromptTemplate(Base):
    """
    Prompt templates table for storing agent system prompts.

    Features:
    - Jinja2 templates with variable injection
    - Multi-language support
    - Channel-specific prompts
    - Versioning and A/B testing
    - Performance tracking
    """
    __tablename__ = "prompt_templates"

    # Identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    agent_type = Column(String(50), nullable=False)  # Using String instead of Enum for flexibility
    prompt_type = Column(String(50), nullable=False, default="system")

    # Template content
    template = Column(Text, nullable=False)  # Jinja2 template with {{variables}}
    variables = Column(JSONB, default=[])  # ["customer_id", "user_profile", "channel"]

    # Metadata
    version = Column(Integer, default=1)
    language = Column(String(10), default="en")  # en, es, ar, fr, de, pt
    channel = Column(String(50))  # instagram, whatsapp, web, null for all

    # Versioning and A/B testing
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default prompt for this agent_type
    parent_id = Column(UUID(as_uuid=True))  # For versioning

    # Performance tracking
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float)  # Track how well this prompt performs
    avg_response_time = Column(Float)  # Average time to generate response (ms)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    updated_by = Column(String(255))

    def __repr__(self):
        return f"<PromptTemplate(name='{self.name}', agent_type='{self.agent_type}', version={self.version})>"
