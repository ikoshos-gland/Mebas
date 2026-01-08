"""
MEB RAG Sistemi - API Models
Request/Response models for FastAPI endpoints
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ================== REQUEST MODELS ==================

class AnalyzeImageRequest(BaseModel):
    """Request for image-based question analysis"""
    image_base64: str = Field(..., description="Base64 encoded question image")
    grade: Optional[int] = Field(None, ge=1, le=12, description="Student grade level")
    subject: Optional[str] = Field(None, description="Subject code (M, F, T...)")
    is_exam_mode: bool = Field(
        False, 
        description="YKS/sınav modu: True=tüm sınıflar (9-12), False=sadece belirtilen sınıf"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                "grade": 12,
                "subject": "M",
                "is_exam_mode": True
            }
        }
    }


class AnalyzeTextRequest(BaseModel):
    """Request for text-based question analysis"""
    question_text: str = Field(..., min_length=5, description="Question text")
    grade: Optional[int] = Field(None, ge=1, le=12, description="Student grade level")
    subject: Optional[str] = Field(None, description="Subject code (M, F, T...)")
    is_exam_mode: bool = Field(
        False, 
        description="YKS/sınav modu: True=tüm sınıflar (9-12), False=sadece belirtilen sınıf"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_text": "Üçgenlerde benzerlik koşullarını açıklayın.",
                "grade": 12,
                "subject": "M",
                "is_exam_mode": True
            }
        }
    }


class FeedbackRequest(BaseModel):
    """Request for submitting feedback"""
    analysis_id: str = Field(..., description="Analysis ID to provide feedback for")
    rating: int = Field(..., ge=-1, le=1, description="-1: bad, 0: neutral, 1: good")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")
    correct_kazanim: Optional[str] = Field(None, description="Correct kazanım code if wrong")


# ================== RESPONSE MODELS ==================

class KazanimMatch(BaseModel):
    """A matched kazanım in the response"""
    code: str
    description: str
    score: float
    grade: Optional[int] = None
    subject: Optional[str] = None
    reason: Optional[str] = None


class PrerequisiteGap(BaseModel):
    """A prerequisite gap in the response"""
    kazanim_code: str
    description: str
    importance: str
    suggestion: str


class TextbookRef(BaseModel):
    """A textbook reference"""
    chapter: Optional[str] = None
    pages: Optional[str] = None
    content: Optional[str] = None
    relevance: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response for question analysis"""
    analysis_id: str = Field(..., description="Unique analysis ID")
    status: str = Field(..., description="success, partial, failed")
    
    # Results
    summary: Optional[str] = Field(None, description="Summary message")
    teacher_explanation: Optional[str] = Field(None, description="GPT-5.2 pedagogical explanation")
    matched_kazanimlar: List[KazanimMatch] = Field(default_factory=list)
    prerequisite_gaps: List[PrerequisiteGap] = Field(default_factory=list)
    textbook_references: List[TextbookRef] = Field(default_factory=list)
    study_suggestions: List[str] = Field(default_factory=list)
    
    # Metadata
    question_text: Optional[str] = Field(None, description="Extracted/provided question")
    detected_topics: List[str] = Field(default_factory=list)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    processing_time_ms: int = Field(0, description="Processing time in milliseconds")
    
    # Error
    error: Optional[str] = Field(None, description="Error message if failed")


class FeedbackResponse(BaseModel):
    """Response for feedback submission"""
    success: bool
    message: str
    feedback_id: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int = 500
