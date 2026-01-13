"""
Assignment CRUD Routes
Create, read, update, delete assignments
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import (
    User, Assignment, ClassAssignment, Classroom,
    StudentEnrollment, AssignmentSubmission
)
from api.auth.deps import (
    get_current_teacher,
    get_current_active_user,
    verify_teacher_owns_classroom,
    require_school_membership
)
from api.auth.permissions import Role

router = APIRouter()


# ================== SCHEMAS ==================

class AssignmentCreate(BaseModel):
    """Create assignment request"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignment_type: str = Field(default="practice")  # practice, exam, homework
    target_kazanimlar: List[str] = Field(default_factory=list)
    exam_id: Optional[str] = None
    due_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Parabol Konusu Odev",
                "description": "Parabol konusuyla ilgili sorular",
                "assignment_type": "homework",
                "target_kazanimlar": ["M.10.2.1", "M.10.2.2"],
                "due_at": "2026-01-20T23:59:00Z"
            }
        }


class AssignmentUpdate(BaseModel):
    """Update assignment request"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    assignment_type: Optional[str] = None
    target_kazanimlar: Optional[List[str]] = None
    due_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class DistributeRequest(BaseModel):
    """Distribute assignment to classrooms"""
    classroom_ids: List[int] = Field(..., min_items=1)
    due_at_override: Optional[datetime] = None


class AssignmentResponse(BaseModel):
    """Assignment response"""
    id: int
    title: str
    description: Optional[str]
    assignment_type: str
    target_kazanimlar: List[str]
    exam_id: Optional[str]
    assigned_at: datetime
    due_at: Optional[datetime]
    is_active: bool
    created_by_name: str
    classroom_count: int
    submission_count: int

    class Config:
        from_attributes = True


class AssignmentDetailResponse(AssignmentResponse):
    """Detailed assignment response with class distributions"""
    distributions: List[dict]


class StudentAssignmentResponse(BaseModel):
    """Assignment as seen by a student"""
    id: int
    title: str
    description: Optional[str]
    assignment_type: str
    target_kazanimlar: List[str]
    due_at: Optional[datetime]
    classroom_name: str
    teacher_name: str
    submission_status: str
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


# ================== TEACHER ROUTES ==================

@router.post("/", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: AssignmentCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Create a new assignment.

    - Requires teacher role
    - Must belong to a school
    """
    if not current_user.school_id and current_user.role != Role.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Odev olusturmak icin bir okula uye olmalisiniz"
        )

    # Validate assignment type
    valid_types = ["practice", "exam", "homework"]
    if data.assignment_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Gecersiz odev tipi. Gecerli tipler: {', '.join(valid_types)}"
        )

    assignment = Assignment(
        school_id=current_user.school_id,
        created_by_id=current_user.id,
        title=data.title,
        description=data.description,
        assignment_type=data.assignment_type,
        target_kazanimlar=data.target_kazanimlar,
        exam_id=data.exam_id,
        due_at=data.due_at,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        assignment_type=assignment.assignment_type,
        target_kazanimlar=assignment.target_kazanimlar or [],
        exam_id=assignment.exam_id,
        assigned_at=assignment.assigned_at,
        due_at=assignment.due_at,
        is_active=assignment.is_active,
        created_by_name=current_user.full_name,
        classroom_count=0,
        submission_count=0
    )


