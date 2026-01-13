"""
Platform Admin - School Management Routes
Platform yöneticisi için okul CRUD operasyonları.
"""
import logging
import re
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.auth.deps import get_platform_admin, get_db
from api.auth.permissions import TIER_LIMITS, get_tier_limits
from src.database.models import User, School, Classroom, StudentEnrollment, BillingRecord

logger = logging.getLogger("api.admin.schools")

router = APIRouter(prefix="/schools", tags=["Admin - Schools"])


# ================== SCHEMAS ==================

class SchoolCreate(BaseModel):
    """Okul oluşturma şeması"""
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    admin_email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    tier: str = Field(default="small", pattern=r"^(small|medium|large)$")

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug sadece küçük harf, rakam ve tire içerebilir')
        return v.lower()


class SchoolUpdate(BaseModel):
    """Okul güncelleme şeması"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    admin_email: Optional[str] = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None


class SchoolTierUpdate(BaseModel):
    """Okul tier güncelleme şeması"""
    tier: str = Field(..., pattern=r"^(small|medium|large)$")


class SchoolResponse(BaseModel):
    """Okul yanıt şeması"""
    id: int
    name: str
    slug: str
    admin_email: str
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    tier: str
    max_students: int
    max_teachers: int
    features: dict
    is_active: bool
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchoolWithStats(SchoolResponse):
    """Okul yanıtı istatistiklerle"""
    student_count: int = 0
    teacher_count: int = 0
    classroom_count: int = 0


class SchoolListResponse(BaseModel):
    """Okul listesi yanıtı"""
    items: List[SchoolWithStats]
    total: int
    page: int
    page_size: int


class TierInfo(BaseModel):
    """Tier bilgi şeması"""
    name: str
    max_students: int
    max_teachers: int
    max_classrooms: int
    price_try: float
    features: dict


# ================== ROUTES ==================

@router.get("/tiers", response_model=List[TierInfo])
async def list_tiers(
    current_user: User = Depends(get_platform_admin)
):
    """
    Tüm tier bilgilerini listeler.
    Platform admin yetkisi gerektirir.
    """
    return [
        TierInfo(name=name, **limits)
        for name, limits in TIER_LIMITS.items()
    ]


@router.get("", response_model=SchoolListResponse)
async def list_schools(
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None
):
    """
    Tüm okulları listeler (sayfalı).
    Platform admin yetkisi gerektirir.
    """
    query = db.query(School)

    # Filtreler
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (School.name.ilike(search_term)) |
            (School.slug.ilike(search_term)) |
            (School.city.ilike(search_term))
        )

    if tier:
        query = query.filter(School.tier == tier)

    if is_active is not None:
        query = query.filter(School.is_active == is_active)

    # Toplam sayı
    total = query.count()

    # Sayfalama
    offset = (page - 1) * page_size
    schools = query.order_by(School.created_at.desc()).offset(offset).limit(page_size).all()

    # İstatistiklerle birlikte döndür
    items = []
    for school in schools:
        student_count = db.query(User).filter(
            User.school_id == school.id,
            User.role == "student"
        ).count()

        teacher_count = db.query(User).filter(
            User.school_id == school.id,
            User.role == "teacher"
        ).count()

        classroom_count = db.query(Classroom).filter(
            Classroom.school_id == school.id,
            Classroom.is_active == True
        ).count()

        school_data = SchoolWithStats.model_validate(school)
        school_data.student_count = student_count
        school_data.teacher_count = teacher_count
        school_data.classroom_count = classroom_count
        items.append(school_data)

    return SchoolListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
async def create_school(
    request: SchoolCreate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Yeni okul oluşturur.
    Platform admin yetkisi gerektirir.
    """
    # Slug benzersizliği kontrolü
    existing = db.query(School).filter(School.slug == request.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu slug zaten kullanılıyor"
        )

    # Tier limitlerini al
    tier_limits = get_tier_limits(request.tier)

    school = School(
        name=request.name,
        slug=request.slug,
        admin_email=request.admin_email,
        phone=request.phone,
        address=request.address,
        city=request.city,
        tier=request.tier,
        max_students=tier_limits["max_students"],
        max_teachers=tier_limits["max_teachers"],
        features=tier_limits["features"],
        is_active=True,
        activated_at=datetime.utcnow(),
    )

    db.add(school)
    db.commit()
    db.refresh(school)

    logger.info(f"School created: {school.slug} by {current_user.email}")

    return school


