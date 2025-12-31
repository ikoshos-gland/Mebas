"""
MEB RAG Sistemi - Response Generator
LLM-based response generation with structured output
"""
from typing import Optional, List, Dict, Any
from langchain_openai import AzureChatOpenAI

from config.settings import get_settings
from src.rag.output_models import AnalysisOutput, MatchedKazanim, PrerequisiteGap


class ResponseGenerator:
    """
    Generates structured responses using LLM with Pydantic output.
    
    CRITICAL: Uses llm.with_structured_output() for guaranteed JSON!
    """
    
    SYSTEM_PROMPT = """Sen bir MEB müfredat uzmanısın. Öğrenci sorularını analiz edip 
kazanımlarla eşleştiriyorsun.

KURALLAR:
1. Sadece verilen kazanımları kullan, uydurma!
2. Ön koşul eksikliği varsa mutlaka belirt
3. Ders kitabından referans verirken sayfa numarası kullan
4. Türkçe yanıt ver
5. Özet mesajı öğrenci için anlaşılır olmalı"""

    ANALYSIS_PROMPT = """## Soru
{question_text}

## Tespit Edilen Konular
{topics}

## Eşleşen Kazanımlar (Retrieval Sonuçları)
{kazanimlar}

## İlgili Ders Kitabı Bölümleri
{textbook_sections}

## Görev
Bu soruyu analiz et ve yapılandırılmış çıktı üret:
1. Öğrenciye anlaşılır bir özet yaz
2. En uygun kazanımları seç ve neden eşleştiğini açıkla
3. Ön koşul eksikliği varsa belirt
4. Ders kitabından referanslar ekle
5. Çalışma önerileri sun"""
    
    def __init__(self, llm: Optional[AzureChatOpenAI] = None):
        """
        Args:
            llm: Optional LangChain Azure ChatOpenAI. Creates one if not provided.
        """
        if llm:
            self.llm = llm
        else:
            settings = get_settings()
            self.llm = AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_deployment=settings.azure_openai_chat_deployment,
                temperature=0
            )
        
        # Create structured output chain
        self.structured_llm = self.llm.with_structured_output(AnalysisOutput)
    
    async def generate(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        related_chunks: List[Dict[str, Any]] = None,
        detected_topics: List[str] = None,
        prerequisite_gaps: List[Dict[str, Any]] = None
    ) -> AnalysisOutput:
        """
        Generate structured analysis response.
        
        Args:
            question_text: The student's question
            matched_kazanimlar: Retrieved kazanımlar from Phase 4
            related_chunks: Related textbook chunks
            detected_topics: Topics detected in the question
            prerequisite_gaps: Pre-computed prerequisite gaps
            
        Returns:
            AnalysisOutput with structured response
        """
        # Build prompt
        prompt = self._build_prompt(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            textbook_sections=related_chunks or [],
            topics=detected_topics or []
        )
        
        try:
            # Generate with structured output
            result = await self.structured_llm.ainvoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])
            
            # Add pre-computed gaps if any
            if prerequisite_gaps:
                result.prerequisite_gaps.extend([
                    PrerequisiteGap(**gap) for gap in prerequisite_gaps
                ])
            
            return result
            
        except Exception as e:
            # Return minimal valid output on error
            return AnalysisOutput(
                summary=f"Analiz sırasında bir hata oluştu: {str(e)}",
                confidence=0.0
            )
    
    def generate_sync(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        related_chunks: List[Dict[str, Any]] = None,
        detected_topics: List[str] = None
    ) -> AnalysisOutput:
        """Synchronous version of generate"""
        prompt = self._build_prompt(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            textbook_sections=related_chunks or [],
            topics=detected_topics or []
        )
        
        try:
            result = self.structured_llm.invoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])
            return result
        except Exception as e:
            return AnalysisOutput(
                summary=f"Analiz sırasında bir hata oluştu: {str(e)}",
                confidence=0.0
            )
    
    def _build_prompt(
        self,
        question_text: str,
        kazanimlar: List[Dict[str, Any]],
        textbook_sections: List[Dict[str, Any]],
        topics: List[str]
    ) -> str:
        """Build the analysis prompt"""
        # Format kazanımlar
        kazanim_text = ""
        for i, k in enumerate(kazanimlar[:5], 1):  # Limit to top 5
            code = k.get("kazanim_code", "")
            desc = k.get("kazanim_description", "")
            score = k.get("score", 0)
            kazanim_text += f"{i}. [{code}] {desc} (skor: {score:.2f})\n"
        
        if not kazanim_text:
            kazanim_text = "Eşleşen kazanım bulunamadı."
        
        # Format textbook sections
        sections_text = ""
        for i, s in enumerate(textbook_sections[:3], 1):  # Limit to 3
            content = s.get("content", "")[:500]  # Truncate
            path = s.get("hierarchy_path", "")
            sections_text += f"{i}. {path}:\n{content}\n\n"
        
        if not sections_text:
            sections_text = "İlgili ders kitabı bölümü bulunamadı."
        
        # Format topics
        topics_text = ", ".join(topics) if topics else "Konu tespit edilemedi"
        
        return self.ANALYSIS_PROMPT.format(
            question_text=question_text,
            topics=topics_text,
            kazanimlar=kazanim_text,
            textbook_sections=sections_text
        )
