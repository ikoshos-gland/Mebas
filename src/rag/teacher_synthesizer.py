"""
MEB RAG Sistemi - Teacher Synthesizer
Uses GPT-5.2 to generate pedagogical explanations from RAG results
"""
from typing import Optional, List, Dict, Any
from openai import AzureOpenAI

from config.settings import get_settings


class TeacherSynthesizer:
    """
    Synthesizes RAG results into teacher-like explanations.
    
    Uses GPT-5.2 for advanced reasoning and pedagogical content generation.
    """
    
    SYSTEM_PROMPT = """Sen deneyimli bir MEB müfredat uzmanı ve özel ders hocasısın.
Sana çözülmüş bir soru, RAG sisteminden gelen kazanımlar ve ders kitabı bölümleri veriliyor.

Eğer "ONCEKI SOHBET" bölümü varsa, bu öğrenciyle önceki konuşmanı gösterir.
Öğrencinin takip soruları sorması durumunda önceki bağlamı kullanarak tutarlı yanıt ver.

⚠️ KRİTİK KURAL - HALÜSİNASYON YASAK:
- Kazanım kodlarını ve açıklamalarını SADECE sana verilen listeden kullan
- ASLA kazanım kodu veya açıklaması UYDURMA
- Sana verilen kazanım listesinde olmayan bir kazanımdan bahsetme
- "EŞLEŞEN KAZANIMLAR" bölümündeki bilgileri AYNEN kullan

📐 MATEMATİKSEL İFADELER:
Matematiksel formüller, denklemler ve semboller için LaTeX kullan:
- Satır içi formül: $x^2 + y^2 = z^2$
- Blok formül (ayrı satır): $$\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$$

Yaygın LaTeX örnekleri:
- Kesir: $\\frac{a}{b}$
- Kök: $\\sqrt{x}$, $\\sqrt[n]{x}$
- Üs: $x^2$, $e^{-x}$
- İndis: $x_1$, $a_{n}$
- Toplam: $\\sum_{i=1}^{n} i$
- Çarpım: $\\prod_{i=1}^{n} i$
- Limit: $\\lim_{x \\to 0} f(x)$
- Türev: $\\frac{dy}{dx}$, $f'(x)$
- İntegral: $\\int_{a}^{b} f(x) dx$
- Trigonometri: $\\sin$, $\\cos$, $\\tan$
- Yunan harfleri: $\\alpha$, $\\beta$, $\\pi$, $\\theta$
- Eşitsizlik: $\\leq$, $\\geq$, $\\neq$

Aşağıdaki yapıda yanıt ver:

**Soru ve Çözüm**
Soruyu kısaca özetle, çözüm adımlarını açıkla ve doğru cevabı vurgula.

**Kazanım Analizi**
Sana verilen kazanımları kullanarak:
- Direkt Kazanım: Listede verilen ilk kazanımın KODUNU ve AÇIKLAMASINI AYNEN yaz
- İlgili Kazanımlar: Listedeki diğer kazanımların KODLARINI ve AÇIKLAMALARINI AYNEN yaz

**Ders Kitabı**
İlgili kavramları açıkla, sayfa referansları ver.

**Özet**
2-3 cümlelik özet ve çalışma önerisi.

KURALLAR:
- Türkçe, öğrenci dostu yaz
- Başlıkları kalın yap
- Matematiksel ifadeler için LaTeX kullan
- Kazanım bilgilerini UYDURMAK YASAK - sadece verilen listeyi kullan"""

    def __init__(self):
        """Initialize with Azure OpenAI GPT-5.2 client"""
        settings = get_settings()
        
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_teacher_deployment
    
    async def synthesize(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        textbook_chunks: List[Dict[str, Any]],
        question_analysis: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a teacher-like explanation from RAG results.

        Args:
            question_text: The student's original question
            matched_kazanimlar: Matched kazanımlar from RAG
            textbook_chunks: Related textbook content from RAG
            question_analysis: Pre-solved question analysis from QuestionAnalyzer
            summary: Optional existing summary to enhance
            chat_history: Previous conversation messages for context

        Returns:
            Pedagogical explanation as markdown string
        """
        import asyncio

        # Build context from RAG results and question analysis
        context = self._build_context(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            chunks=textbook_chunks,
            question_analysis=question_analysis,
            summary=summary,
            chat_history=chat_history
        )
        
        try:
            # Use GPT-5.2 for synthesis
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                max_completion_tokens=2048
                # Note: GPT-5.2 only supports default temperature (1)
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback to basic summary
            return f"Analiz tamamlandı. {summary or 'Detaylı açıklama üretilemedi.'}\n\n_Hata: {str(e)}_"
    
    async def synthesize_stream(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        textbook_chunks: List[Dict[str, Any]],
        question_analysis: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ):
        """
        Stream the teacher explanation token by token.

        Yields:
            str: Each token/chunk as it's generated
        """
        context = self._build_context(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            chunks=textbook_chunks,
            question_analysis=question_analysis,
            summary=summary,
            chat_history=chat_history
        )
        
        try:
            # Use streaming mode
            stream = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                max_completion_tokens=2048,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n_Hata: {str(e)}_"
    
    def synthesize_sync(
        self,
        question_text: str,
        matched_kazanimlar: List[Dict[str, Any]],
        textbook_chunks: List[Dict[str, Any]],
        summary: Optional[str] = None
    ) -> str:
        """Synchronous version of synthesize"""
        context = self._build_context(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            chunks=textbook_chunks,
            summary=summary
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": context}
                ],
                max_completion_tokens=2048
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Analiz tamamlandı. {summary or ''}\n\n_Hata: {str(e)}_"
    
    def _build_context(
        self,
        question_text: str,
        kazanimlar: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]],
        question_analysis: Optional[Dict[str, Any]] = None,
        summary: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build the context prompt from RAG results and question analysis"""
        from src.rag.chat_memory import format_chat_history_for_prompt

        # Format chat history if provided
        history_text = format_chat_history_for_prompt(chat_history) if chat_history else ""

        # Format kazanımlar - separate primary and related
        kazanim_text = ""

        # Filter out None values from kazanimlar
        valid_kazanimlar = [k for k in (kazanimlar or []) if k and isinstance(k, dict)]

        if valid_kazanimlar:
            # First kazanım is the primary (highest confidence)
            primary = valid_kazanimlar[0]
            code = primary.get("kazanim_code") or primary.get("code", "")
            desc = primary.get("kazanim_description") or primary.get("description", "")
            grade = primary.get("grade", "")
            score = primary.get("blended_score") or primary.get("score", 0)
            clean_desc = self._clean_kazanim_description(desc)
            
            kazanim_text += f"""
**DİREKT KAZANIM**
- **Kod:** {code}
- **Sınıf:** {grade}. Sınıf
- **Açıklama:** {clean_desc}
"""
            
            # Rest are related kazanımlar
            if len(valid_kazanimlar) > 1:
                kazanim_text += "\n**İLGİLİ KAZANIMLAR**\n"
                for i, k in enumerate(valid_kazanimlar[1:5], 1):
                    code = k.get("kazanim_code") or k.get("code", "")
                    desc = k.get("kazanim_description") or k.get("description", "")
                    grade = k.get("grade", "")
                    clean_desc = self._clean_kazanim_description(desc)
                    
                    kazanim_text += f"- **{code}** ({grade}. Sınıf): {clean_desc}\n"
        
        if not kazanim_text:
            kazanim_text = "Eşleşen kazanım bulunamadı."
        
        # Format textbook chunks - MUST include grade level clearly
        chunks_text = ""
        for i, c in enumerate(chunks[:5], 1):
            chapter = c.get("hierarchy_path") or c.get("chapter", "")
            pages = c.get("page_range") or c.get("pages", "")
            grade = c.get("grade", "")
            content = c.get("content", "")[:800]
            
            # Clear grade label
            grade_label = f"{grade}. SINIF" if grade else "Sınıf Bilinmiyor"
            chunks_text += f"""
**{grade_label} - Sayfa {pages}**
{chapter}
{content}
"""
        
        if not chunks_text:
            chunks_text = "İlgili ders kitabı bölümü bulunamadı."
        
        # Format question analysis if provided (from QuestionAnalyzer)
        analysis_text = ""
        if question_analysis and isinstance(question_analysis, dict):
            qa = question_analysis
            solution_steps = qa.get("solution_steps") or []
            steps_text = "\n".join([f"  {i}. {step}" for i, step in enumerate(solution_steps, 1)]) if solution_steps else "Adımlar belirtilmedi"
            
            analysis_text = f"""
## 🔍 SORU ANALİZİ (QuestionAnalyzer tarafından çözüldü)
**Konu:** {qa.get("subject_area", "Belirsiz")}
**Soru Tipi:** {qa.get("question_type", "Belirsiz")}
**Temel Kavramlar:** {", ".join(qa.get("key_concepts", [])) or "Belirtilmedi"}

### Çözüm Adımları:
{steps_text}

### ✅ DOĞRU CEVAP: {qa.get("correct_answer", "Belirlenemedi")}
**Açıklama:** {qa.get("explanation", "")}
"""
        
        # Build full context with question analysis and chat history
        return f"""{history_text}## ÖĞRENCİNİN SORUSU
{question_text}
{analysis_text}
## EŞLEŞEN KAZANIMLAR
{kazanim_text}

## DERS KİTABI BÖLÜMLERİ
{chunks_text}

---
Yukarıdaki bilgileri kullanarak 4 bölümlü yanıtını oluştur. SORU ANALİZİ bölümündeki çözümü temel al.
Eğer ONCEKI SOHBET bölümü varsa, öğrencinin takip sorusu olabilir - bağlamı dikkate al."""

    def _clean_kazanim_description(self, desc: str) -> str:
        """
        Clean kazanım description by removing teacher-focused content.
        
        Removes sections like:
        - "Öğrenme-öğretme uygulamaları"
        - "Etkinlik:"
        - "Öğretmen:" notes
        """
        import re
        
        # Common patterns for teacher notes
        patterns = [
            r'Öğrenme[–-]öğretme uygulamaları.*',  # Learning-teaching activities
            r'Etkinlik\s*:.*',  # Activity suggestions
            r'Öğretmen\s*:.*',  # Teacher notes
            r'Örnek etkinlik.*',  # Example activities
            r'a\)\s*Öğretmen.*',  # Numbered teacher instructions
            r'b\)\s*Öğretmen.*',
            r'c\)\s*Öğretmen.*',
        ]
        
        cleaned = desc
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

