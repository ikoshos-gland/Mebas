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
from api.auth.permissions import Role, Permission, has_permission
from src.database.db import get_db
from src.database.models import User, Subscription, School, Classroom, StudentEnrollment

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


# ================== ROLE-BASED DEPENDENCIES ==================

async def get_current_teacher(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require teacher role or higher (teacher, school_admin, platform_admin).

    Raises HTTPException 403 if user doesn't have teacher privileges.
    """
    allowed_roles = [Role.TEACHER.value, Role.SCHOOL_ADMIN.value, Role.PLATFORM_ADMIN.value]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için öğretmen yetkisi gerekli"
        )
    return current_user


async def get_current_school_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require school admin role or higher (school_admin, platform_admin).

    Raises HTTPException 403 if user doesn't have school admin privileges.
    """
    allowed_roles = [Role.SCHOOL_ADMIN.value, Role.PLATFORM_ADMIN.value]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için okul yöneticisi yetkisi gerekli"
        )
    return current_user


async def get_platform_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require platform admin role.

    Raises HTTPException 403 if user is not a platform admin.
    """
    if current_user.role != Role.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için platform yöneticisi yetkisi gerekli"
        )
    return current_user


# ================== RESOURCE ACCESS VERIFICATION ==================

async def verify_school_access(
    school_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> School:
    """
    Verify user has access to the specified school.

    - Platform admins can access any school
    - Other users must belong to the school

    Returns the School object if access is granted.
    Raises HTTPException 404 if school not found, 403 if access denied.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    # Platform admins can access any school
    if current_user.role == Role.PLATFORM_ADMIN.value:
        return school

    # Others must belong to the school
    if current_user.school_id != school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu okula erişim yetkiniz yok"
        )

    return school


async def verify_classroom_access(
    classroom_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Classroom:
    """
    Verify user has access to the specified classroom.

    Access rules:
    - Platform admins: Access any classroom
    - School admins: Access any classroom in their school
    - Teachers: Access classrooms they own
    - Students: Access classrooms they're enrolled in

    Returns the Classroom object if access is granted.
    Raises HTTPException 404 if not found, 403 if access denied.
    """
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sınıf bulunamadı"
        )

    # Platform admins can access any classroom
    if current_user.role == Role.PLATFORM_ADMIN.value:
        return classroom

    # Must be same school for all other users
    if current_user.school_id != classroom.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sınıfa erişim yetkiniz yok"
        )

    # School admins can access any classroom in their school
    if current_user.role == Role.SCHOOL_ADMIN.value:
        return classroom

    # Teachers can access classrooms they own
    if current_user.role == Role.TEACHER.value:
        if classroom.teacher_id == current_user.id:
            return classroom
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sınıfa erişim yetkiniz yok"
        )

    # Students must be enrolled
    if current_user.role == Role.STUDENT.value:
        enrollment = db.query(StudentEnrollment).filter(
            StudentEnrollment.classroom_id == classroom_id,
            StudentEnrollment.student_id == current_user.id,
            StudentEnrollment.status == "active"
        ).first()

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu sınıfa kayıtlı değilsiniz"
            )
        return classroom

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Erişim reddedildi"
    )


async def verify_teacher_owns_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
) -> Classroom:
    """
    Verify the current teacher owns the specified classroom.

    - Platform admins can manage any classroom
    - School admins can manage any classroom in their school
    - Teachers can only manage their own classrooms

    Returns the Classroom object if access is granted.
    """
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sınıf bulunamadı"
        )

    # Platform admins can manage any classroom
    if current_user.role == Role.PLATFORM_ADMIN.value:
        return classroom

    # Must be same school
    if current_user.school_id != classroom.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sınıfı yönetme yetkiniz yok"
        )

    # School admins can manage any classroom in their school
    if current_user.role == Role.SCHOOL_ADMIN.value:
        return classroom

    # Teachers can only manage their own classrooms
    if classroom.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sınıfı yönetme yetkiniz yok"
        )

    return classroom


async def require_school_membership(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Require user to be a member of a school.

    Platform admins are exempt from this requirement.
    Raises HTTPException 403 if user has no school.
    """
    if current_user.role == Role.PLATFORM_ADMIN.value:
        return current_user

    if not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için bir okula üye olmanız gerekli"
        )
    return current_user
