"""
MEB RAG Sistemi - Response Generator
LLM-based response generation with structured output
"""
from typing import Optional, List, Dict, Any
from langchain_openai import AzureChatOpenAI

from config.settings import get_settings
from src.rag.output_models import AnalysisOutput, MatchedKazanim, PrerequisiteGap
from src.utils.resilience import with_resilience, CircuitOpenError


class ResponseGenerator:
    """
    Generates structured responses using LLM with Pydantic output.
    
    CRITICAL: Uses llm.with_structured_output() for guaranteed JSON!
    """
    
    SYSTEM_PROMPT = """Sen bir MEB müfredat uzmanısın. Öğrenci sorularını analiz edip 
kazanımlarla eşleştiriyorsun.

KURALLAR:
1. Sadece verilen kazanımları kullan, uydurma!
2. Soruyu ADIM ADIM çöz ve her adımı açıkla.
3. Nihai cevabı net bir şekilde belirt.
4. Ön koşul eksikliği varsa mutlaka belirt.
5. Ders kitabından referans verirken sayfa numarası kullan.
6. Türkçe yanıt ver.
7. Özet mesajı öğrenci için anlaşılır olmalı."""

    ANALYSIS_PROMPT = """## Soru
{question_text}

## Tespit Edilen Konular
{topics}

## Eşleşen Kazanımlar (Retrieval Sonuçları)
{kazanimlar}

## İlgili Ders Kitabı Bölümleri
{textbook_sections}

## Görev
Bu soruyu analiz et ve AŞAĞIDAKİ YAPIDA BİR ÇIKIŞ ÜRET. 'solution_steps' alanı BOŞ OLAMAZ!

ZORUNLU ADIMLAR:
1. [ÖNEMLİ] Soruyu adım adım çöz ve her mantıksal adımı 'solution_steps' listesine ekle. En az 3 adım olmalı.
2. [ÖNEMLİ] Sorunun net cevabını 'final_answer' alanına yaz (Örn: "D şıkkı, 20").
3. [KRİTİK] VERİLEN TÜM KAZANIMLARI 'matched_kazanimlar' listesine dahil et! Hiçbirini atlama!
   - DOĞRUDAN EŞLEŞMELER → match_type: "primary" olarak işaretle
   - ALTERNATİF/DOLAYLI KAZANIMLAR → match_type: "alternative" olarak işaretle
4. HER KAZANIM İÇİN neden eşleştiğini 'match_reason' alanında açıkla (1-2 cümle).
5. Ön koşul eksikliği varsa belirt.
6. Öğrenci için motive edici bir özet yaz.
7. Ders kitabı referanslarını tam hiyerarşi ile belirt (Kitap > Ünite > Konu > Sayfa).

EŞLEŞME NEDENİ FORMATI:
Her kazanım için match_reason alanı şu formatta olmalı:
"Bu kazanım [soru konusu] ile eşleşiyor çünkü [sebep]. Soruda [ortak kavram] kullanılıyor."

Eğer soru bir görsel ise ve metin yoksa, görseldeki soruyu çözmeye çalış.
Eğer soru çözülemiyorsa, solution_steps alanına "Soruyu çözmek için yeterli bilgi yok" şeklinde tek bir adım ekle."""
    
    def __init__(self, llm: Optional[AzureChatOpenAI] = None):
        """
        Args:
            llm: Optional LangChain Azure ChatOpenAI. Creates one if not provided.
        """
        self.settings = get_settings()
        if llm:
            self.llm = llm
        else:
            self.llm = AzureChatOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_deployment=self.settings.azure_openai_chat_deployment,
                temperature=self.settings.llm_temperature_deterministic
            )

        # Create structured output chain
        self.structured_llm = self.llm.with_structured_output(AnalysisOutput)
    
    async def generate(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        related_chunks: List[Dict[str, Any]] = None,
        related_images: List[Dict[str, Any]] = None,
        detected_topics: List[str] = None,
        prerequisite_gaps: List[Dict[str, Any]] = None
    ) -> AnalysisOutput:
        """
        Generate structured analysis response.
        
        Args:
            question_text: The student's question
            matched_kazanimlar: Retrieved kazanımlar from Phase 4
            related_chunks: Related textbook chunks
            related_images: Related textbook images
            detected_topics: Topics detected in the question
            prerequisite_gaps: Pre-computed prerequisite gaps
            
        Returns:
            AnalysisOutput with structured response
        """
        from src.rag.output_models import ImageReference
        
        # Build prompt
        prompt = self._build_prompt(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            textbook_sections=related_chunks or [],
            topics=detected_topics or []
        )
        
        try:
            # Generate with structured output and resilience
            result = await self._invoke_llm_with_resilience(prompt)
            
            # Add pre-computed gaps if any
            if prerequisite_gaps:
                result.prerequisite_gaps.extend([
                    PrerequisiteGap(**gap) for gap in prerequisite_gaps
                ])
                
            # Add retrieved images
            if related_images:
                result.image_references.extend([
                    ImageReference(
                        image_id=img.get("image_id") or img.get("id"),
                        caption=img.get("caption", ""),
                        page_number=img.get("page_number", 0),
                        why_relevant="Görsel konuyla ilgili"  # Default reason
                    ) for img in related_images
                ])
            
            return result
            
        except CircuitOpenError as e:
            # Circuit is open - service is known to be down
            return AnalysisOutput(
                summary=f"Servis geçici olarak kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
                confidence=0.0
            )
        except Exception as e:
            # Return minimal valid output on error
            return AnalysisOutput(
                summary=f"Analiz sırasında bir hata oluştu: {str(e)}",
                confidence=0.0
            )

    async def _invoke_llm_with_resilience(self, prompt: str) -> AnalysisOutput:
        """
        Invoke LLM with circuit breaker and retry protection.

        Uses the resilience module for:
        - Circuit breaker to fast-fail if Azure OpenAI is down
        - Exponential backoff retry for transient failures
        - Timeout protection
        """
        @with_resilience(
            circuit_name="azure_openai_response",
            timeout=self.settings.timeout_generate_response,
            use_circuit_breaker=True,
            use_retry=True
        )
        async def _invoke():
            return await self.structured_llm.ainvoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])

        return await _invoke()

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
        """Build the analysis prompt with detailed kazanım and textbook information"""
        # Format kazanımlar - Split by type
        primary_matches = []
        alternative_matches = []

        for k in kazanimlar:
            mclient = k.get("match_type", "primary")
            # Handle both string and Enum if mixed
            mtype = mclient.value if hasattr(mclient, "value") else str(mclient)

            if mtype == "alternative":
                alternative_matches.append(k)
            else:
                primary_matches.append(k)

        # 1. Primary Matches - WITH DETAILED INFO
        max_kazanimlar = self.settings.response_max_kazanimlar
        kazanim_text = "--- DOĞRUDAN EŞLEŞMELER (Çözüm İçin Kullan) ---\n"
        if primary_matches:
            for i, k in enumerate(primary_matches[:max_kazanimlar], 1):
                code = k.get("kazanim_code", "")
                title = k.get("kazanim_title", "")
                desc = k.get("kazanim_description", "")
                score = k.get("blended_score", k.get("score", 0))
                grade = k.get("grade", "?")
                subject = k.get("subject", "")
                # Get reranker reasoning if available
                match_reason = k.get("rerank_reasoning", "")

                kazanim_text += f"{i}. [{code}] {title or desc[:100]}\n"
                kazanim_text += f"   Açıklama: {desc}\n"
                kazanim_text += f"   Skor: {score:.2f} | Sınıf: {grade} | Ders: {subject}\n"
                if match_reason:
                    kazanim_text += f"   Eşleşme Nedeni: {match_reason}\n"
                kazanim_text += "\n"
        else:
            kazanim_text += "Doğrudan eşleşen kazanım bulunamadı.\n"

        # 2. Alternative Matches
        if alternative_matches:
            kazanim_text += "\n--- ALTERNATİF/İLGİLİ KAZANIMLAR (Bağlam İçin Kullan) ---\n"
            for i, k in enumerate(alternative_matches[:max_kazanimlar], 1):
                code = k.get("kazanim_code", "")
                title = k.get("kazanim_title", "")
                desc = k.get("kazanim_description", "")
                grade = k.get("grade", "?")
                kazanim_text += f"- [{code}] (Sınıf {grade}) {title or desc}\n"

        # Format textbook sections - WITH FULL HIERARCHY
        max_sections = self.settings.response_max_textbook_sections
        content_truncate = self.settings.response_content_truncate
        sections_text = ""
        for i, s in enumerate(textbook_sections[:max_sections], 1):
            content = s.get("content", "")[:content_truncate]
            hierarchy = s.get("hierarchy_path", "")
            page_range = s.get("page_range", "")
            textbook_name = s.get("textbook_name", "Ders Kitabı")
            grade = s.get("grade", "")
            chunk_type = s.get("chunk_type", "")

            # Build full hierarchy string
            full_hierarchy = textbook_name
            if grade:
                full_hierarchy = f"{textbook_name} ({grade}. Sınıf)"
            if hierarchy:
                full_hierarchy += f" > {hierarchy}"
            if page_range:
                full_hierarchy += f" > Sayfa {page_range}"

            sections_text += f"{i}. [{full_hierarchy}]\n"
            if chunk_type:
                sections_text += f"   Tür: {chunk_type}\n"
            sections_text += f"   {content}\n\n"

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
