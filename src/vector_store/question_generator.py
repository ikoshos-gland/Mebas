"""
MEB RAG Sistemi - Sentetik Soru Üreticisi
Her kazanım için GPT ile test soruları üretir
"""
from openai import AzureOpenAI, AsyncAzureOpenAI
from dataclasses import dataclass
from typing import List, Optional
import json

from config.settings import get_settings


@dataclass
class SyntheticQuestion:
    """Generated synthetic question for a kazanım"""
    question_text: str
    difficulty: str  # "kolay", "orta", "zor"
    question_type: str  # "çoktan_seçmeli", "boşluk_doldurma", "problem", "doğru_yanlış"
    parent_kazanim_id: str
    parent_kazanim_code: str
    related_textbook_section: str = ""


class SyntheticQuestionGenerator:
    """
    Generates synthetic questions for each kazanım.
    
    Uses gpt-4o for high-quality question generation.
    Generates 20 questions per kazanım by default.
    JSON response format for reliable parsing.
    """
    
    # Cost-optimized default: 20 questions provides sufficient coverage
    DEFAULT_COUNT = 20
    
    GENERATION_PROMPT = """Sen bir MEB sınav hazırlama uzmanısın.

KAZANIM: {kazanim_code} - {kazanim_description}
SINIF: {grade}. Sınıf
DERS: {subject}

Bu kazanımı ölçen {count} farklı soru üret.

KURALLAR:
1. Zorluk dağılımı: 8 kolay, 8 orta, 4 zor
2. Soru tipleri: çoktan_seçmeli, boşluk_doldurma, problem, doğru_yanlış
3. Matematik/Fen için formülleri LaTeX formatında yaz ($x^2$ gibi)
4. Sadece bu kazanımı test et, başka konuya karışma!
5. Gerçekçi ve çözülebilir olmalı

JSON formatında döndür (başka açıklama yazma):
{{"questions": [{{"question": "...", "difficulty": "kolay/orta/zor", "type": "çoktan_seçmeli/problem/..."}}]}}"""
    
    def __init__(self, client: Optional[AzureOpenAI] = None):
        """
        Args:
            client: Optional Azure OpenAI client. If not provided, creates one.
        """
        if client:
            self.client = client
        else:
            settings = get_settings()
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version
            )
    
    def generate_for_kazanim(
        self,
        kazanim: dict,
        textbook_sections: Optional[List[str]] = None,
        count: int = DEFAULT_COUNT
    ) -> List[SyntheticQuestion]:
        """
        Generate synthetic questions for a kazanım (sync version).
        
        Args:
            kazanim: Dict with id, code, description, grade, subject
            textbook_sections: Optional related textbook content
            count: Number of questions to generate
            
        Returns:
            List of SyntheticQuestion objects
        """
        prompt = self.GENERATION_PROMPT.format(
            count=count,
            kazanim_code=kazanim.get("code", ""),
            kazanim_description=kazanim.get("description", ""),
            grade=kazanim.get("grade", ""),
            subject=kazanim.get("subject", "")
        )
        
        # Add textbook context if available
        if textbook_sections:
            context = "\n".join(textbook_sections[:2])  # Limit context size
            prompt += f"\n\nDERS KİTABI BAĞLAMI:\n{context}"
        
        # Retry logic for JSON parsing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use gpt-4o for high-quality question generation
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=3000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                data = json.loads(content)
                
                # Handle different JSON structures
                questions = data.get("questions", data) if isinstance(data, dict) else data
                if not isinstance(questions, list):
                    questions = [questions]
                
                return [
                    SyntheticQuestion(
                        question_text=q.get("question", ""),
                        difficulty=q.get("difficulty", "orta"),
                        question_type=q.get("type", "problem"),
                        parent_kazanim_id=str(kazanim.get("id", "")),
                        parent_kazanim_code=kazanim.get("code", ""),
                        related_textbook_section=textbook_sections[0] if textbook_sections else ""
                    )
                    for q in questions
                    if q.get("question")
                ]
                
            except json.JSONDecodeError as e:
                print(f"JSON parse hatası (deneme {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return []
            except Exception as e:
                print(f"Soru üretim hatası: {e}")
                return []
        
        return []
    
    async def generate_for_kazanim_async(
        self,
        kazanim: dict,
        textbook_sections: Optional[List[str]] = None,
        count: int = DEFAULT_COUNT
    ) -> List[SyntheticQuestion]:
        """
        Generate synthetic questions for a kazanım (async version).
        Includes exponential backoff for rate limit handling.
        """
        import asyncio
        
        settings = get_settings()
        async_client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
        
        prompt = self.GENERATION_PROMPT.format(
            count=count,
            kazanim_code=kazanim.get("code", ""),
            kazanim_description=kazanim.get("description", ""),
            grade=kazanim.get("grade", ""),
            subject=kazanim.get("subject", "")
        )
        
        if textbook_sections:
            context = "\n".join(textbook_sections[:2])
            prompt += f"\n\nDERS KİTABI BAĞLAMI:\n{context}"
        
        max_retries = 5  # Increased for rate limits
        for attempt in range(max_retries):
            try:
                response = await async_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=3000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                data = json.loads(content)
                
                questions = data.get("questions", data) if isinstance(data, dict) else data
                if not isinstance(questions, list):
                    questions = [questions]
                
                return [
                    SyntheticQuestion(
                        question_text=q.get("question", ""),
                        difficulty=q.get("difficulty", "orta"),
                        question_type=q.get("type", "problem"),
                        parent_kazanim_id=str(kazanim.get("id", "")),
                        parent_kazanim_code=kazanim.get("code", ""),
                        related_textbook_section=textbook_sections[0] if textbook_sections else ""
                    )
                    for q in questions
                    if q.get("question")
                ]
                
            except json.JSONDecodeError as e:
                print(f"JSON parse hatası (deneme {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return []
            except Exception as e:
                error_str = str(e)
                # Rate limit handling with exponential backoff
                if "429" in error_str or "rate" in error_str.lower():
                    wait_time = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
                    print(f"⚠️ Rate limit! {wait_time}s bekleniyor... (deneme {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                print(f"Async soru üretim hatası: {e}")
                return []
        
        return []

