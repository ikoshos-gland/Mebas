"""
Progress routes - Kazanım ilerleme takibi
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from api.auth.deps import get_current_active_user
from src.database.db import get_db
from src.database.models import User, UserKazanimProgress, Kazanim, kazanim_prerequisites
import logging

logger = logging.getLogger("api.progress")

router = APIRouter(prefix="/users/me/progress", tags=["Progress"])


# ================== SCHEMAS ==================

class KazanimProgressResponse(BaseModel):
    """Single kazanim progress item"""
    kazanim_code: str
    kazanim_description: str
    status: str  # tracked, in_progress, understood
    initial_confidence_score: float
    understanding_confidence: Optional[float] = None
    tracked_at: datetime
    understood_at: Optional[datetime] = None
    grade: Optional[int] = None
    subject: Optional[str] = None

    class Config:
        from_attributes = True


class ProgressListResponse(BaseModel):
    """Paginated progress list"""
    items: List[KazanimProgressResponse]
    total: int
    understood_count: int
    tracked_count: int
    in_progress_count: int


class TrackKazanimRequest(BaseModel):
    """Request to track a kazanim"""
    kazanim_code: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    conversation_id: Optional[str] = None


class MarkUnderstoodRequest(BaseModel):
    """Request to mark kazanim as understood"""
    understanding_signals: List[str] = Field(default_factory=list)
    understanding_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ProgressStatsResponse(BaseModel):
    """Progress statistics"""
    total_tracked: int
    total_understood: int
    in_progress_count: int
    this_week_understood: int
    streak_days: int
    by_subject: dict = {}
    by_grade: dict = {}


class RecommendationResponse(BaseModel):
    """Prerequisite recommendation"""
    kazanim_code: str
    kazanim_description: str
    grade: int
    reason: str
    priority: str  # critical, important, helpful
    related_to: List[str] = Field(default_factory=list)


# ================== HELPER FUNCTIONS ==================

def get_kazanim_info(db: Session, kazanim_code: str) -> dict:
    """Get kazanim details from database or Azure Search"""
    kazanim = db.query(Kazanim).filter(Kazanim.code == kazanim_code).first()
    if kazanim:
        return {
            "description": kazanim.description or "",
            "grade": kazanim.grade,
            "subject": kazanim.subject.name if kazanim.subject else None
        }

    # Fallback: extract grade from code (e.g., M.9.1.2.3 -> 9)
    parts = kazanim_code.split(".")
    grade = None
    if len(parts) >= 2:
        try:
            grade = int(parts[1])
        except ValueError:
            pass

    return {
        "description": f"Kazanım: {kazanim_code}",
        "grade": grade,
        "subject": None
    }


def calculate_streak(db: Session, user_id: int) -> int:
    """Calculate study streak days"""
    # Get dates with understood kazanımlar
    understood_dates = db.query(
        func.date(UserKazanimProgress.understood_at)
    ).filter(
        UserKazanimProgress.user_id == user_id,
        UserKazanimProgress.status == "understood",
        UserKazanimProgress.understood_at.isnot(None)
    ).distinct().order_by(
        func.date(UserKazanimProgress.understood_at).desc()
    ).all()

    if not understood_dates:
        return 0

    streak = 0
    today = datetime.utcnow().date()
    expected_date = today

    for (date_val,) in understood_dates:
        if date_val == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        elif date_val < expected_date:
            break

    return streak


# ================== ROUTES ==================

@router.get("", response_model=ProgressListResponse)
async def get_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    grade: Optional[int] = Query(None, ge=1, le=12),
    subject: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get user's kazanim progress for panel display.
    Returns paginated list with counts.
    """
    # Base query
    query = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id
    )

    # Apply filters
    if status_filter:
        query = query.filter(UserKazanimProgress.status == status_filter)

    # Get total counts
    total = query.count()
    understood_count = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "understood"
    ).count()
    tracked_count = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "tracked"
    ).count()
    in_progress_count = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "in_progress"
    ).count()

    # Get items with pagination
    progress_items = query.order_by(
        UserKazanimProgress.tracked_at.desc()
    ).offset(offset).limit(limit).all()

    # Enrich with kazanim details
    items = []
    for item in progress_items:
        kazanim_info = get_kazanim_info(db, item.kazanim_code)

        # Apply grade/subject filters after enrichment
        if grade and kazanim_info.get("grade") != grade:
            continue
        if subject and kazanim_info.get("subject") != subject:
            continue

        items.append(KazanimProgressResponse(
            kazanim_code=item.kazanim_code,
            kazanim_description=kazanim_info["description"],
            status=item.status,
            initial_confidence_score=item.initial_confidence_score or 0.0,
            understanding_confidence=item.understanding_confidence,
            tracked_at=item.tracked_at,
            understood_at=item.understood_at,
            grade=kazanim_info["grade"],
            subject=kazanim_info["subject"]
        ))

    return ProgressListResponse(
        items=items,
        total=total,
        understood_count=understood_count,
        tracked_count=tracked_count,
        in_progress_count=in_progress_count
    )