@router.get("/{school_id}", response_model=SchoolWithStats)
async def get_school(
    school_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Okul detaylarını getirir.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    # İstatistikleri hesapla
    student_count = db.query(User).filter(
        User.school_id == school.id,
        User.role == "student"
    ).count()

    teacher_count = db.query(User).filter(
        User.school_id == school.id,
        User.role == "teacher"
    ).count()

    classroom_count = db.query(Classroom).filter(
        Classroom.school_id == school.id,
        Classroom.is_active == True
    ).count()

    response = SchoolWithStats.model_validate(school)
    response.student_count = student_count
    response.teacher_count = teacher_count
    response.classroom_count = classroom_count

    return response


@router.put("/{school_id}", response_model=SchoolResponse)
async def update_school(
    school_id: int,
    request: SchoolUpdate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Okul bilgilerini günceller.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    # Güncellenebilir alanlar
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(school, key, value)

    db.commit()
    db.refresh(school)

    logger.info(f"School updated: {school.slug} by {current_user.email}")

    return school


@router.put("/{school_id}/tier", response_model=SchoolResponse)
async def update_school_tier(
    school_id: int,
    request: SchoolTierUpdate,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Okul tier'ını değiştirir.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    # Yeni tier limitlerini al
    tier_limits = get_tier_limits(request.tier)

    # Mevcut kullanıcı sayılarını kontrol et
    student_count = db.query(User).filter(
        User.school_id == school.id,
        User.role == "student"
    ).count()

    teacher_count = db.query(User).filter(
        User.school_id == school.id,
        User.role == "teacher"
    ).count()

    # Downgrade kontrolü
    if student_count > tier_limits["max_students"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu tier için maksimum {tier_limits['max_students']} öğrenci olabilir. Şu an {student_count} öğrenci var."
        )

    if teacher_count > tier_limits["max_teachers"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu tier için maksimum {tier_limits['max_teachers']} öğretmen olabilir. Şu an {teacher_count} öğretmen var."
        )

    # Güncelle
    school.tier = request.tier
    school.max_students = tier_limits["max_students"]
    school.max_teachers = tier_limits["max_teachers"]
    school.features = tier_limits["features"]

    db.commit()
    db.refresh(school)

    logger.info(f"School tier changed: {school.slug} to {request.tier} by {current_user.email}")

    return school


@router.post("/{school_id}/activate", response_model=SchoolResponse)
async def activate_school(
    school_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Devre dışı bırakılmış okulu aktifleştirir.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    if school.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Okul zaten aktif"
        )

    school.is_active = True
    school.activated_at = datetime.utcnow()

    db.commit()
    db.refresh(school)

    logger.info(f"School activated: {school.slug} by {current_user.email}")

    return school


@router.post("/{school_id}/deactivate", response_model=SchoolResponse)
async def deactivate_school(
    school_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Okulu devre dışı bırakır (soft delete).
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    if not school.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Okul zaten devre dışı"
        )

    school.is_active = False

    db.commit()
    db.refresh(school)

    logger.info(f"School deactivated: {school.slug} by {current_user.email}")

    return school


@router.get("/{school_id}/users", response_model=dict)
async def list_school_users(
    school_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None
):
    """
    Okuldaki kullanıcıları listeler.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    query = db.query(User).filter(User.school_id == school_id)

    if role:
        query = query.filter(User.role == role)

    total = query.count()
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "grade": u.grade,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.put("/{school_id}/users/{user_id}/role")
async def change_user_role(
    school_id: int,
    user_id: int,
    role: str = Query(..., pattern=r"^(student|teacher|school_admin)$"),
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcı rolünü değiştirir.
    Platform admin yetkisi gerektirir.
    """
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Okul bulunamadı"
        )

    user = db.query(User).filter(User.id == user_id, User.school_id == school_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    # Limit kontrolü - sadece teacher rolü için
    if role == "teacher":
        teacher_count = db.query(User).filter(
            User.school_id == school_id,
            User.role == "teacher",
            User.id != user_id
        ).count()

        if teacher_count >= school.max_teachers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maksimum öğretmen limitine ({school.max_teachers}) ulaşıldı"
            )

    old_role = user.role
    user.role = role

    # Öğretmenden öğrenciye geçişte grade kontrolü
    if role == "student" and not user.grade:
        user.grade = 9  # Default grade

    db.commit()

    logger.info(f"User role changed: {user.email} from {old_role} to {role} by {current_user.email}")

    return {"message": f"Kullanıcı rolü {role} olarak güncellendi"}


@router.delete("/{school_id}/users/{user_id}")
async def remove_user_from_school(
    school_id: int,
    user_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """
    Kullanıcıyı okuldan çıkarır.
    Platform admin yetkisi gerektirir.
    """
    user = db.query(User).filter(User.id == user_id, User.school_id == school_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )

    user.school_id = None

    # Sınıf kayıtlarını da kaldır
    db.query(StudentEnrollment).filter(StudentEnrollment.student_id == user_id).delete()

    db.commit()

    logger.info(f"User removed from school: {user.email} from school {school_id} by {current_user.email}")

    return {"message": "Kullanıcı okuldan çıkarıldı"}
