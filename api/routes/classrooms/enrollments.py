"""
Student Enrollment Routes
Öğrenci kayıt yönetimi API'leri.
"""
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth.deps import (
    get_current_active_user,
    get_current_teacher,
    verify_teacher_owns_classroom,
    require_school_membership,
    get_db
)
from api.auth.permissions import Role
from src.database.models import User, Classroom, StudentEnrollment

logger = logging.getLogger("api.enrollments")

router = APIRouter(tags=["Enrollments"])


# ================== SCHEMAS ==================

class EnrollmentResponse(BaseModel):
    """Kayıt yanıt şeması"""
    id: int
    student_id: int
    student_name: str
    student_email: str
    student_grade: Optional[int]
    status: str
    enrolled_at: datetime
    removed_at: Optional[datetime]

    class Config:
        from_attributes = True


class EnrollmentListResponse(BaseModel):
    """Kayıt listesi yanıtı"""
    items: List[EnrollmentResponse]
    total: int


class JoinClassroomRequest(BaseModel):
    """Sınıfa katılma isteği"""
    join_code: str = Field(..., min_length=8, max_length=8)


class EnrolledClassroomResponse(BaseModel):
    """Kayıtlı sınıf yanıtı"""
    id: int
    classroom_id: int
    classroom_name: str
    grade: int
    subject: Optional[str]
    teacher_name: str
    enrolled_at: datetime


# ================== STUDENT ROUTES (STATIC PATHS - MUST BE FIRST) ==================

@router.post("/join", response_model=dict)
async def join_classroom_by_code(
    request: JoinClassroomRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Katılım kodu ile sınıfa katılır.
    Sadece öğrenciler için.
    """
    if current_user.role != Role.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sadece öğrenciler sınıfa katılabilir"
        )

    # Sınıfı bul
    classroom = db.query(Classroom).filter(
        Classroom.join_code == request.join_code.upper(),
        Classroom.join_enabled == True,
        Classroom.is_active == True,
        Classroom.is_archived == False
    ).first()

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geçersiz katılım kodu veya sınıf kapalı"
        )

    # Aynı okul kontrolü
    if current_user.school_id != classroom.school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu sınıf farklı bir okula ait"
        )

    # Mevcut kaydı kontrol et
    existing = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.student_id == current_user.id
    ).first()

    if existing:
        if existing.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Zaten bu sınıfa kayıtlısınız"
            )
        # Yeniden aktifleştir
        existing.status = "active"
        existing.enrolled_at = datetime.utcnow()
        existing.removed_at = None
        db.commit()

        logger.info(f"Student {current_user.email} re-joined classroom {classroom.name}")

        return {
            "message": f"{classroom.name} sınıfına başarıyla katıldınız",
            "classroom_id": classroom.id,
            "classroom_name": classroom.name
        }

    # Yeni kayıt
    enrollment = StudentEnrollment(
        classroom_id=classroom.id,
        student_id=current_user.id,
    )

    db.add(enrollment)
    db.commit()

    logger.info(f"Student {current_user.email} joined classroom {classroom.name}")

    return {
        "message": f"{classroom.name} sınıfına başarıyla katıldınız",
        "classroom_id": classroom.id,
        "classroom_name": classroom.name
    }


@router.get("/enrolled", response_model=List[EnrolledClassroomResponse])
async def list_enrolled_classrooms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Öğrencinin kayıtlı olduğu sınıfları listeler.
    Sadece öğrenciler için.
    """
    if current_user.role != Role.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu sayfa sadece öğrenciler için"
        )

    enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == current_user.id,
        StudentEnrollment.status == "active"
    ).all()

    result = []
    for enrollment in enrollments:
        classroom = db.query(Classroom).filter(
            Classroom.id == enrollment.classroom_id,
            Classroom.is_active == True,
            Classroom.is_archived == False
        ).first()

        if not classroom:
            continue

        teacher = db.query(User).filter(User.id == classroom.teacher_id).first()

        result.append(EnrolledClassroomResponse(
            id=enrollment.id,
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            grade=classroom.grade,
            subject=classroom.subject,
            teacher_name=teacher.full_name if teacher else "Bilinmiyor",
            enrolled_at=enrollment.enrolled_at
        ))

    return result


