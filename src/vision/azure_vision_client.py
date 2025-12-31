"""
MEB RAG Sistemi - Azure GPT-4o Vision Client
Async görsel analizi için
"""
from openai import AsyncAzureOpenAI
from dataclasses import dataclass
from typing import Optional, List
import json
import re
import base64

from config.settings import get_settings


@dataclass
class VisionAnalysisResult:
    """Result of vision analysis on a question image"""
    extracted_text: str
    question_type: Optional[str] = None  # çoktan_seçmeli, problem, boşluk_doldurma
    topics: List[str] = None
    math_expressions: List[str] = None
    estimated_grade: Optional[int] = None
    confidence: float = 0.0
    raw_response: str = ""
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = []
        if self.math_expressions is None:
            self.math_expressions = []


class AzureVisionClient:
    """
    Async Azure GPT-4o Vision client for question image analysis.
    
    CRITICAL: Uses AsyncAzureOpenAI for non-blocking FastAPI compatibility!
    """
    
    EXTRACTION_PROMPT = """Bu bir öğrenci sorusu resmi. Lütfen analiz et:

1. **Soru Metni**: Resimdeki tüm metni çıkar. Matematik ifadelerini LaTeX formatında yaz ($x^2$ gibi).

2. **Soru Tipi**: Şunlardan biri:
   - çoktan_seçmeli
   - problem
   - boşluk_doldurma
   - doğru_yanlış
   - eşleştirme
   - grafik_yorumlama

3. **Konular**: Bu soru hangi konularla ilgili? (liste olarak)

4. **Tahmini Sınıf**: Bu soru kaçıncı sınıf seviyesine uygun? (1-12 arası, emin değilsen null)

**ÖNEMLİ**: Emin olmadığın alanlarda null döndür, tahmin yapma!

JSON formatında döndür:
{
    "extracted_text": "...",
    "question_type": "...",
    "topics": ["...", "..."],
    "math_expressions": ["$...$", "$...$"],
    "estimated_grade": 5,
    "confidence": 0.85
}"""
    
    def __init__(self, client: Optional[AsyncAzureOpenAI] = None):
        """
        Args:
            client: Optional async client. If not provided, creates one.
        """
        if client:
            self.client = client
        else:
            settings = get_settings()
            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )
        self.settings = get_settings()
    
    async def analyze_image(
        self, 
        image_base64: str,
        detail: str = "high"
    ) -> VisionAnalysisResult:
        """
        Analyze question image using GPT-4o Vision.
        
        Args:
            image_base64: Base64 encoded image string
            detail: Vision detail level ("low", "high", "auto")
            
        Returns:
            VisionAnalysisResult with extracted info
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": detail
                            }
                        },
                        {
                            "type": "text",
                            "text": self.EXTRACTION_PROMPT
                        }
                    ]
                }],
                max_tokens=2000,
                temperature=0
            )
            
            raw_content = response.choices[0].message.content
            return self._parse_response(raw_content)
            
        except Exception as e:
            print(f"Vision analysis error: {e}")
            return VisionAnalysisResult(
                extracted_text="",
                confidence=0.0,
                raw_response=str(e)
            )
    
    async def analyze_image_from_bytes(
        self, 
        image_bytes: bytes,
        detail: str = "high"
    ) -> VisionAnalysisResult:
        """
        Analyze image from bytes (for FastAPI UploadFile).
        
        Args:
            image_bytes: Raw image bytes
            detail: Vision detail level
            
        Returns:
            VisionAnalysisResult
        """
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        return await self.analyze_image(image_base64, detail)
    
    def _parse_response(self, raw_content: str) -> VisionAnalysisResult:
        """
        Parse GPT response with robust JSON extraction.
        
        CRITICAL: Handles markdown code blocks and malformed JSON!
        """
        try:
            # Step 1: Clean markdown code blocks
            cleaned = self._clean_markdown_blocks(raw_content)
            
            # Step 2: Try direct JSON parse
            data = json.loads(cleaned)
            
            return VisionAnalysisResult(
                extracted_text=data.get("extracted_text", ""),
                question_type=data.get("question_type"),
                topics=data.get("topics", []),
                math_expressions=data.get("math_expressions", []),
                estimated_grade=data.get("estimated_grade"),
                confidence=data.get("confidence", 0.0),
                raw_response=raw_content
            )
            
        except json.JSONDecodeError:
            # Fallback: Extract what we can
            return self._fallback_parse(raw_content)
    
    def _clean_markdown_blocks(self, content: str) -> str:
        """
        Remove ```json and ``` markdown wrappers.
        GPT often wraps JSON in code blocks.
        """
        # Remove ```json or ``` wrappers
        content = re.sub(r'^```(?:json)?\s*\n?', '', content.strip())
        content = re.sub(r'\n?```\s*$', '', content.strip())
        
        # Also try to find JSON object in the content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json_match.group(0)
        
        return content
    
    def _fallback_parse(self, raw_content: str) -> VisionAnalysisResult:
        """
        Fallback parsing when JSON fails.
        Extracts what information we can from the text.
        """
        # Try to extract text between quotes
        text_match = re.search(r'"extracted_text"\s*:\s*"([^"]*)"', raw_content)
        extracted_text = text_match.group(1) if text_match else raw_content[:500]
        
        # Try to find grade
        grade_match = re.search(r'"estimated_grade"\s*:\s*(\d+)', raw_content)
        grade = int(grade_match.group(1)) if grade_match else None
        
        # Try to find question type
        type_match = re.search(
            r'"question_type"\s*:\s*"(çoktan_seçmeli|problem|boşluk_doldurma|doğru_yanlış)"',
            raw_content
        )
        question_type = type_match.group(1) if type_match else None
        
        return VisionAnalysisResult(
            extracted_text=extracted_text,
            question_type=question_type,
            estimated_grade=grade,
            confidence=0.3,  # Low confidence for fallback
            raw_response=raw_content
        )
    
    async def quick_classify(self, image_base64: str) -> dict:
        """
        Quick classification without full extraction.
        
        For when you just need type/grade estimation.
        Uses low detail mode for cost savings.
        """
        quick_prompt = """Bu soru resmini hızlıca sınıflandır:
- question_type: çoktan_seçmeli/problem/boşluk_doldurma/doğru_yanlış
- estimated_grade: 1-12 arası
- subject: Matematik/Fen/Türkçe/Diğer

Sadece JSON döndür: {"question_type": "...", "estimated_grade": 5, "subject": "..."}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.settings.azure_openai_chat_deployment,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "low"  # Cost savings!
                            }
                        },
                        {"type": "text", "text": quick_prompt}
                    ]
                }],
                max_tokens=100,
                temperature=0
            )
            
            content = self._clean_markdown_blocks(response.choices[0].message.content)
            return json.loads(content)
            
        except Exception as e:
            return {"error": str(e)}
