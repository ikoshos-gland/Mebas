"""
Assignment Submission Routes
Track and manage student submissions
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
)
from api.auth.permissions import Role

router = APIRouter()


# ================== SCHEMAS ==================

class SubmissionUpdate(BaseModel):
    """Update submission status"""
    status: Optional[str] = None  # pending, started, submitted, graded
    score: Optional[float] = None
    max_score: Optional[float] = None
    kazanimlar_progress: Optional[dict] = None


class SubmissionResponse(BaseModel):
    """Submission response"""
    id: int
    student_id: int
    student_name: str
    student_email: str
    status: str
    started_at: Optional[datetime]
    submitted_at: Optional[datetime]
    score: Optional[float]
    max_score: Optional[float]
    kazanimlar_progress: dict

    class Config:
        from_attributes = True


class SubmissionDetailResponse(SubmissionResponse):
    """Detailed submission with assignment info"""
    assignment_id: int
    assignment_title: str
    classroom_name: str
    due_at: Optional[datetime]


class SubmissionStats(BaseModel):
    """Submission statistics for an assignment"""
    total_students: int
    pending: int
    started: int
    submitted: int
    graded: int
    avg_score: Optional[float]


# ================== TEACHER ROUTES ==================

@router.get("/{assignment_id}/submissions", response_model=List[SubmissionResponse])
async def get_assignment_submissions(
    assignment_id: int,
    classroom_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Get all submissions for an assignment.

    - Teachers see submissions for their assignments
    - Can filter by classroom and status
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Odev bulunamadi")

    # Check access
    if current_user.role == Role.PLATFORM_ADMIN.value:
        pass
    elif current_user.role == Role.SCHOOL_ADMIN.value:
        if assignment.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")
    else:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")

    # Build query
    query = db.query(AssignmentSubmission).join(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment_id
    )

    if classroom_id:
        query = query.filter(ClassAssignment.classroom_id == classroom_id)

    if status_filter:
        query = query.filter(AssignmentSubmission.status == status_filter)

    submissions = query.all()

    results = []
    for s in submissions:
        student = db.query(User).filter(User.id == s.student_id).first()
        results.append(SubmissionResponse(
            id=s.id,
            student_id=s.student_id,
            student_name=student.full_name if student else "Bilinmiyor",
            student_email=student.email if student else "",
            status=s.status,
            started_at=s.started_at,
            submitted_at=s.submitted_at,
            score=s.score,
            max_score=s.max_score,
            kazanimlar_progress=s.kazanimlar_progress or {}
        ))

    return results


@router.get("/{assignment_id}/submissions/stats", response_model=SubmissionStats)
async def get_submission_stats(
    assignment_id: int,
    classroom_id: Optional[int] = None,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get submission statistics for an assignment."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Odev bulunamadi")

    # Check access
    if current_user.role == Role.PLATFORM_ADMIN.value:
        pass
    elif current_user.role == Role.SCHOOL_ADMIN.value:
        if assignment.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")
    else:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")

    # Build query
    query = db.query(AssignmentSubmission).join(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment_id
    )

    if classroom_id:
        query = query.filter(ClassAssignment.classroom_id == classroom_id)

    submissions = query.all()

    total = len(submissions)
    pending = sum(1 for s in submissions if s.status == "pending")
    started = sum(1 for s in submissions if s.status == "started")
    submitted = sum(1 for s in submissions if s.status == "submitted")
    graded = sum(1 for s in submissions if s.status == "graded")

    # Calculate average score for graded submissions
    graded_scores = [s.score for s in submissions if s.status == "graded" and s.score is not None]
    avg_score = sum(graded_scores) / len(graded_scores) if graded_scores else None

    return SubmissionStats(
        total_students=total,
        pending=pending,
        started=started,
        submitted=submitted,
        graded=graded,
        avg_score=avg_score
    )


@router.put("/submissions/{submission_id}", response_model=SubmissionResponse)
async def update_submission_teacher(
    submission_id: int,
    data: SubmissionUpdate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Update a submission (teacher grading).

    - Set status to 'graded'
    - Set score
    """
    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Teslim bulunamadi")

    # Get assignment for access check
    class_assignment = submission.class_assignment
    assignment = class_assignment.assignment

    # Check access
    if current_user.role == Role.PLATFORM_ADMIN.value:
        pass
    elif current_user.role == Role.SCHOOL_ADMIN.value:
        if assignment.school_id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Erisim reddedildi")
    else:
        if assignment.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="Bu teslimi guncelleme yetkiniz yok")

    # Update fields
    if data.status is not None:
        valid_statuses = ["pending", "started", "submitted", "graded"]
        if data.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Gecersiz durum")
        submission.status = data.status

    if data.score is not None:
        submission.score = data.score
    if data.max_score is not None:
        submission.max_score = data.max_score
    if data.kazanimlar_progress is not None:
        submission.kazanimlar_progress = data.kazanimlar_progress

    db.commit()
    db.refresh(submission)

    student = db.query(User).filter(User.id == submission.student_id).first()

    return SubmissionResponse(
        id=submission.id,
        student_id=submission.student_id,
        student_name=student.full_name if student else "Bilinmiyor",
        student_email=student.email if student else "",
        status=submission.status,
        started_at=submission.started_at,
        submitted_at=submission.submitted_at,
        score=submission.score,
        max_score=submission.max_score,
        kazanimlar_progress=submission.kazanimlar_progress or {}
    )


