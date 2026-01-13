"""
Platform Admin User Management Routes
Platform yöneticisi için kullanıcı yönetimi API'leri.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import or_
from firebase_admin.auth import EmailAlreadyExistsError, UserNotFoundError

from api.auth.deps import get_platform_admin, get_db
from api.auth.firebase import (
    create_firebase_user,
    delete_firebase_user,
    update_firebase_user,
    send_password_reset_email
)
from src.database.models import User, School, Subscription, StudentEnrollment

logger = logging.getLogger("api.admin.users")

router = APIRouter(prefix="/users", tags=["Admin Users"])


# ================== SCHEMAS ==================

class AdminCreateUser(BaseModel):
    """Admin tarafından kullanıcı oluşturma şeması"""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern=r"^(student|teacher|school_admin)$")
    grade: Optional[int] = Field(None, ge=1, le=12)
    school_id: Optional[int] = None


class AdminUpdateUser(BaseModel):
    """Admin tarafından kullanıcı güncelleme şeması"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[str] = Field(None, pattern=r"^(student|teacher|school_admin)$")
    grade: Optional[int] = Field(None, ge=1, le=12)
    school_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Kullanıcı yanıt şeması"""
    id: int
    email: str
    full_name: str
    role: str
    grade: Optional[int]
    school_id: Optional[int]
    school_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    profile_complete: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Kullanıcı listesi yanıtı"""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class UserDetailResponse(UserResponse):
    """Kullanıcı detay yanıtı (ek alanlar)"""
    firebase_uid: str
    avatar_url: Optional[str] = None
    classroom_count: int = 0
    conversation_count: int = 0


# ================== ROUTES ==================

