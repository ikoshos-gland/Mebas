"""
MEB RAG Sistemi - Pydantic Output Models
Structured output for guaranteed JSON responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class DifficultyLevel(str, Enum):
    """Difficulty levels for educational content"""
    EASY = "kolay"
    MEDIUM = "orta"
    HARD = "zor"


class BloomLevel(str, Enum):
    """Bloom's Taxonomy levels"""
    REMEMBER = "hatırlama"
    UNDERSTAND = "anlama"
    APPLY = "uygulama"
    ANALYZE = "analiz"
    EVALUATE = "değerlendirme"
    CREATE = "yaratma"


class MatchedKazanim(BaseModel):
    """A matched kazanım from retrieval"""
    kazanim_code: str = Field(..., description="Kazanım kodu (örn: M.5.1.2.3)")
    kazanim_description: str = Field(..., description="Kazanım açıklaması")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Eşleşme skoru")
    match_reason: str = Field(..., description="Neden bu kazanım eşleşti")
    related_topics: List[str] = Field(default_factory=list, description="İlgili konular")
    bloom_level: Optional[BloomLevel] = Field(None, description="Bloom taksonomisi")


class PrerequisiteGap(BaseModel):
    """A detected prerequisite knowledge gap"""
    missing_kazanim_code: str = Field(..., description="Eksik ön koşul kazanım kodu")
    missing_kazanim_description: str = Field(..., description="Eksik kazanım açıklaması")
    importance: str = Field(..., description="Bu ön koşulun önemi")
    suggestion: str = Field(..., description="Bu açığı kapatmak için öneri")


class TextbookReference(BaseModel):
    """Reference to textbook content"""
    chapter_title: str = Field(..., description="Bölüm başlığı")
    page_range: str = Field(..., description="Sayfa aralığı")
    section_title: Optional[str] = Field(None, description="Alt bölüm başlığı")
    relevance: str = Field(..., description="Bu referansın soru ile ilişkisi")


class ImageReference(BaseModel):
    """Reference to a textbook image"""
    image_id: str = Field(..., description="Görsel ID'si")
    caption: str = Field(..., description="Görsel açıklaması")
    page_number: int = Field(..., description="Sayfa numarası")
    why_relevant: str = Field(..., description="Bu görselin neden ilgili olduğu")


class SolutionStep(BaseModel):
    """A step in the solution process"""
    step_number: int = Field(..., description="Adım numarası")
    description: str = Field(..., description="Bu adımda ne yapıldığı")
    result: Optional[str] = Field(None, description="Bu adımın sonucu (varsa)")


class AnalysisOutput(BaseModel):
    """
    Complete analysis output model.
    
    CRITICAL: Used with llm.with_structured_output() for guaranteed JSON!
    """
    # Main message to user
    summary: str = Field(
        ..., 
        description="Kullanıcıya gösterilecek ana özet mesajı"
    )
    
    # Solution
    solution_steps: List[SolutionStep] = Field(
        default_factory=list,
        description="Sorunun adım adım çözümü"
    )
    
    final_answer: Optional[str] = Field(
        None, 
        description="Sorunun nihai cevabı"
    )
    
    # Matched kazanımlar
    matched_kazanimlar: List[MatchedKazanim] = Field(
        default_factory=list,
        description="Eşleşen kazanımlar listesi"
    )
    
    # Prerequisite gaps
    prerequisite_gaps: List[PrerequisiteGap] = Field(
        default_factory=list,
        description="Tespit edilen ön koşul eksiklikleri"
    )
    
    # Textbook references
    textbook_references: List[TextbookReference] = Field(
        default_factory=list,
        description="İlgili ders kitabı bölümleri"
    )
    
    # Image references (for "See Figure X" style citations)
    image_references: List[ImageReference] = Field(
        default_factory=list,
        description="İlgili görseller"
    )
    
    # Question metadata
    detected_topics: List[str] = Field(
        default_factory=list,
        description="Soruda tespit edilen konular"
    )
    
    difficulty_estimate: Optional[DifficultyLevel] = Field(
        None,
        description="Tahmini zorluk seviyesi"
    )
    
    # Study suggestions
    study_suggestions: List[str] = Field(
        default_factory=list,
        description="Çalışma önerileri"
    )
    
    # Confidence
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Analiz güven skoru"
    )


class AnalysisRequest(BaseModel):
    """API request model"""
    question_text: Optional[str] = Field(None, description="Soru metni")
    question_image_base64: Optional[str] = Field(None, description="Base64 soru görseli")
    grade: Optional[int] = Field(None, ge=1, le=12, description="Sınıf seviyesi")
    subject: Optional[str] = Field(None, description="Ders kodu (M, F, T...)")


class AnalysisResponse(BaseModel):
    """API response model"""
    analysis_id: str = Field(..., description="Analiz ID'si")
    status: str = Field(..., description="success, partial, failed")
    output: Optional[AnalysisOutput] = Field(None, description="Analiz çıktısı")
    processing_time_ms: int = Field(0, description="İşlem süresi (ms)")
    error: Optional[str] = Field(None, description="Hata mesajı (varsa)")


class FeedbackRequest(BaseModel):
    """User feedback request"""
    analysis_id: str = Field(..., description="Analiz ID'si")
    rating: int = Field(..., ge=-1, le=1, description="-1: kötü, 0: nötr, 1: iyi")
    comment: Optional[str] = Field(None, description="Kullanıcı yorumu")
    correct_kazanim: Optional[str] = Field(None, description="Doğru kazanım (düzeltme)")
