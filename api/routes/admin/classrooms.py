"""
Platform Admin Classroom Management Routes
Admin can manage classrooms across all schools.
"""
import logging
import secrets
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.auth.deps import get_platform_admin, get_db
from src.database.models import User, Classroom, StudentEnrollment, School

logger = logging.getLogger("api.admin.classrooms")

router = APIRouter(prefix="/classrooms", tags=["Admin Classrooms"])


# ============ Schemas ============

class AdminCreateClassroom(BaseModel):
    """Schema for creating a classroom by admin"""
    name: str = Field(..., min_length=1, max_length=100)
    school_id: int
    teacher_id: int
    grade: int = Field(..., ge=1, le=12)
    subject: Optional[str] = Field(None, max_length=50)


class AdminUpdateClassroom(BaseModel):
    """Schema for updating a classroom"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    teacher_id: Optional[int] = None
    grade: Optional[int] = Field(None, ge=1, le=12)
    subject: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class ClassroomResponse(BaseModel):
    """Classroom response schema"""
    id: int
    name: str
    join_code: str
    school_id: int
    school_name: Optional[str] = None
    teacher_id: int
    teacher_name: Optional[str] = None
    grade: int
    subject: Optional[str] = None
    student_count: int = 0
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClassroomListResponse(BaseModel):
    """Paginated classroom list response"""
    items: List[ClassroomResponse]
    total: int
    page: int
    page_size: int


class StudentInClassroom(BaseModel):
    """Student info in classroom"""
    id: int
    email: str
    full_name: str
    grade: Optional[int] = None
    enrolled_at: datetime

    class Config:
        from_attributes = True


class AddStudentRequest(BaseModel):
    """Request to add student to classroom"""
    student_id: int


# ============ Endpoints ============

@router.get("", response_model=ClassroomListResponse)
async def list_classrooms(
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    school_id: Optional[int] = None,
    teacher_id: Optional[int] = None,
    grade: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """List all classrooms with filtering and pagination"""

    query = db.query(Classroom)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Classroom.name.ilike(search_term),
                Classroom.join_code.ilike(search_term)
            )
        )

    if school_id:
        query = query.filter(Classroom.school_id == school_id)

    if teacher_id:
        query = query.filter(Classroom.teacher_id == teacher_id)

    if grade:
        query = query.filter(Classroom.grade == grade)

    if is_active is not None:
        query = query.filter(Classroom.is_active == is_active)

    # Count total
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    classrooms = query.order_by(Classroom.created_at.desc()).offset(offset).limit(page_size).all()

    # Build response with related data
    items = []
    for classroom in classrooms:
        # Get school name
        school = db.query(School).filter(School.id == classroom.school_id).first()
        school_name = school.name if school else None

        # Get teacher name
        teacher = db.query(User).filter(User.id == classroom.teacher_id).first()
        teacher_name = teacher.full_name if teacher else None

        # Get student count
        student_count = db.query(StudentEnrollment).filter(
            StudentEnrollment.classroom_id == classroom.id,
            StudentEnrollment.status == "active"
        ).count()

        items.append(ClassroomResponse(
            id=classroom.id,
            name=classroom.name,
            join_code=classroom.join_code,
            school_id=classroom.school_id,
            school_name=school_name,
            teacher_id=classroom.teacher_id,
            teacher_name=teacher_name,
            grade=classroom.grade,
            subject=classroom.subject,
            student_count=student_count,
            is_active=classroom.is_active,
            created_at=classroom.created_at
        ))

    return ClassroomListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=ClassroomResponse)
async def create_classroom(
    data: AdminCreateClassroom,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Create a new classroom"""

    # Verify school exists
    school = db.query(School).filter(School.id == data.school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="Okul bulunamadi")

    # Verify teacher exists
    teacher = db.query(User).filter(
        User.id == data.teacher_id,
        User.role.in_(["teacher", "school_admin"])
    ).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Ogretmen bulunamadi")

    # Create classroom
    join_code = secrets.token_hex(4).upper()  # 8 character code

    classroom = Classroom(
        name=data.name,
        join_code=join_code,
        school_id=data.school_id,
        teacher_id=data.teacher_id,
        grade=data.grade,
        subject=data.subject,
        is_active=True
    )

    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    logger.info(f"Admin {current_user.email} created classroom: {classroom.name} (ID: {classroom.id})")

    return ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        join_code=classroom.join_code,
        school_id=classroom.school_id,
        school_name=school.name,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.full_name,
        grade=classroom.grade,
        subject=classroom.subject,
        student_count=0,
        is_active=classroom.is_active,
        created_at=classroom.created_at
    )


