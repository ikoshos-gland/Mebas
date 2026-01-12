"""
Firebase Admin SDK initialization and utilities
"""
import os
import json
import logging
from functools import lru_cache
from typing import Optional

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import InvalidIdTokenError, ExpiredIdTokenError, RevokedIdTokenError

from config.settings import get_settings

logger = logging.getLogger("api.auth.firebase")

_firebase_app: Optional[firebase_admin.App] = None


def get_firebase_app() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK (singleton).

    Supports two modes:
    1. Path to credentials file (development)
    2. JSON string from environment variable (production/Docker)
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    settings = get_settings()
    cred = None

    # Option 1: Path to credentials file
    if settings.firebase_credentials_path and os.path.exists(settings.firebase_credentials_path):
        logger.info(f"Loading Firebase credentials from file: {settings.firebase_credentials_path}")
        cred = credentials.Certificate(settings.firebase_credentials_path)

    # Option 2: JSON string from environment (for Docker/production)
    elif os.environ.get("FIREBASE_CREDENTIALS_JSON"):
        logger.info("Loading Firebase credentials from FIREBASE_CREDENTIALS_JSON environment variable")
        cred_dict = json.loads(os.environ["FIREBASE_CREDENTIALS_JSON"])
        cred = credentials.Certificate(cred_dict)

    else:
        raise RuntimeError(
            "Firebase credentials not found. Please provide either:\n"
            "1. FIREBASE_CREDENTIALS_PATH in .env pointing to service account JSON file\n"
            "2. FIREBASE_CREDENTIALS_JSON environment variable with JSON string"
        )

    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized successfully")

    return _firebase_app


def verify_firebase_token(id_token: str) -> dict:
    """
    Verify a Firebase ID token.

    Args:
        id_token: Firebase ID token string from client

    Returns:
        Decoded token dict containing:
        - uid: Firebase user ID
        - email: User's email
        - email_verified: Whether email is verified
        - name: Display name (if set)
        - picture: Profile picture URL (if set)
        - firebase: Firebase-specific claims

    Raises:
        InvalidIdTokenError: If token format is invalid
        ExpiredIdTokenError: If token has expired
        RevokedIdTokenError: If token has been revoked
    """
    # Ensure Firebase is initialized
    get_firebase_app()

    # Verify the token
    decoded_token = auth.verify_id_token(id_token)

    return decoded_token


def get_firebase_user(uid: str) -> Optional[auth.UserRecord]:
    """
    Get Firebase user by UID.

    Args:
        uid: Firebase user ID

    Returns:
        UserRecord or None if not found
    """
    get_firebase_app()

    try:
        return auth.get_user(uid)
    except auth.UserNotFoundError:
        return None


def revoke_user_tokens(uid: str) -> None:
    """
    Revoke all refresh tokens for a user.
    Forces re-authentication on all devices.

    Args:
        uid: Firebase user ID
    """
    get_firebase_app()
    auth.revoke_refresh_tokens(uid)
    logger.info(f"Revoked all tokens for user: {uid}")
