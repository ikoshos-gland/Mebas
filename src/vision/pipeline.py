"""
MEB RAG Sistemi - Question Analysis Pipeline
Görsel soru analizi iş akışı
"""
from dataclasses import dataclass
from typing import Optional, Union
from pathlib import Path

from src.vision.azure_vision_client import AzureVisionClient, VisionAnalysisResult
from src.vision.preprocessor import ImagePreprocessor


@dataclass
class QuestionAnalysisInput:
    """Input for question analysis"""
    image_bytes: Optional[bytes] = None
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    user_grade: Optional[int] = None  # User-provided grade (takes precedence!)
    subject_hint: Optional[str] = None


@dataclass
class QuestionAnalysisOutput:
    """Complete analysis output for a question image"""
    # From vision
    extracted_text: str
    question_type: Optional[str] = None
    topics: list = None
    math_expressions: list = None
    
    # Grade (user-provided takes precedence over AI estimate)
    grade: Optional[int] = None
    grade_source: str = "unknown"  # "user", "ai", "default"
    
    # For RAG
    subject: Optional[str] = None
    confidence: float = 0.0
    
    # Debug
    raw_response: str = ""
    preprocessing_applied: bool = False
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []
        if self.math_expressions is None:
            self.math_expressions = []


class QuestionAnalysisPipeline:
    """
    Full pipeline for analyzing question images.
    
    Flow:
    1. Preprocess image (enhance for OCR)
    2. Send to GPT-4o Vision
    3. Parse and structure response
    4. Apply user overrides (grade)
    """
    
    def __init__(
        self, 
        vision_client: Optional[AzureVisionClient] = None,
        preprocessor: Optional[ImagePreprocessor] = None
    ):
        self.vision_client = vision_client or AzureVisionClient()
        self.preprocessor = preprocessor or ImagePreprocessor()
    
    async def analyze(
        self, 
        input_data: QuestionAnalysisInput,
        preprocess: bool = True,
        detail: str = "high"
    ) -> QuestionAnalysisOutput:
        """
        Analyze a question image.
        
        Args:
            input_data: Question input with image and optional hints
            preprocess: Whether to enhance image before analysis
            detail: Vision detail level ("low", "high", "auto")
            
        Returns:
            QuestionAnalysisOutput with all extracted info
        """
        # Step 1: Get image bytes
        image_bytes = await self._get_image_bytes(input_data)
        
        if not image_bytes:
            return QuestionAnalysisOutput(
                extracted_text="",
                confidence=0.0,
                raw_response="No image provided"
            )
        
        # Step 2: Preprocess if requested
        preprocessing_applied = False
        if preprocess:
            try:
                image_bytes, image_base64 = self.preprocessor.enhance_from_bytes(image_bytes)
                preprocessing_applied = True
            except Exception as e:
                # If preprocessing fails, use original
                import base64
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        else:
            import base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Step 3: Send to Vision API
        vision_result = await self.vision_client.analyze_image(image_base64, detail)
        
        # Step 4: Determine grade (user-provided takes precedence!)
        grade, grade_source = self._determine_grade(input_data, vision_result)
        
        # Step 5: Build output
        return QuestionAnalysisOutput(
            extracted_text=vision_result.extracted_text,
            question_type=vision_result.question_type,
            topics=vision_result.topics,
            math_expressions=vision_result.math_expressions,
            grade=grade,
            grade_source=grade_source,
            subject=input_data.subject_hint or self._infer_subject(vision_result),
            confidence=vision_result.confidence,
            raw_response=vision_result.raw_response,
            preprocessing_applied=preprocessing_applied
        )
    
    async def analyze_from_bytes(
        self,
        image_bytes: bytes,
        user_grade: Optional[int] = None,
        subject_hint: Optional[str] = None,
        preprocess: bool = True
    ) -> QuestionAnalysisOutput:
        """
        Convenience method for FastAPI uploads.
        
        Args:
            image_bytes: Raw image bytes from UploadFile
            user_grade: User-provided grade level
            subject_hint: Optional subject hint
            preprocess: Whether to enhance image
            
        Returns:
            QuestionAnalysisOutput
        """
        input_data = QuestionAnalysisInput(
            image_bytes=image_bytes,
            user_grade=user_grade,
            subject_hint=subject_hint
        )
        return await self.analyze(input_data, preprocess=preprocess)
    
    async def quick_analyze(
        self,
        image_bytes: bytes
    ) -> dict:
        """
        Quick analysis for grade/type only.
        Uses low detail mode for cost savings.
        
        Returns:
            Dict with question_type, estimated_grade, subject
        """
        import base64
        
        # Light preprocessing
        try:
            _, image_base64 = self.preprocessor.compress_for_api(image_bytes, 200)
        except Exception:
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        return await self.vision_client.quick_classify(image_base64)
    
    async def _get_image_bytes(
        self, 
        input_data: QuestionAnalysisInput
    ) -> Optional[bytes]:
        """Get image bytes from various input sources"""
        if input_data.image_bytes:
            return input_data.image_bytes
        
        if input_data.image_path:
            path = Path(input_data.image_path)
            if path.exists():
                return path.read_bytes()
        
        if input_data.image_base64:
            import base64
            return base64.b64decode(input_data.image_base64)
        
        return None
    
    def _determine_grade(
        self, 
        input_data: QuestionAnalysisInput,
        vision_result: VisionAnalysisResult
    ) -> tuple:
        """
        Determine final grade, preferring user input.
        
        Priority:
        1. User-provided grade (always wins!)
        2. AI-estimated grade (if confident)
        3. Default (None)
        """
        # User grade takes absolute precedence
        if input_data.user_grade is not None:
            return input_data.user_grade, "user"
        
        # AI estimate as fallback
        if vision_result.estimated_grade is not None and vision_result.confidence >= 0.5:
            return vision_result.estimated_grade, "ai"
        
        # No confident grade
        return None, "unknown"
    
    def _infer_subject(self, vision_result: VisionAnalysisResult) -> Optional[str]:
        """Infer subject from topics or math expressions"""
        topics_lower = [t.lower() for t in vision_result.topics]
        
        # Math indicators
        math_keywords = ["matematik", "sayı", "kesir", "geometri", "üçgen", "denklem"]
        if vision_result.math_expressions or any(k in " ".join(topics_lower) for k in math_keywords):
            return "M"  # Matematik
        
        # Science indicators
        science_keywords = ["fizik", "kuvvet", "hareket", "enerji", "ışık"]
        if any(k in " ".join(topics_lower) for k in science_keywords):
            return "F"  # Fizik
        
        return None