@router.post("/track", response_model=KazanimProgressResponse)
async def track_kazanim(
    request: TrackKazanimRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Track a new kazanim (called automatically from chat).
    Idempotent - won't duplicate if already tracked.
    """
    # Check if already tracked
    existing = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.kazanim_code == request.kazanim_code
    ).first()

    if existing:
        # Return existing without error
        kazanim_info = get_kazanim_info(db, existing.kazanim_code)
        return KazanimProgressResponse(
            kazanim_code=existing.kazanim_code,
            kazanim_description=kazanim_info["description"],
            status=existing.status,
            initial_confidence_score=existing.initial_confidence_score or 0.0,
            understanding_confidence=existing.understanding_confidence,
            tracked_at=existing.tracked_at,
            understood_at=existing.understood_at,
            grade=kazanim_info["grade"],
            subject=kazanim_info["subject"]
        )

    # Create new progress entry
    progress = UserKazanimProgress(
        user_id=current_user.id,
        kazanim_code=request.kazanim_code,
        status="tracked",
        initial_confidence_score=request.confidence_score,
        source_conversation_id=request.conversation_id,
        tracked_at=datetime.utcnow()
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)

    logger.info(f"Kazanim tracked: {current_user.email} -> {request.kazanim_code}")

    kazanim_info = get_kazanim_info(db, progress.kazanim_code)
    return KazanimProgressResponse(
        kazanim_code=progress.kazanim_code,
        kazanim_description=kazanim_info["description"],
        status=progress.status,
        initial_confidence_score=progress.initial_confidence_score or 0.0,
        understanding_confidence=progress.understanding_confidence,
        tracked_at=progress.tracked_at,
        understood_at=progress.understood_at,
        grade=kazanim_info["grade"],
        subject=kazanim_info["subject"]
    )


@router.put("/{kazanim_code}/understood", response_model=KazanimProgressResponse)
async def mark_understood(
    kazanim_code: str,
    request: MarkUnderstoodRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a kazanim as understood (called by AI detection or manually).
    """
    progress = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.kazanim_code == kazanim_code
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kazanım takipte değil: {kazanim_code}"
        )

    # Update status
    progress.status = "understood"
    progress.understanding_confidence = request.understanding_confidence
    progress.understanding_signals = request.understanding_signals
    progress.understood_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)

    logger.info(f"Kazanim understood: {current_user.email} -> {kazanim_code}")

    kazanim_info = get_kazanim_info(db, progress.kazanim_code)
    return KazanimProgressResponse(
        kazanim_code=progress.kazanim_code,
        kazanim_description=kazanim_info["description"],
        status=progress.status,
        initial_confidence_score=progress.initial_confidence_score or 0.0,
        understanding_confidence=progress.understanding_confidence,
        tracked_at=progress.tracked_at,
        understood_at=progress.understood_at,
        grade=kazanim_info["grade"],
        subject=kazanim_info["subject"]
    )


