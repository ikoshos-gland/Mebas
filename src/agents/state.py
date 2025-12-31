"""
MEB RAG Sistemi - LangGraph State Definition
Graph state for question analysis workflow
"""
from typing import TypedDict, Optional, List, Any


class QuestionAnalysisState(TypedDict, total=False):
    """
    State for the MEB RAG question analysis workflow.
    
    CRITICAL: total=False allows partial updates!
    Nodes only need to return the fields they modify.
    
    Grade priority:
    - user_grade (if provided) ALWAYS takes precedence over ai_estimated_grade
    """
    
    # ===== INPUT =====
    # Original question (text or extracted from image)
    question_text: str
    
    # Image input (if question is an image)
    question_image_base64: Optional[str]
    
    # User-provided grade (HIGHEST PRIORITY!)
    user_grade: Optional[int]
    
    # Subject hint from user
    user_subject: Optional[str]
    
    # YKS/Exam mode flag - changes filter behavior!
    # True: grade_level le X (cumulative, for YKS prep)
    # False: grade_level eq X (exact match, for school)
    is_exam_mode: bool
    
    # ===== ANALYSIS RESULTS =====
    # Vision analysis output (Phase 5)
    vision_result: Optional[dict]
    
    # AI-estimated grade (lower priority than user_grade)
    ai_estimated_grade: Optional[int]
    
    # Detected topics
    detected_topics: List[str]
    
    # Math expressions found
    math_expressions: List[str]
    
    # Question type
    question_type: Optional[str]
    
    # ===== RETRIEVAL =====
    # Matched kazanımlar (Phase 4)
    matched_kazanimlar: List[dict]
    
    # Related textbook chunks
    related_chunks: List[dict]
    
    # Related images
    related_images: List[dict]
    
    # ===== RESPONSE =====
    # Generated response (Phase 7)
    response: Optional[dict]
    
    # Prerequisite gaps found
    prerequisite_gaps: List[dict]
    
    # ===== CONTROL =====
    # Current retry count for retrieval
    retrieval_retry_count: int
    
    # Error state
    error: Optional[str]
    
    # Processing status
    status: str  # "processing", "success", "failed", "needs_retry"
    
    # Analysis ID for tracking
    analysis_id: str


def get_effective_grade(state: QuestionAnalysisState) -> Optional[int]:
    """
    Get the effective grade, preferring user-provided over AI-estimated.
    
    Priority:
    1. user_grade (always wins if provided)
    2. ai_estimated_grade (fallback)
    3. None
    """
    if state.get("user_grade") is not None:
        return state["user_grade"]
    return state.get("ai_estimated_grade")


def get_effective_subject(state: QuestionAnalysisState) -> Optional[str]:
    """
    Get the effective subject.
    
    Priority:
    1. user_subject (if provided)
    2. Detected from topics
    3. None
    """
    if state.get("user_subject"):
        return state["user_subject"]
    
    # Try to infer from topics
    topics = state.get("detected_topics", [])
    topics_text = " ".join(topics).lower()
    
    if any(k in topics_text for k in ["matematik", "sayı", "kesir", "geometri"]):
        return "M"
    if any(k in topics_text for k in ["fizik", "kuvvet", "hareket"]):
        return "F"
    
    return None


def create_initial_state(
    question_text: str = "",
    question_image_base64: Optional[str] = None,
    user_grade: Optional[int] = None,
    user_subject: Optional[str] = None,
    is_exam_mode: bool = False,
    analysis_id: str = ""
) -> QuestionAnalysisState:
    """Create initial state with defaults"""
    import uuid
    
    return {
        "question_text": question_text,
        "question_image_base64": question_image_base64,
        "user_grade": user_grade,
        "user_subject": user_subject,
        "is_exam_mode": is_exam_mode,
        "vision_result": None,
        "ai_estimated_grade": None,
        "detected_topics": [],
        "math_expressions": [],
        "question_type": None,
        "matched_kazanimlar": [],
        "related_chunks": [],
        "related_images": [],
        "response": None,
        "prerequisite_gaps": [],
        "retrieval_retry_count": 0,
        "error": None,
        "status": "processing",
        "analysis_id": analysis_id or str(uuid.uuid4())[:8]
    }
