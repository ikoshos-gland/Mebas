"""
MEB RAG Sistemi - Feedback Routes
User feedback endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from api.models import FeedbackRequest, FeedbackResponse
from src.database.db import get_db
from src.database.models import Feedback


router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Submit feedback for an analysis.
    
    Helps improve the system by providing user feedback
    on the quality of kazanım matches.
    """
    try:
        # Create feedback record
        feedback = Feedback(
            analysis_id=request.analysis_id,
            rating=request.rating,
            comment=request.comment,
            correct_kazanim=request.correct_kazanim,
            question_text="",  # Could be populated if we store analysis
            matched_kazanim=""
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return FeedbackResponse(
            success=True,
            message="Geri bildiriminiz alındı, teşekkürler!",
            feedback_id=feedback.id
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_feedback_stats(db: Session = Depends(get_db)):
    """
    Get feedback statistics.
    
    Returns aggregated feedback data for monitoring.
    """
    try:
        total = db.query(Feedback).count()
        positive = db.query(Feedback).filter(Feedback.rating == 1).count()
        negative = db.query(Feedback).filter(Feedback.rating == -1).count()
        neutral = db.query(Feedback).filter(Feedback.rating == 0).count()
        
        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "satisfaction_rate": positive / total if total > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
