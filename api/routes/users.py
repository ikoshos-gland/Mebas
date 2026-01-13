"""
User routes - Profile and preferences management
"""
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.deps import get_current_active_user
from src.database.db import get_db
from src.database.models import User, Subscription
import logging

logger = logging.getLogger("api.users")

router = APIRouter(prefix="/users", tags=["Users"])


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
    preferences: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionResponse(BaseModel):
    """Subscription response schema"""
    plan: str
    questions_used_today: int
    questions_limit: int
    images_used_today: int
    images_limit: int
    started_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithSubscription(UserResponse):
    """User with subscription info"""
    subscription: Optional[SubscriptionResponse] = None


class UpdateProfileRequest(BaseModel):
    """Update profile request schema"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    grade: Optional[int] = Field(None, ge=1, le=12)
    avatar_url: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    """Update preferences request schema"""
    default_subject: Optional[str] = None
    default_grade: Optional[int] = Field(None, ge=1, le=12)
    notifications_enabled: Optional[bool] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")


# ================== ROUTES ==================

@router.get("/me", response_model=UserWithSubscription)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile with subscription info.
    """
    # Load subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    response = UserWithSubscription.model_validate(current_user)
    if subscription:
        response.subscription = SubscriptionResponse.model_validate(subscription)

    return response


@router.put("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile.
    """
    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guncellenecek alan belirtilmedi"
        )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.email}")

    return UserResponse.model_validate(current_user)


@router.get("/me/preferences", response_model=Dict[str, Any])
async def get_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user's preferences.
    """
    return current_user.preferences or {}


@router.put("/me/preferences", response_model=Dict[str, Any])
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's preferences.
    """
    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guncellenecek tercih belirtilmedi"
        )

    # Merge with existing preferences
    preferences = current_user.preferences or {}
    preferences.update(update_data)
    current_user.preferences = preferences

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    logger.info(f"User preferences updated: {current_user.email}")

    return current_user.preferences


@router.get("/me/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's subscription info.
    """
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abonelik bulunamadi"
        )

    return SubscriptionResponse.model_validate(subscription)
