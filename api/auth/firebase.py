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


def create_firebase_user(email: str, password: str, display_name: str) -> str:
    """
    Create a new Firebase user.

    Args:
        email: User's email address
        password: User's password (min 6 characters)
        display_name: User's display name

    Returns:
        Firebase UID of the created user

    Raises:
        firebase_admin.auth.EmailAlreadyExistsError: If email is already in use
    """
    get_firebase_app()

    user = auth.create_user(
        email=email,
        password=password,
        display_name=display_name,
        email_verified=True,  # Admin-created users are pre-verified
    )

    logger.info(f"Created Firebase user: {email} (uid: {user.uid})")
    return user.uid


def delete_firebase_user(uid: str) -> None:
    """
    Delete a Firebase user.

    Args:
        uid: Firebase user ID to delete

    Raises:
        firebase_admin.auth.UserNotFoundError: If user doesn't exist
    """
    get_firebase_app()
    auth.delete_user(uid)
    logger.info(f"Deleted Firebase user: {uid}")


def update_firebase_user(
    uid: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    display_name: Optional[str] = None,
    disabled: Optional[bool] = None
) -> auth.UserRecord:
    """
    Update a Firebase user.

    Args:
        uid: Firebase user ID
        email: New email (optional)
        password: New password (optional)
        display_name: New display name (optional)
        disabled: Whether to disable the account (optional)

    Returns:
        Updated UserRecord
    """
    get_firebase_app()

    update_kwargs = {}
    if email is not None:
        update_kwargs["email"] = email
    if password is not None:
        update_kwargs["password"] = password
    if display_name is not None:
        update_kwargs["display_name"] = display_name
    if disabled is not None:
        update_kwargs["disabled"] = disabled

    user = auth.update_user(uid, **update_kwargs)
    logger.info(f"Updated Firebase user: {uid}")
    return user


def send_password_reset_email(email: str) -> str:
    """
    Generate a password reset link for a user.

    Args:
        email: User's email address

    Returns:
        Password reset link
    """
    get_firebase_app()
    link = auth.generate_password_reset_link(email)
    logger.info(f"Generated password reset link for: {email}")
    return link
