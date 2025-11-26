"""
API key authentication and rate limiting.
"""
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import get_settings

settings = get_settings()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify the API key from request header."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide X-API-Key header."
        )
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )
    return api_key


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limiting key from request.
    Uses API key if present (preferred for multi-tenant scenarios),
    otherwise falls back to IP address.
    """
    # Try to get API key from header for rate limiting
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key[:8]}"  # Use first 8 chars for privacy

    # Fall back to remote address
    return get_remote_address(request)


def get_customer_id_from_request(request: Request) -> str:
    """Extract customer_id for rate limiting from request body or query params."""
    # Try to get from query params first
    customer_id = request.query_params.get("customer_id")
    if customer_id:
        return customer_id
    # Fall back to rate limit key
    return get_rate_limit_key(request)


# Rate limiter instance - uses API key for better multi-tenant support
limiter = Limiter(key_func=get_rate_limit_key)


def get_rate_limit_string() -> str:
    """Get rate limit string for slowapi."""
    return f"{settings.rate_limit_per_minute}/minute"