@router.get("/", response_model=List[AssignmentResponse])
async def list_assignments(
    assignment_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    List assignments created by the current teacher.

    - Teachers see their own assignments
    - School admins see all school assignments
    - Platform admins see all assignments
    """
    query = db.query(Assignment)

    if current_user.role == Role.PLATFORM_ADMIN.value:
        pass  # See all
    elif current_user.role == Role.SCHOOL_ADMIN.value:
        query = query.filter(Assignment.school_id == current_user.school_id)
    else:
        query = query.filter(Assignment.created_by_id == current_user.id)

    if assignment_type:
        query = query.filter(Assignment.assignment_type == assignment_type)
    if is_active is not None:
        query = query.filter(Assignment.is_active == is_active)

    # Pagination
    offset = (page - 1) * page_size
    assignments = query.order_by(Assignment.assigned_at.desc()).offset(offset).limit(page_size).all()

    results = []
    for a in assignments:
        classroom_count = db.query(func.count(ClassAssignment.id)).filter(
            ClassAssignment.assignment_id == a.id
        ).scalar()

        submission_count = db.query(func.count(AssignmentSubmission.id)).join(ClassAssignment).filter(
            ClassAssignment.assignment_id == a.id
        ).scalar()

        results.append(AssignmentResponse(
            id=a.id,
            title=a.title,
            description=a.description,
            assignment_type=a.assignment_type,
            target_kazanimlar=a.target_kazanimlar or [],
            exam_id=a.exam_id,
            assigned_at=a.assigned_at,
            due_at=a.due_at,
            is_active=a.is_active,
            created_by_name=a.created_by.full_name if a.created_by else "Bilinmiyor",
            classroom_count=classroom_count,
            submission_count=submission_count
        ))

    return results


@router.get("/{assignment_id}", response_model=AssignmentDetailResponse)
async def get_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get assignment details with distributions."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Odev bulunamadi"
        )

    # Check access
    if current_user.role == Role.PLATFORM_ADMIN.value:
        pass
    elif current_user.role == Role.SCHOOL_ADMIN.value:
        if assignment.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")
    else:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")

    # Get distributions
    distributions = []
    class_assignments = db.query(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment_id
    ).all()

    for ca in class_assignments:
        submission_count = db.query(func.count(AssignmentSubmission.id)).filter(
            AssignmentSubmission.class_assignment_id == ca.id
        ).scalar()

        distributions.append({
            "classroom_id": ca.classroom_id,
            "classroom_name": ca.classroom.name if ca.classroom else "Bilinmiyor",
            "distributed_at": ca.distributed_at.isoformat() if ca.distributed_at else None,
            "due_at": (ca.due_at_override or assignment.due_at).isoformat() if (ca.due_at_override or assignment.due_at) else None,
            "submission_count": submission_count,
            "student_count": ca.classroom.student_count if ca.classroom else 0
        })

    classroom_count = len(class_assignments)
    submission_count = db.query(func.count(AssignmentSubmission.id)).join(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment_id
    ).scalar()

    return AssignmentDetailResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        assignment_type=assignment.assignment_type,
        target_kazanimlar=assignment.target_kazanimlar or [],
        exam_id=assignment.exam_id,
        assigned_at=assignment.assigned_at,
        due_at=assignment.due_at,
        is_active=assignment.is_active,
        created_by_name=assignment.created_by.full_name if assignment.created_by else "Bilinmiyor",
        classroom_count=classroom_count,
        submission_count=submission_count,
        distributions=distributions
    )


@router.put("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Update an assignment."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Odev bulunamadi")

    # Check ownership
    if current_user.role not in [Role.PLATFORM_ADMIN.value, Role.SCHOOL_ADMIN.value]:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bu odevi duzenleme yetkiniz yok")

    # Update fields
    if data.title is not None:
        assignment.title = data.title
    if data.description is not None:
        assignment.description = data.description
    if data.assignment_type is not None:
        assignment.assignment_type = data.assignment_type
    if data.target_kazanimlar is not None:
        assignment.target_kazanimlar = data.target_kazanimlar
    if data.due_at is not None:
        assignment.due_at = data.due_at
    if data.is_active is not None:
        assignment.is_active = data.is_active

    db.commit()
    db.refresh(assignment)

    classroom_count = db.query(func.count(ClassAssignment.id)).filter(
        ClassAssignment.assignment_id == assignment.id
    ).scalar()
    submission_count = db.query(func.count(AssignmentSubmission.id)).join(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment.id
    ).scalar()

    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        description=assignment.description,
        assignment_type=assignment.assignment_type,
        target_kazanimlar=assignment.target_kazanimlar or [],
        exam_id=assignment.exam_id,
        assigned_at=assignment.assigned_at,
        due_at=assignment.due_at,
        is_active=assignment.is_active,
        created_by_name=assignment.created_by.full_name if assignment.created_by else "Bilinmiyor",
        classroom_count=classroom_count,
        submission_count=submission_count
    )


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Delete an assignment and all its distributions."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Odev bulunamadi")

    # Check ownership
    if current_user.role not in [Role.PLATFORM_ADMIN.value, Role.SCHOOL_ADMIN.value]:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bu odevi silme yetkiniz yok")

    db.delete(assignment)
    db.commit()


@router.post("/{assignment_id}/distribute", status_code=status.HTTP_201_CREATED)
async def distribute_assignment(
    assignment_id: int,
    data: DistributeRequest,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Distribute assignment to classrooms.

    - Creates ClassAssignment records
    - Creates pending submissions for all enrolled students
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Odev bulunamadi")

    # Check ownership
    if current_user.role not in [Role.PLATFORM_ADMIN.value, Role.SCHOOL_ADMIN.value]:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bu odevi dagitma yetkiniz yok")

    distributed_count = 0
    for classroom_id in data.classroom_ids:
        # Verify classroom access
        classroom = db.query(Classroom).filter(Classroom.id == classroom_id).first()
        if not classroom:
            continue

        # Check school match
        if classroom.school_id != assignment.school_id:
            continue

        # Check if already distributed
        existing = db.query(ClassAssignment).filter(
            ClassAssignment.assignment_id == assignment_id,
            ClassAssignment.classroom_id == classroom_id
        ).first()
        if existing:
            continue

        # Create class assignment
        class_assignment = ClassAssignment(
            assignment_id=assignment_id,
            classroom_id=classroom_id,
            due_at_override=data.due_at_override
        )
        db.add(class_assignment)
        db.flush()

        # Create pending submissions for enrolled students
        enrollments = db.query(StudentEnrollment).filter(
            StudentEnrollment.classroom_id == classroom_id,
            StudentEnrollment.status == "active"
        ).all()

        for enrollment in enrollments:
            submission = AssignmentSubmission(
                class_assignment_id=class_assignment.id,
                student_id=enrollment.student_id,
                status="pending"
            )
            db.add(submission)

        distributed_count += 1

    db.commit()

    return {
        "message": f"Odev {distributed_count} sinifa dagitildi",
        "distributed_count": distributed_count
    }


# ================== STUDENT ROUTES ==================

@router.get("/my", response_model=List[StudentAssignmentResponse])
async def get_my_assignments(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get assignments for the current student.

    - Returns assignments from enrolled classrooms
    - Includes submission status
    """
    if current_user.role not in [Role.STUDENT.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint sadece ogrenciler icindir"
        )

    # Get enrolled classroom IDs
    enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.student_id == current_user.id,
        StudentEnrollment.status == "active"
    ).all()

    classroom_ids = [e.classroom_id for e in enrollments]
    if not classroom_ids:
        return []

    # Get class assignments for enrolled classrooms
    query = db.query(ClassAssignment).filter(
        ClassAssignment.classroom_id.in_(classroom_ids)
    ).join(Assignment).filter(
        Assignment.is_active == True
    )

    class_assignments = query.all()

    results = []
    for ca in class_assignments:
        # Get submission for this student
        submission = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.class_assignment_id == ca.id,
            AssignmentSubmission.student_id == current_user.id
        ).first()

        submission_status = submission.status if submission else "pending"
        started_at = submission.started_at if submission else None
        submitted_at = submission.submitted_at if submission else None

        if status_filter and submission_status != status_filter:
            continue

        results.append(StudentAssignmentResponse(
            id=ca.assignment.id,
            title=ca.assignment.title,
            description=ca.assignment.description,
            assignment_type=ca.assignment.assignment_type,
            target_kazanimlar=ca.assignment.target_kazanimlar or [],
            due_at=ca.due_at_override or ca.assignment.due_at,
            classroom_name=ca.classroom.name if ca.classroom else "Bilinmiyor",
            teacher_name=ca.classroom.teacher.full_name if ca.classroom and ca.classroom.teacher else "Bilinmiyor",
            submission_status=submission_status,
            started_at=started_at,
            submitted_at=submitted_at
        ))

    return results
