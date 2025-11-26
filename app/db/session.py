"""
Database session management using SQLAlchemy async.
"""
import socket
from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

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
