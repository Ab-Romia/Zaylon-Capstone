"""
API key authentication and rate limiting.
"""
from fastapi import HTTPException, Security, Request
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from config import get_settings

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


def get_customer_id_from_request(request: Request) -> str:
    """Extract customer_id for rate limiting from request body or query params."""
    # Try to get from query params first
    customer_id = request.query_params.get("customer_id")
    if customer_id:
        return customer_id
    # Fall back to remote address
    return get_remote_address(request)


# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_string() -> str:
    """Get rate limit string for slowapi."""
    return f"{settings.rate_limit_per_minute}/minute"
