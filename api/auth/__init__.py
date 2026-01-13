"""
Authentication utilities for MEB RAG API - Firebase Authentication
"""
from api.auth.firebase import (
    get_firebase_app,
    verify_firebase_token,
)
from api.auth.deps import (
    get_current_user,
    get_current_active_user,
    get_optional_user,
)

__all__ = [
    "get_firebase_app",
    "verify_firebase_token",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
]
