"""
MEB RAG Sistemi - Question Analyzer
Dedicated LLM for solving questions from OCR text - completely separate from RAG
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import AzureOpenAI

from config.settings import get_settings


class QuestionAnalysis(BaseModel):
    """Structured output from question analysis"""
    question_summary: str = Field(
        description="Sorunun kısa ve anlaşılır özeti"
    )
    question_type: str = Field(
        description="Soru tipi: çoktan seçmeli, doğru-yanlış, açık uçlu, vb."
    )
    subject_area: str = Field(
        description="Konu alanı: Biyoloji, Matematik, Fizik, vb."
    )
    key_concepts: list[str] = Field(
        default_factory=list,
        description="Soruyu çözmek için gereken temel kavramlar"
    )
    solution_steps: list[str] = Field(
        default_factory=list,
        description="Adım adım çözüm"
    )
    correct_answer: str = Field(
        description="Doğru cevap (örn: 'D şıkkı' veya '42')"
    )
    explanation: str = Field(
        description="Cevabın kısa açıklaması"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Cevabın doğruluğuna güven skoru"
    )


class QuestionAnalyzer:
    """
    Dedicated LLM for analyzing and solving questions from OCR text.
    
    This component is COMPLETELY SEPARATE from RAG.
    It focuses only on understanding and solving the question.
    The result is then passed to TeacherSynthesizer for pedagogical explanation.
    """
    
    SYSTEM_PROMPT = """Sen uzman bir soru çözücüsün. Sana verilen OCR metninden çıkarılan soruyu analiz et ve çöz.

GÖREVLER:
1. Soruyu anla ve özetle
2. Sorunun tipini belirle (çoktan seçmeli, açık uçlu, vb.)
3. Hangi konu alanıyla ilgili olduğunu tespit et
4. Çözmek için gereken temel kavramları listele
5. Adım adım çöz
6. Doğru cevabı net olarak belirt
7. Cevabı kısaca açıkla

KURALLAR:
- Sadece verilen bilgilerle çalış
- Adım adım mantıksal çözüm yap
- Cevabı NET ve AÇIK belirt (örn: "D şıkkı", "Doğru", "42 cm²")
- Emin değilsen düşük confidence ver
- Türkçe yanıt ver"""

    USER_PROMPT_TEMPLATE = """## OCR'dan Çıkarılan Metin
{ocr_text}

---
Yukarıdaki soruyu analiz et ve çöz. Adım adım düşün, sonra cevabı ver."""

    def __init__(self):
        """Initialize with Azure OpenAI client"""
        settings = get_settings()
        
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        # Use the same deployment as teacher (GPT-5.2) for best quality
        self.deployment = settings.azure_openai_teacher_deployment
    
    async def analyze(self, ocr_text: str) -> Dict[str, Any]:
        """
        Analyze and solve a question from OCR text.
        
        Args:
            ocr_text: The extracted text from question image
            
        Returns:
            Dictionary with question analysis and solution
        """
        import asyncio
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            return {
                "question_summary": "Soru metni okunamadı",
                "question_type": "belirsiz",
                "subject_area": "belirsiz",
                "key_concepts": [],
                "solution_steps": [],
                "correct_answer": "Belirlenemedi",
                "explanation": "OCR metni yetersiz",
                "confidence": 0.0
            }
        
        prompt = self.USER_PROMPT_TEMPLATE.format(ocr_text=ocr_text)
        
        try:
            # Use structured output for guaranteed JSON
            from langchain_openai import AzureChatOpenAI
            
            settings = get_settings()
            llm = AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_deployment=settings.azure_openai_chat_deployment,  # Use gpt-4o for structured output
                temperature=0
            )
            
            structured_llm = llm.with_structured_output(QuestionAnalysis)
            
            result = await structured_llm.ainvoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])
            
            return result.model_dump()
            
        except Exception as e:
            # Fallback: try without structured output
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_completion_tokens=1500
                )
                
                # Parse the text response into structured format
                text_response = response.choices[0].message.content
                return self._parse_text_response(text_response, ocr_text)
                
            except Exception as e2:
                return {
                    "question_summary": ocr_text[:200] + "..." if len(ocr_text) > 200 else ocr_text,
                    "question_type": "belirsiz",
                    "subject_area": "belirsiz", 
                    "key_concepts": [],
                    "solution_steps": [],
                    "correct_answer": "Analiz edilemedi",
                    "explanation": f"Hata: {str(e2)}",
                    "confidence": 0.0
                }
    
    def analyze_sync(self, ocr_text: str) -> Dict[str, Any]:
        """Synchronous version of analyze"""
        import asyncio
        return asyncio.run(self.analyze(ocr_text))
    
    def _parse_text_response(self, text: str, original_ocr: str) -> Dict[str, Any]:
        """Parse unstructured text response into structured format"""
        # Simple extraction - look for key patterns
        lines = text.split('\n')
        
        result = {
            "question_summary": original_ocr[:200] + "..." if len(original_ocr) > 200 else original_ocr,
            "question_type": "çoktan seçmeli",
            "subject_area": "belirsiz",
            "key_concepts": [],
            "solution_steps": [],
            "correct_answer": "",
            "explanation": text[:500],
            "confidence": 0.7
        }
        
        # Try to extract correct answer
        answer_patterns = [
            "doğru cevap:", "cevap:", "sonuç:", "yanıt:",
            "doğru cevap", "cevabı", "şıkkı"
        ]
        
        for line in lines:
            line_lower = line.lower()
            for pattern in answer_patterns:
                if pattern in line_lower:
                    # Extract the answer
                    result["correct_answer"] = line.strip()
                    break
            
            # Look for step indicators
            if any(line.strip().startswith(f"{i}.") for i in range(1, 10)):
                result["solution_steps"].append(line.strip())
        
        # If no answer found, try to find A, B, C, D patterns
        if not result["correct_answer"]:
            for line in lines:
                if any(f"{letter} şıkkı" in line.lower() or f"{letter})" in line for letter in "ABCDE"):
                    result["correct_answer"] = line.strip()
                    break
        
        return result
