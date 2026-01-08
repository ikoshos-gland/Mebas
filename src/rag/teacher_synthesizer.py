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
    
    SYSTEM_PROMPT = """Sen deneyimli bir MEB müfredat uzmanı ve pedagogsun. 
Öğrencinin sorusunu analiz edip, RAG sisteminden gelen kazanım ve ders kitabı bilgilerini kullanarak 
öğretici bir açıklama yapıyorsun.

ROLÜN:
1. Bir hoca gibi konuşursun - samimi ama profesyonel
2. Öğrencinin eksik olduğu konuları tespit edersin
3. MEB kazanımlarına göre neyi çalışması gerektiğini söylersin
4. Ders kitabından ilgili bölümlere yönlendirirsin
5. Karmaşık kavramları basit örneklerle açıklarsın

FORMAT:
- Önce öğrencinin sorusunu kısaca özetle
- Sonra ana kavramları açıkla
- Eksik görülen konuları belirt
- Çalışma önerileri sun
- İlgili kazanım kodlarını referans ver

DİL: Türkçe, öğrenci dostu, teşvik edici"""

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
        summary: Optional[str] = None
    ) -> str:
        """
        Generate a teacher-like explanation from RAG results.
        
        Args:
            question_text: The student's original question
            matched_kazanimlar: Matched kazanımlar from RAG
            textbook_chunks: Related textbook content from RAG
            summary: Optional existing summary to enhance
            
        Returns:
            Pedagogical explanation as markdown string
        """
        import asyncio
        
        # Build context from RAG results
        context = self._build_context(
            question_text=question_text,
            kazanimlar=matched_kazanimlar,
            chunks=textbook_chunks,
            summary=summary
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
        summary: Optional[str] = None
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
            summary=summary
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
        summary: Optional[str]
    ) -> str:
        """Build the context prompt from RAG results"""
        
        # Format kazanımlar
        kazanim_text = ""
        for i, k in enumerate(kazanimlar[:5], 1):
            code = k.get("kazanim_code") or k.get("code", "")
            desc = k.get("kazanim_description") or k.get("description", "")
            grade = k.get("grade", "")
            score = k.get("score", 0)
            
            kazanim_text += f"""
{i}. **{code}** (Sınıf: {grade}, Eşleşme: %{score*100:.0f})
   {desc[:500]}
"""
        
        if not kazanim_text:
            kazanim_text = "Eşleşen kazanım bulunamadı."
        
        # Format textbook chunks
        chunks_text = ""
        for i, c in enumerate(chunks[:3], 1):
            chapter = c.get("hierarchy_path") or c.get("chapter", "")
            pages = c.get("page_range") or c.get("pages", "")
            content = c.get("content", "")[:400]
            
            chunks_text += f"""
{i}. **{chapter}** (Sayfa: {pages})
   {content}...
"""
        
        if not chunks_text:
            chunks_text = "İlgili ders kitabı bölümü bulunamadı."
        
        # Build full context
        return f"""## Öğrenci Sorusu
{question_text}

## RAG Sistemi - Eşleşen Kazanımlar
{kazanim_text}

## RAG Sistemi - Ders Kitabı Referansları
{chunks_text}

## Mevcut Özet
{summary or "Özet henüz üretilmedi."}

---

Yukarıdaki bilgileri kullanarak öğrenciye yardımcı olacak, öğretici ve teşvik edici bir açıklama yaz.
Şunları içersin:
1. Sorunun kısa bir analizi
2. Temel kavramların açıklaması
3. Hangi kazanımları çalışması gerektiği (kazanım kodlarıyla birlikte)
4. Ders kitabından hangi bölümleri okuması gerektiği
5. Ekstra tavsiyeler veya dikkat edilmesi gereken noktalar"""
