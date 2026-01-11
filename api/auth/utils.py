"""
Authentication utilities - Password hashing and JWT token handling
"""
from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt

from config.settings import get_settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (must include 'sub' for user id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token data or None if invalid
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_google_token(token: str) -> Optional[dict]:
    """
    Verify a Google OAuth token.

    Args:
        token: Google ID token

    Returns:
        User info dict or None if invalid
    """
    from google.oauth2 import id_token
    from google.auth.transport import requests

    settings = get_settings()

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id
        )

        # Token is valid, return user info
        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "full_name": idinfo.get("name", ""),
            "avatar_url": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }
    except ValueError:
        # Invalid token
        return None
