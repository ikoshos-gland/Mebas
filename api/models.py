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
    image_base64: str = Field(
        ...,
        description="Base64 encoded question image",
        max_length=10_000_000  # ~7.5MB decoded limit to prevent DoS
    )
    grade: Optional[int] = Field(None, ge=1, le=12, description="Student grade level")
    subject: Optional[str] = Field(None, description="Subject code (M, F, T...)")
    is_exam_mode: bool = Field(
        False,
        description="YKS/sınav modu: True=tüm sınıflar (9-12), False=sadece belirtilen sınıf"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID for chat history context"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                "grade": 12,
                "subject": "M",
                "is_exam_mode": True,
                "conversation_id": "abc123-def456"
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
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID for chat history context"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "question_text": "Üçgenlerde benzerlik koşullarını açıklayın.",
                "grade": 12,
                "subject": "M",
                "is_exam_mode": True,
                "conversation_id": "abc123-def456"
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


# ================== CHAT MODELS ==================

class ChatRequest(BaseModel):
    """Request for chat endpoint (unified interface)"""
    message: Optional[str] = Field(None, description="User's text message", max_length=10_000)
    image_base64: Optional[str] = Field(
        None,
        description="Base64 encoded image (optional)",
        max_length=10_000_000  # ~7.5MB decoded limit to prevent DoS
    )
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    grade: Optional[int] = Field(None, ge=1, le=12, description="Student grade level")
    subject: Optional[str] = Field(None, description="Subject code (M, F, T...)")
    is_exam_mode: bool = Field(False, description="YKS/sınav modu")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Bu konuyu açıklar mısın?",
                "session_id": "abc-123",
                "grade": 12
            }
        }
    }


class ChatResponse(BaseModel):
    """Response for chat endpoint"""
    session_id: str = Field(..., description="Session ID for continuity")
    response: str = Field(..., description="Assistant's response")
    route: str = Field(..., description="Which route was taken: new_image_analysis or follow_up_chat")
    analysis_id: Optional[str] = Field(None, description="Analysis ID if new analysis was done")
    processing_time_ms: int = Field(0, description="Processing time")


# ================== EXAM MODELS ==================

class ExamGenerateRequest(BaseModel):
    """Request for exam generation"""
    title: str = Field(default="Çalışma Sınavı", max_length=200)
    question_count: int = Field(default=10, ge=5, le=30)
    difficulty_distribution: dict = Field(
        default={"kolay": 0.3, "orta": 0.5, "zor": 0.2},
        description="Zorluk dağılımı oranları (toplam 1.0 olmalı)"
    )
    kazanim_codes: Optional[List[str]] = Field(
        None,
        description="Spesifik kazanım kodları (None = kullanıcının takip ettikleri)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "10. Sınıf Matematik Deneme",
                "question_count": 15,
                "difficulty_distribution": {"kolay": 0.2, "orta": 0.5, "zor": 0.3},
                "kazanim_codes": ["MAT.10.1.1.1", "MAT.10.1.2.3"]
            }
        }
    }


class ExamQuestionDetail(BaseModel):
    """Detail of a question in the exam"""
    file: str
    kazanim: str
    difficulty: str
    answer: Optional[str] = None


class ExamGenerateResponse(BaseModel):
    """Response for exam generation"""
    exam_id: str = Field(..., description="Unique exam ID")
    pdf_url: str = Field(..., description="Download URL for the PDF")
    kazanimlar_covered: List[str] = Field(default_factory=list)
    question_count: int
    questions: List[ExamQuestionDetail] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    skipped_kazanimlar: List[str] = Field(
        default_factory=list,
        description="Soru bulunamayan ve atlanan kazanımlar"
    )
    warning: Optional[str] = Field(
        None,
        description="Uyarı mesajı (bazı kazanımlar atlandıysa)"
    )


class ExamListItem(BaseModel):
    """Item in exam list"""
    exam_id: str
    title: str
    question_count: int
    kazanimlar_count: int
    pdf_url: str
    created_at: datetime


class ExamListResponse(BaseModel):
    """Response for listing exams"""
    exams: List[ExamListItem] = Field(default_factory=list)
    total: int = 0