@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = Query(None, pattern=r"^(student|teacher|school_admin|platform_admin)$"),
    school_id: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """
    Tüm kullanıcıları listeler.
    Platform admin yetkisi gerektirir.
    """
    query = db.query(User)

    # Filtreler
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    if role:
        query = query.filter(User.role == role)

    if school_id:
        query = query.filter(User.school_id == school_id)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Toplam sayı
    total = query.count()

    # Sayfalama
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    # Okul isimlerini ekle
    items = []
    for user in users:
        school_name = None
        if user.school_id:
            school = db.query(School).filter(School.id == user.school_id).first()
            school_name = school.name if school else None

        items.append(UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            grade=user.grade,
            school_id=user.school_id,
            school_name=school_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            profile_complete=user.profile_complete,
            created_at=user.created_at,
            last_login=user.last_login
        ))

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: AdminCreateUser,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Yeni kullanıcı oluşturur.
    Platform admin yetkisi gerektirir.
    Firebase'de kullanıcı oluşturur ve DB'ye kaydeder.
    """
    # Öğrenci için sınıf zorunlu
    if request.role == "student" and not request.grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Öğrenciler için sınıf seviyesi zorunludur"
        )

    # Email benzersizlik kontrolü
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi zaten kayıtlı"
        )

    # Okul kontrolü
    school = None
    if request.school_id:
        school = db.query(School).filter(School.id == request.school_id).first()
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Okul bulunamadı"
            )

        # Öğretmen/admin limiti kontrolü
        if request.role in ["teacher", "school_admin"]:
            teacher_count = db.query(User).filter(
                User.school_id == request.school_id,
                User.role.in_(["teacher", "school_admin"])
            ).count()
            if teacher_count >= school.max_teachers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bu okulun öğretmen limiti doldu ({school.max_teachers})"
                )

        # Öğrenci limiti kontrolü
        if request.role == "student":
            student_count = db.query(User).filter(
                User.school_id == request.school_id,
                User.role == "student"
            ).count()
            if student_count >= school.max_students:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bu okulun öğrenci limiti doldu ({school.max_students})"
                )

    # Firebase'de kullanıcı oluştur
    firebase_uid = None
    try:
        firebase_uid = create_firebase_user(
            email=request.email,
            password=request.password,
            display_name=request.full_name
        )
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email adresi Firebase'de zaten kayıtlı"
        )
    except Exception as e:
        logger.error(f"Firebase user creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanıcı oluşturulurken hata oluştu"
        )

    try:
        # DB'de kullanıcı oluştur
        user = User(
            firebase_uid=firebase_uid,
            email=request.email,
            full_name=request.full_name,
            role=request.role,
            grade=request.grade if request.role == "student" else None,
            school_id=request.school_id,
            is_active=True,
            is_verified=True,
            profile_complete=True,
        )

        db.add(user)
        db.flush()

        # Subscription oluştur
        subscription = Subscription(
            user_id=user.id,
            plan="free",
            questions_limit=10,
            images_limit=0,
        )
        db.add(subscription)

        db.commit()
        db.refresh(user)

        logger.info(f"Admin {current_user.email} created user: {user.email} ({user.role})")

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            grade=user.grade,
            school_id=user.school_id,
            school_name=school.name if school else None,
            is_active=user.is_active,
            is_verified=user.is_verified,
            profile_complete=user.profile_complete,
            created_at=user.created_at,
            last_login=user.last_login
        )

    except Exception as e:
        # Rollback: Firebase kullanıcısını sil
        if firebase_uid:
            try:
                delete_firebase_user(firebase_uid)
            except Exception:
                pass
        db.rollback()
        logger.error(f"User creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kullanıcı kaydedilirken hata oluştu"
        )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcı detayını getirir.
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    school_name = None
    if user.school_id:
        school = db.query(School).filter(School.id == user.school_id).first()
        school_name = school.name if school else None

    # Ek istatistikler
    classroom_count = 0
    if user.role == "student":
        classroom_count = db.query(StudentEnrollment).filter(
            StudentEnrollment.student_id == user.id,
            StudentEnrollment.status == "active"
        ).count()
    elif user.role in ["teacher", "school_admin"]:
        from src.database.models import Classroom
        classroom_count = db.query(Classroom).filter(
            Classroom.teacher_id == user.id
        ).count()

    from src.database.models import Conversation
    conversation_count = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).count()

    return UserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        grade=user.grade,
        school_id=user.school_id,
        school_name=school_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        profile_complete=user.profile_complete,
        created_at=user.created_at,
        last_login=user.last_login,
        firebase_uid=user.firebase_uid,
        avatar_url=user.avatar_url,
        classroom_count=classroom_count,
        conversation_count=conversation_count
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    request: AdminUpdateUser,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcı bilgilerini günceller.
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    # Platform admin'i güncelleyemez
    if user.role == "platform_admin" and user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin kullanıcıları güncellenemez"
        )

    # Okul değişikliği kontrolü
    if request.school_id is not None and request.school_id != user.school_id:
        if request.school_id:
            school = db.query(School).filter(School.id == request.school_id).first()
            if not school:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Okul bulunamadı"
                )
        user.school_id = request.school_id

    # Rol değişikliği
    if request.role is not None and request.role != user.role:
        user.role = request.role
        # Öğrenci değilse grade'i temizle
        if request.role != "student":
            user.grade = None

    # Sınıf seviyesi
    if request.grade is not None:
        if user.role == "student":
            user.grade = request.grade
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sadece öğrenciler için sınıf seviyesi belirlenebilir"
            )

    # İsim güncellemesi
    if request.full_name is not None:
        user.full_name = request.full_name
        # Firebase'de de güncelle
        try:
            update_firebase_user(user.firebase_uid, display_name=request.full_name)
        except Exception as e:
            logger.warning(f"Firebase update failed: {e}")

    # Aktiflik durumu
    if request.is_active is not None:
        user.is_active = request.is_active
        # Firebase'de de güncelle
        try:
            update_firebase_user(user.firebase_uid, disabled=not request.is_active)
        except Exception as e:
            logger.warning(f"Firebase update failed: {e}")

    db.commit()
    db.refresh(user)

    logger.info(f"Admin {current_user.email} updated user: {user.email}")

    school_name = None
    if user.school_id:
        school = db.query(School).filter(School.id == user.school_id).first()
        school_name = school.name if school else None

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        grade=user.grade,
        school_id=user.school_id,
        school_name=school_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        profile_complete=user.profile_complete,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcıyı siler (Firebase ve DB'den).
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    # Platform admin silinemez
    if user.role == "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin kullanıcıları silinemez"
        )

    # Kendi kendini silemez
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kendinizi silemezsiniz"
        )

    # Firebase'den sil
    try:
        delete_firebase_user(user.firebase_uid)
    except UserNotFoundError:
        logger.warning(f"Firebase user not found: {user.firebase_uid}")
    except Exception as e:
        logger.error(f"Firebase deletion failed: {e}")

    # Sınıf kayıtlarını sil
    db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == user_id
    ).delete()

    # Kullanıcıyı sil
    db.delete(user)
    db.commit()

    logger.info(f"Admin {current_user.email} deleted user: {user.email}")


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcı için şifre sıfırlama linki oluşturur.
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    try:
        reset_link = send_password_reset_email(user.email)
        logger.info(f"Admin {current_user.email} requested password reset for: {user.email}")
        return {
            "message": "Şifre sıfırlama linki oluşturuldu",
            "reset_link": reset_link
        }
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Şifre sıfırlama linki oluşturulamadı"
        )


@router.post("/{user_id}/assign-school")
async def assign_user_to_school(
    user_id: int,
    school_id: int = Query(...),
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcıyı bir okula atar.
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    # Limit kontrolü
    if user.role in ["teacher", "school_admin"]:
        teacher_count = db.query(User).filter(
            User.school_id == school_id,
            User.role.in_(["teacher", "school_admin"]),
            User.id != user_id
        ).count()
        if teacher_count >= school.max_teachers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bu okulun öğretmen limiti doldu ({school.max_teachers})"
            )

    if user.role == "student":
        student_count = db.query(User).filter(
            User.school_id == school_id,
            User.role == "student",
            User.id != user_id
        ).count()
        if student_count >= school.max_students:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bu okulun öğrenci limiti doldu ({school.max_students})"
            )

    user.school_id = school_id
    db.commit()

    logger.info(f"Admin {current_user.email} assigned user {user.email} to school {school.name}")

    return {"message": f"{user.full_name} kullanıcısı {school.name} okuluna atandı"}
