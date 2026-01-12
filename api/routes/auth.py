"""
Authentication routes - Firebase Authentication

Firebase handles: register, login, password reset, Google OAuth
Backend handles: profile completion, user data sync
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.deps import get_current_user, get_current_active_user
from src.database.db import get_db
from src.database.models import User

logger = logging.getLogger("api.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================== SCHEMAS ==================

class UserResponse(BaseModel):
    """User response schema"""
    id: int
    firebase_uid: str
    email: str
    full_name: str
    role: str
    grade: Optional[int] = None
    avatar_url: Optional[str] = None
    is_verified: bool
    profile_complete: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompleteProfileRequest(BaseModel):
    """Complete profile after first Firebase login"""
    role: str = Field(pattern="^(student|teacher)$")
    grade: Optional[int] = Field(None, ge=1, le=12)
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)


class UpdateProfileRequest(BaseModel):
    """Update user profile"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    grade: Optional[int] = Field(None, ge=1, le=12)


# ================== ROUTES ==================

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user.

    Returns user profile from database.
    Creates user on first login if not exists.
    """
    return UserResponse.model_validate(current_user)


@router.post("/complete-profile", response_model=UserResponse)
async def complete_profile(
    request: CompleteProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete user profile after first Firebase login.

    Required for students to set their grade.
    Can only be called once (when profile_complete is False).
    """
    if current_user.profile_complete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profil zaten tamamlanmis"
        )

    if request.role == "student" and not request.grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ogrenciler icin sinif seviyesi gereklidir"
        )

    current_user.role = request.role
    current_user.grade = request.grade if request.role == "student" else None

    if request.full_name:
        current_user.full_name = request.full_name

    current_user.profile_complete = True
    current_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    logger.info(f"Profile completed for user: {current_user.email}, role: {request.role}")

    return UserResponse.model_validate(current_user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile.

    Only allows updating certain fields (full_name, grade).
    """
    if request.full_name is not None:
        current_user.full_name = request.full_name

    if request.grade is not None:
        if current_user.role != "student":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sinif seviyesi sadece ogrenciler icin ayarlanabilir"
            )
        current_user.grade = request.grade

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    logger.info(f"Profile updated for user: {current_user.email}")

    return UserResponse.model_validate(current_user)
