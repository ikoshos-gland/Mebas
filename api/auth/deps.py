"""
Authentication dependencies for FastAPI routes - Firebase Authentication
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from firebase_admin import auth as firebase_auth

from api.auth.firebase import verify_firebase_token
from src.database.db import get_db
from src.database.models import User, Subscription

logger = logging.getLogger("api.auth.deps")

# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from Firebase ID token.

    - Verifies Firebase ID token
    - Creates user in database on first login
    - Updates last_login timestamp

    Raises HTTPException 401 if not authenticated.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum gecersiz veya suresi dolmus",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    try:
        # Verify Firebase token
        decoded_token = verify_firebase_token(credentials.credentials)
    except (firebase_auth.InvalidIdTokenError,
            firebase_auth.ExpiredIdTokenError,
            firebase_auth.RevokedIdTokenError) as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error verifying Firebase token: {e}")
        raise credentials_exception

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise credentials_exception

    # Find user by Firebase UID
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not user:
        # First-time login - create user from Firebase data
        email = decoded_token.get("email", "")
        name = decoded_token.get("name") or email.split("@")[0] if email else "User"

        user = User(
            firebase_uid=firebase_uid,
            email=email,
            full_name=name,
            avatar_url=decoded_token.get("picture"),
            is_verified=decoded_token.get("email_verified", False),
            role="student",  # Default role
            profile_complete=False,  # Needs to complete profile
        )
        db.add(user)
        db.flush()

        # Create default subscription (free plan)
        subscription = Subscription(
            user_id=user.id,
            plan="free",
            questions_limit=10,
            images_limit=0,
        )
        db.add(subscription)
        db.commit()
        db.refresh(user)

        logger.info(f"New user created from Firebase: {user.email}")
    else:
        # Update last login and sync Firebase data
        user.last_login = datetime.utcnow()

        # Sync email verification status from Firebase
        if decoded_token.get("email_verified") and not user.is_verified:
            user.is_verified = True

        # Sync avatar if updated
        if decoded_token.get("picture") and user.avatar_url != decoded_token.get("picture"):
            user.avatar_url = decoded_token.get("picture")

        db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active.

    Raises HTTPException 403 if user is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabiniz devre disi birakilmis"
        )
    return current_user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.

    Useful for endpoints that work for both authenticated and anonymous users.
    Does NOT create user on first login - use get_current_user for that.
    """
    if not credentials:
        return None

    try:
        decoded_token = verify_firebase_token(credentials.credentials)
    except Exception:
        return None

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        return None

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    return user