@router.put("/{kazanim_code}/in-progress", response_model=KazanimProgressResponse)
async def mark_in_progress(
    kazanim_code: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a kazanim as in-progress (actively studying).
    """
    progress = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.kazanim_code == kazanim_code
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kazanım takipte değil: {kazanim_code}"
        )

    progress.status = "in_progress"
    db.commit()
    db.refresh(progress)

    kazanim_info = get_kazanim_info(db, progress.kazanim_code)
    return KazanimProgressResponse(
        kazanim_code=progress.kazanim_code,
        kazanim_description=kazanim_info["description"],
        status=progress.status,
        initial_confidence_score=progress.initial_confidence_score or 0.0,
        understanding_confidence=progress.understanding_confidence,
        tracked_at=progress.tracked_at,
        understood_at=progress.understood_at,
        grade=kazanim_info["grade"],
        subject=kazanim_info["subject"]
    )


@router.get("/stats", response_model=ProgressStatsResponse)
async def get_progress_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for dashboard.
    """
    # Count by status
    total_tracked = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id
    ).count()

    total_understood = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "understood"
    ).count()

    in_progress_count = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "in_progress"
    ).count()

    # This week understood
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week_understood = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status == "understood",
        UserKazanimProgress.understood_at >= week_ago
    ).count()

    # Calculate streak
    streak_days = calculate_streak(db, current_user.id)

    # Group by subject and grade (from kazanim codes)
    progress_items = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id
    ).all()

    by_subject = {}
    by_grade = {}

    for item in progress_items:
        kazanim_info = get_kazanim_info(db, item.kazanim_code)

        # By subject
        subject = kazanim_info.get("subject") or "Diğer"
        if subject not in by_subject:
            by_subject[subject] = {"tracked": 0, "in_progress": 0, "understood": 0}
        by_subject[subject][item.status] = by_subject[subject].get(item.status, 0) + 1

        # By grade
        grade = kazanim_info.get("grade")
        if grade:
            if grade not in by_grade:
                by_grade[grade] = {"tracked": 0, "in_progress": 0, "understood": 0}
            by_grade[grade][item.status] = by_grade[grade].get(item.status, 0) + 1

    return ProgressStatsResponse(
        total_tracked=total_tracked,
        total_understood=total_understood,
        in_progress_count=in_progress_count,
        this_week_understood=this_week_understood,
        streak_days=streak_days,
        by_subject=by_subject,
        by_grade=by_grade
    )


@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, le=20)
):
    """
    Get prerequisite recommendations based on tracked kazanımlar.
    Returns kazanımlar that are prerequisites for tracked items but not yet understood.
    """
    # Get user's tracked and in-progress kazanımlar (not yet understood)
    tracked_items = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.status.in_(["tracked", "in_progress"])
    ).all()

    if not tracked_items:
        return []

    tracked_codes = [item.kazanim_code for item in tracked_items]

    # Get understood codes to exclude
    understood_codes = set(
        item.kazanim_code for item in db.query(UserKazanimProgress).filter(
            UserKazanimProgress.user_id == current_user.id,
            UserKazanimProgress.status == "understood"
        ).all()
    )

    # Find prerequisites using the kazanim_prerequisites table
    recommendations = []
    prereq_count = {}  # Count how many tracked items need each prereq

    for code in tracked_codes:
        kazanim = db.query(Kazanim).filter(Kazanim.code == code).first()
        if not kazanim:
            continue

        for prereq in kazanim.prerequisites:
            prereq_code = prereq.code

            # Skip if already understood or already tracking
            if prereq_code in understood_codes or prereq_code in tracked_codes:
                continue

            # Count how many tracked items need this prereq
            if prereq_code not in prereq_count:
                prereq_count[prereq_code] = {
                    "count": 0,
                    "related_to": [],
                    "kazanim": prereq
                }
            prereq_count[prereq_code]["count"] += 1
            prereq_count[prereq_code]["related_to"].append(code)

    # Build recommendations with priority
    for prereq_code, data in prereq_count.items():
        kazanim = data["kazanim"]
        count = data["count"]

        # Determine priority
        if count >= 3:
            priority = "critical"
            reason = f"{count} takipteki kazanım için kritik ön koşul"
        elif count >= 2:
            priority = "important"
            reason = f"{count} takipteki kazanım için önemli"
        else:
            priority = "helpful"
            reason = "İlgili kazanım için faydalı"

        recommendations.append(RecommendationResponse(
            kazanim_code=prereq_code,
            kazanim_description=kazanim.description or f"Kazanım: {prereq_code}",
            grade=kazanim.grade or 0,
            reason=reason,
            priority=priority,
            related_to=data["related_to"][:3]  # Limit related items shown
        ))

    # Sort by priority (critical > important > helpful) then by count
    priority_order = {"critical": 0, "important": 1, "helpful": 2}
    recommendations.sort(key=lambda x: (priority_order.get(x.priority, 3), -len(x.related_to)))

    return recommendations[:limit]


@router.delete("/{kazanim_code}")
async def remove_progress(
    kazanim_code: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a kazanim from tracking.
    """
    progress = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == current_user.id,
        UserKazanimProgress.kazanim_code == kazanim_code
    ).first()

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kazanım takipte değil: {kazanim_code}"
        )

    db.delete(progress)
    db.commit()

    logger.info(f"Kazanim removed from tracking: {current_user.email} -> {kazanim_code}")

    return {"message": f"Kazanım takipten kaldırıldı: {kazanim_code}"}