@router.get("/{classroom_id}", response_model=ClassroomResponse)
async def get_classroom(
    classroom_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Get classroom details"""

    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Sinif bulunamadi")

    # Get related data
    school = db.query(School).filter(School.id == classroom.school_id).first()
    teacher = db.query(User).filter(User.id == classroom.teacher_id).first()
    student_count = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).count()

    return ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        join_code=classroom.join_code,
        school_id=classroom.school_id,
        school_name=school.name if school else None,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.full_name if teacher else None,
        grade=classroom.grade,
        subject=classroom.subject,
        student_count=student_count,
        is_active=classroom.is_active,
        created_at=classroom.created_at
    )


@router.put("/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: int,
    data: AdminUpdateClassroom,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Update classroom"""

    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Sinif bulunamadi")

    # Update fields
    if data.name is not None:
        classroom.name = data.name

    if data.teacher_id is not None:
        teacher = db.query(User).filter(
            User.id == data.teacher_id,
            User.role.in_(["teacher", "school_admin"])
        ).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Ogretmen bulunamadi")
        classroom.teacher_id = data.teacher_id

    if data.grade is not None:
        classroom.grade = data.grade

    if data.subject is not None:
        classroom.subject = data.subject

    if data.is_active is not None:
        classroom.is_active = data.is_active

    db.commit()
    db.refresh(classroom)

    logger.info(f"Admin {current_user.email} updated classroom: {classroom.name} (ID: {classroom.id})")

    # Get related data
    school = db.query(School).filter(School.id == classroom.school_id).first()
    teacher = db.query(User).filter(User.id == classroom.teacher_id).first()
    student_count = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).count()

    return ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        join_code=classroom.join_code,
        school_id=classroom.school_id,
        school_name=school.name if school else None,
        teacher_id=classroom.teacher_id,
        teacher_name=teacher.full_name if teacher else None,
        grade=classroom.grade,
        subject=classroom.subject,
        student_count=student_count,
        is_active=classroom.is_active,
        created_at=classroom.created_at
    )


@router.delete("/{classroom_id}")
async def delete_classroom(
    classroom_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Delete classroom"""

    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Sinif bulunamadi")

    classroom_name = classroom.name

    # Delete enrollments first
    db.query(StudentEnrollment).filter(StudentEnrollment.classroom_id == classroom_id).delete()

    # Delete classroom
    db.delete(classroom)
    db.commit()

    logger.info(f"Admin {current_user.email} deleted classroom: {classroom_name} (ID: {classroom_id})")

    return {"message": "Sinif silindi"}


@router.get("/{classroom_id}/students", response_model=List[StudentInClassroom])
async def list_classroom_students(
    classroom_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """List students in a classroom"""

    # Verify classroom exists
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Sinif bulunamadi")

    # Get enrollments with students
    enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom_id,
        StudentEnrollment.status == "active"
    ).all()

    students = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.student_id).first()
        if student:
            students.append(StudentInClassroom(
                id=student.id,
                email=student.email,
                full_name=student.full_name,
                grade=student.grade,
                enrolled_at=enrollment.enrolled_at
            ))

    return students


@router.post("/{classroom_id}/students")
async def add_student_to_classroom(
    classroom_id: int,
    data: AddStudentRequest,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Add a student to classroom"""

    # Verify classroom exists
    classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Sinif bulunamadi")

    # Verify student exists
    student = db.query(User).filter(
        User.id == data.student_id,
        User.role == "student"
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ogrenci bulunamadi")

    # Check if already enrolled
    existing = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom_id,
        StudentEnrollment.student_id == data.student_id
    ).first()

    if existing:
        if existing.status == "active":
            raise HTTPException(status_code=400, detail="Ogrenci zaten bu sinifta")
        # Reactivate enrollment
        existing.status = "active"
        existing.enrolled_at = datetime.utcnow()
        existing.removed_at = None
        db.commit()
    else:
        # Create new enrollment
        enrollment = StudentEnrollment(
            classroom_id=classroom_id,
            student_id=data.student_id,
            status="active"
        )
        db.add(enrollment)
        db.commit()

    logger.info(f"Admin {current_user.email} added student {student.email} to classroom {classroom.name}")

    return {"message": "Ogrenci sinifa eklendi"}


@router.delete("/{classroom_id}/students/{student_id}")
async def remove_student_from_classroom(
    classroom_id: int,
    student_id: int,
    current_user: User = Depends(get_platform_admin),
    db: Session = Depends(get_db)
):
    """Remove a student from classroom"""

    # Find enrollment
    enrollment = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom_id,
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Ogrenci bu sinifta bulunamadi")

    # Soft delete - update status
    enrollment.status = "removed"
    enrollment.removed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Admin {current_user.email} removed student {student_id} from classroom {classroom_id}")

    return {"message": "Ogrenci siniftan cikarildi"}