@router.delete("/enrolled/{classroom_id}")
async def leave_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sınıftan ayrılır.
    Sadece öğrenciler için.
    """
    if current_user.role != Role.STUDENT.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem sadece öğrenciler için"
        )

    enrollment = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom_id,
        StudentEnrollment.student_id == current_user.id,
        StudentEnrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu sınıfa kayıtlı değilsiniz"
        )

    enrollment.status = "inactive"  # Öğrenci kendi ayrıldı
    enrollment.removed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Student {current_user.email} left classroom {classroom_id}")

    return {"message": "Sınıftan ayrıldınız"}


# ================== TEACHER ROUTES (DYNAMIC PATHS) ==================

@router.get("/{classroom_id}/students", response_model=EnrollmentListResponse)
async def list_classroom_students(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, pattern=r"^(active|inactive|removed)$")
):
    """
    Sınıftaki öğrencileri listeler.
    Öğretmen yetkisi gerektirir.
    """
    query = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id
    )

    if status_filter:
        query = query.filter(StudentEnrollment.status == status_filter)
    else:
        # Varsayılan olarak aktif olanları göster
        query = query.filter(StudentEnrollment.status == "active")

    enrollments = query.order_by(StudentEnrollment.enrolled_at.desc()).all()

    items = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.student_id).first()
        if student:
            items.append(EnrollmentResponse(
                id=enrollment.id,
                student_id=student.id,
                student_name=student.full_name,
                student_email=student.email,
                student_grade=student.grade,
                status=enrollment.status,
                enrolled_at=enrollment.enrolled_at,
                removed_at=enrollment.removed_at
            ))

    return EnrollmentListResponse(items=items, total=len(items))


@router.post("/{classroom_id}/students/{student_id}", response_model=EnrollmentResponse)
async def add_student_to_classroom(
    student_id: int,
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Öğrenciyi sınıfa ekler (öğretmen tarafından).
    Öğretmen yetkisi gerektirir.
    """
    # Öğrenciyi bul
    student = db.query(User).filter(
        User.id == student_id,
        User.school_id == current_user.school_id,
        User.role == "student"
    ).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bulunamadı veya aynı okulda değil"
        )

    # Mevcut kaydı kontrol et
    existing = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.student_id == student_id
    ).first()

    if existing:
        if existing.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Öğrenci zaten bu sınıfa kayıtlı"
            )
        # Yeniden aktifleştir
        existing.status = "active"
        existing.enrolled_at = datetime.utcnow()
        existing.removed_at = None
        db.commit()
        db.refresh(existing)

        return EnrollmentResponse(
            id=existing.id,
            student_id=student.id,
            student_name=student.full_name,
            student_email=student.email,
            student_grade=student.grade,
            status=existing.status,
            enrolled_at=existing.enrolled_at,
            removed_at=existing.removed_at
        )

    # Yeni kayıt oluştur
    enrollment = StudentEnrollment(
        classroom_id=classroom.id,
        student_id=student_id,
    )

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    logger.info(f"Student {student.email} added to classroom {classroom.name} by teacher")

    return EnrollmentResponse(
        id=enrollment.id,
        student_id=student.id,
        student_name=student.full_name,
        student_email=student.email,
        student_grade=student.grade,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
        removed_at=enrollment.removed_at
    )


@router.delete("/{classroom_id}/students/{student_id}")
async def remove_student_from_classroom(
    student_id: int,
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Öğrenciyi sınıftan çıkarır.
    Öğretmen yetkisi gerektirir.
    """
    enrollment = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bu sınıfa kayıtlı değil"
        )

    enrollment.status = "removed"
    enrollment.removed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Student {student_id} removed from classroom {classroom.name}")

    return {"message": "Öğrenci sınıftan çıkarıldı"}
