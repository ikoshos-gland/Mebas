"""
Authentication routes - Register, Login, Google OAuth
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_google_token,
)
from src.database.db import get_db
from src.database.models import User, Subscription
import logging

logger = logging.getLogger("api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================== SCHEMAS ==================

class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    full_name: str
    role: str
    grade: Optional[int] = None
    avatar_url: Optional[str] = None
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Authentication response with token and user"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request schema"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default="student", pattern="^(student|teacher)$")
    grade: Optional[int] = Field(default=None, ge=1, le=12)


class GoogleAuthRequest(BaseModel):
    """Google OAuth request schema"""
    credential: str


# ================== ROUTES ==================

@router.post("/register", response_model=AuthResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email and password.

    - **email**: User's email address (must be unique)
    - **password**: Password (min 6 characters)
    - **full_name**: User's full name
    - **role**: 'student' or 'teacher'
    - **grade**: Grade level (1-12, required for students)
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kullanılıyor"
        )

    # Validate grade for students
    if request.role == "student" and not request.grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Öğrenciler için sınıf seviyesi gereklidir"
        )

    # Create user
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        role=request.role,
        grade=request.grade,
        is_active=True,
        is_verified=False,  # Email verification not implemented yet
    )
    db.add(user)
    db.flush()  # Get user.id

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

    logger.info(f"New user registered: {user.email}")

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns JWT token and user info.
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı"
        )

    # Check if user has a password (not OAuth-only)
    if not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bu hesap Google ile oluşturulmuş. Lütfen Google ile giriş yapın."
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"User logged in: {user.email}")

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/google", response_model=AuthResponse)
async def google_auth(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate with Google OAuth.

    Creates a new user if doesn't exist, otherwise logs in.
    """
    # Verify Google token
    google_user = verify_google_token(request.credential)

    if not google_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google doğrulama başarısız"
        )

    # Check if user exists by Google ID
    user = db.query(User).filter(User.google_id == google_user["google_id"]).first()

    if not user:
        # Check if email exists (user registered with email, now linking Google)
        user = db.query(User).filter(User.email == google_user["email"]).first()

        if user:
            # Link Google account to existing user
            user.google_id = google_user["google_id"]
            if not user.avatar_url and google_user.get("avatar_url"):
                user.avatar_url = google_user["avatar_url"]
        else:
            # Create new user
            user = User(
                email=google_user["email"],
                full_name=google_user["full_name"] or google_user["email"].split("@")[0],
                google_id=google_user["google_id"],
                avatar_url=google_user.get("avatar_url"),
                is_active=True,
                is_verified=google_user.get("email_verified", False),
                role="student",  # Default role, can be changed in settings
            )
            db.add(user)
            db.flush()

            # Create default subscription
            subscription = Subscription(
                user_id=user.id,
                plan="free",
                questions_limit=10,
                images_limit=0,
            )
            db.add(subscription)

            logger.info(f"New Google user registered: {user.email}")

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesabınız devre dışı bırakılmış"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    logger.info(f"Google user logged in: {user.email}")

    # Create access token
    access_token = create_access_token(data={"sub": user.id})

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: Session = Depends(get_db),
):
    """
    Get current user info.

    Requires authentication.
    """
    from api.auth.deps import get_current_active_user
    from fastapi import Security
    # Note: This endpoint is defined but needs the proper auth dependency
    # Use the /users/me endpoint instead for full profile
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Bu endpoint /users/me olarak taşındı"
    )