# ================== STUDENT ROUTES ==================

@router.post("/submissions/{submission_id}/start")
async def start_assignment(
    submission_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark assignment as started by the student.
    """
    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id,
        AssignmentSubmission.student_id == current_user.id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Teslim bulunamadi")

    if submission.status != "pending":
        raise HTTPException(status_code=400, detail="Bu odev zaten baslatilmis")

    submission.status = "started"
    submission.started_at = datetime.utcnow()
    db.commit()

    return {"message": "Odev baslatildi", "status": "started"}


@router.post("/submissions/{submission_id}/submit")
async def submit_assignment(
    submission_id: int,
    kazanimlar_progress: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Submit an assignment (student).
    """
    submission = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.id == submission_id,
        AssignmentSubmission.student_id == current_user.id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Teslim bulunamadi")

    if submission.status == "submitted":
        raise HTTPException(status_code=400, detail="Bu odev zaten teslim edilmis")

    if submission.status == "graded":
        raise HTTPException(status_code=400, detail="Bu odev zaten notlanmis")

    submission.status = "submitted"
    submission.submitted_at = datetime.utcnow()

    if kazanimlar_progress:
        submission.kazanimlar_progress = kazanimlar_progress

    db.commit()

    return {"message": "Odev teslim edildi", "status": "submitted"}


@router.get("/submissions/my/{assignment_id}", response_model=SubmissionDetailResponse)
async def get_my_submission(
    assignment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the current student's submission for an assignment.
    """
    # Find the submission
    submission = db.query(AssignmentSubmission).join(ClassAssignment).filter(
        ClassAssignment.assignment_id == assignment_id,
        AssignmentSubmission.student_id == current_user.id
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Bu odev icin teslim bulunamadi")

    class_assignment = submission.class_assignment
    assignment = class_assignment.assignment
    classroom = class_assignment.classroom

    return SubmissionDetailResponse(
        id=submission.id,
        student_id=submission.student_id,
        student_name=current_user.full_name,
        student_email=current_user.email,
        status=submission.status,
        started_at=submission.started_at,
        submitted_at=submission.submitted_at,
        score=submission.score,
        max_score=submission.max_score,
        kazanimlar_progress=submission.kazanimlar_progress or {},
        assignment_id=assignment.id,
        assignment_title=assignment.title,
        classroom_name=classroom.name if classroom else "Bilinmiyor",
        due_at=class_assignment.due_at_override or assignment.due_at
    )
