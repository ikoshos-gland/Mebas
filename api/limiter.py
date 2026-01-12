"""
Rate limiter configuration for API endpoints.
Shared module to avoid circular imports.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - shared across all routes
limiter = Limiter(key_func=get_remote_address)
