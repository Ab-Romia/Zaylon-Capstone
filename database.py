"""
Database models and connection management using SQLAlchemy async.
"""
from datetime import datetime
from typing import AsyncGenerator
import socket
import re
from urllib.parse import urlparse, urlunparse
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
import uuid

from config import get_settings

settings = get_settings()


def force_ipv4_connection_url(database_url: str) -> str:
    """
    Force IPv4 resolution for database connection URL.
    Resolves hostname to IPv4 address to avoid IPv6 connection issues on Render.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Parse the database URL
        parsed = urlparse(database_url)
        hostname = parsed.hostname

        if not hostname:
            return database_url

        logger.info(f"Attempting to resolve database hostname: {hostname}")

        # Check if hostname is already an IPv4 address
        try:
            socket.inet_aton(hostname)
            # Already an IPv4 address
            logger.info(f"Hostname is already IPv4: {hostname}")
            return database_url
        except socket.error:
            pass

        # Check if it's an IPv6 address (skip resolution)
        if ':' in hostname and '[' in parsed.netloc:
            # It's an IPv6 address, try to resolve to IPv4
            logger.warning(f"Detected IPv6 address in connection string: {hostname}")
            hostname = hostname.strip('[]')

        # Resolve hostname to IPv4 only
        try:
            # Get IPv4 addresses only (AF_INET)
            addr_info = socket.getaddrinfo(
                hostname,
                parsed.port,
                socket.AF_INET,  # Force IPv4
                socket.SOCK_STREAM
            )
            if addr_info:
                ipv4_address = addr_info[0][4][0]
                logger.info(f"Resolved {hostname} to IPv4: {ipv4_address}")

                # Rebuild the netloc with IPv4 address
                if parsed.username and parsed.password:
                    new_netloc = f"{parsed.username}:{parsed.password}@{ipv4_address}"
                elif parsed.username:
                    new_netloc = f"{parsed.username}@{ipv4_address}"
                else:
                    new_netloc = ipv4_address

                # Add port if present
                if parsed.port:
                    new_netloc = f"{new_netloc}:{parsed.port}"

                # Reconstruct URL
                new_parsed = parsed._replace(netloc=new_netloc)
                resolved_url = urlunparse(new_parsed)
                logger.info(f"Database URL successfully converted to IPv4")
                return resolved_url
        except socket.gaierror as e:
            # If resolution fails, return original URL
            logger.error(f"Failed to resolve hostname to IPv4: {e}")
            pass

    except Exception as e:
        # If anything fails, return original URL
        logger.error(f"Error forcing IPv4 for database URL: {e}")

    return database_url


# Force IPv4 connection
ipv4_database_url = force_ipv4_connection_url(settings.database_url)

# Create async engine with IPv4-compatible settings
engine = create_async_engine(
    ipv4_database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "timeout": 30,  # Increase connection timeout
        "command_timeout": 60,  # Command execution timeout
        "server_settings": {
            "application_name": "ecommerce_dm_microservice",
            "jit": "off",
            "default_transaction_isolation": "read committed"
        }
    }
)

# Create async session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


# ============================================================================
# Existing Supabase Tables (Read-Only Models)
# ============================================================================

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


# ============================================================================
# New Tables for Microservice
# ============================================================================

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


class CustomerFact(Base):
    """Memory Bank - Long-term customer facts and preferences."""
    __tablename__ = "customer_facts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(255), nullable=False, index=True)
    fact_type = Column(String(100), nullable=False)  # preference, constraint, personal_info
    fact_key = Column(String(255), nullable=False)  # e.g., "preferred_size", "favorite_color"
    fact_value = Column(Text, nullable=False)  # The actual value
    confidence = Column(Integer, default=100)  # 0-100, how confident we are
    source = Column(String(50))  # 'explicit' (user stated) or 'inferred' (agent deduced)
    extra_data = Column('metadata', JSONB, default={})  # Additional context
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_customer_facts_customer', 'customer_id'),
        Index('idx_customer_facts_key', 'customer_id', 'fact_key'),
    )


# ============================================================================
# Database Session Management
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Create only the new tables (don't touch existing Supabase tables)
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()
