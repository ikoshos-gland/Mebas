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


class MatchType(str, Enum):
    """Type of kazanım match"""
    PRIMARY = "primary"
    ALTERNATIVE = "alternative"


class QuestionType(str, Enum):
    """Type of question for curriculum alignment"""
    MULTIPLE_CHOICE = "multiple_choice"
    FIND_WRONG = "find_wrong"
    OPEN_ENDED = "open_ended"
    CALCULATION = "calculation"
    TRUE_FALSE = "true_false"
    MATCHING = "matching"


class QueryUnderstanding(BaseModel):
    """
    LLM-based query understanding output for curriculum alignment.

    SOTA Pre-Retrieval Query Understanding:
    Bridges semantic gap between user question and curriculum terminology.
    """

    # Ana konu (MEB müfredat terminolojisi)
    primary_topic: str = Field(
        ...,
        description="Ana konu - MEB müfredat terminolojisi ile (örn: Dolaşım Sistemi, Hücre Bölünmesi)"
    )

    # Anahtar kavramlar (arama için kritik) - MAX 5!
    key_concepts: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="EN KRİTİK 3-5 anahtar kavram (örn: kalp, kapakçık, biküspit). Fazla değil!"
    )

    # Ders tahmini
    inferred_subject: Optional[str] = Field(
        default=None,
        description="Tespit edilen ders kodu (BİY, FİZ, KİM, MAT)"
    )

    # Sınıf tahmini
    inferred_grade: Optional[int] = Field(
        default=None,
        ge=9,
        le=12,
        description="Bu konu hangi sınıfta öğretiliyor (9-12)"
    )

    # Zenginleştirilmiş sorgu (retrieval için)
    enriched_query: str = Field(
        ...,
        description="Anahtar kavramlarla zenginleştirilmiş arama sorgusu"
    )

    # Soru tipi
    question_type: Optional[QuestionType] = Field(
        default=None,
        description="Soru tipi: multiple_choice, find_wrong, open_ended, calculation"
    )

    # Güven skoru
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Analiz güven skoru"
    )


class MatchedKazanim(BaseModel):
    """A matched kazanım from retrieval"""
    kazanim_code: str = Field(..., description="Kazanım kodu (örn: M.5.1.2.3)")
    kazanim_description: str = Field(..., description="Kazanım açıklaması")
    match_score: float = Field(..., ge=0.0, le=1.0, description="Eşleşme skoru")
    match_reason: str = Field(..., description="Neden bu kazanım eşleşti")
    related_topics: List[str] = Field(default_factory=list, description="İlgili konular")
    bloom_level: Optional[BloomLevel] = Field(None, description="Bloom taksonomisi")
    match_type: MatchType = Field(MatchType.PRIMARY, description="Eşleşme türü (ana veya alternatif)")


class PrerequisiteGap(BaseModel):
    """A detected prerequisite knowledge gap"""
    missing_kazanim_code: str = Field(..., description="Eksik ön koşul kazanım kodu")
    missing_kazanim_description: str = Field(..., description="Eksik kazanım açıklaması")
    importance: str = Field(..., description="Bu ön koşulun önemi")
    suggestion: str = Field(..., description="Bu açığı kapatmak için öneri")


class TextbookReference(BaseModel):
    """Reference to textbook content with full hierarchy"""
    textbook_name: str = Field(..., description="Kitap adı (örn: Biyoloji 9)")
    chapter_title: str = Field(..., description="Bölüm/Ünite başlığı")
    page_range: str = Field(..., description="Sayfa aralığı (örn: 45-47)")
    section_title: Optional[str] = Field(None, description="Alt bölüm başlığı")
    content_preview: Optional[str] = Field(None, description="İçerik önizlemesi (ilk 200 karakter)")
    relevance: str = Field(..., description="Bu referansın soru ile ilişkisi")
    full_hierarchy: str = Field(..., description="Tam hiyerarşi: Kitap > Ünite > Konu > Sayfa")


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


class RelationshipType(str, Enum):
    """Types of relationships between kazanımlar"""
    PREREQUISITE = "prerequisite"  # Biri diğerinin ön koşulu
    PARALLEL = "parallel"  # Aynı anda öğrenilebilir
    EXTENSION = "extension"  # Biri diğerinin genişlemesi
    APPLICATION = "application"  # Biri diğerinin pratik uygulaması


class LearningPathItem(BaseModel):
    """A step in the learning path"""
    kazanim_code: str = Field(..., description="Kazanım kodu")
    kazanim_title: str = Field(..., description="Kazanım başlığı")
    order: int = Field(..., ge=1, description="Öğrenme sırası (1 = ilk öğrenilecek)")
    reason: str = Field(..., description="Neden bu sırada öğrenmeli")
    estimated_hours: Optional[float] = Field(None, description="Tahmini çalışma süresi (saat)")


class InterdisciplinarySynthesis(BaseModel):
    """Synthesis of related kazanımlar with learning path suggestions"""
    related_kazanimlar: List[str] = Field(
        default_factory=list,
        description="İlişkili kazanım kodları listesi"
    )
    relationship_type: RelationshipType = Field(
        ...,
        description="İlişki türü: prerequisite, parallel, extension, application"
    )
    synthesis_summary: str = Field(
        ...,
        description="Kazanımlar arası ilişki özeti ve sentez"
    )
    key_concepts: List[str] = Field(
        default_factory=list,
        description="Ortak kilit kavramlar"
    )
    learning_path: List[LearningPathItem] = Field(
        default_factory=list,
        description="Önerilen öğrenme sırası"
    )
    study_tips: List[str] = Field(
        default_factory=list,
        description="Çalışma önerileri"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Sentez güven skoru"
    )


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

    # Interdisciplinary synthesis (learning path suggestions)
    interdisciplinary_synthesis: Optional[InterdisciplinarySynthesis] = Field(
        None,
        description="İlişkili kazanımlar sentezi ve öğrenme yolu önerisi"
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
