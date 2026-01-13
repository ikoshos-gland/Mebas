"""
MEB RAG Sistemi - Question Analyzer
GPT-4o Vision ile soru görüntülerini analiz eder.
"""
import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage

from config.settings import get_settings
from .question_indexer import QuestionIndexer, QuestionInfo, FolderIndex

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AnalysisResult:
    """Soru analiz sonucu"""
    kazanim_code: str
    difficulty: str  # kolay, orta, zor
    answer: Optional[str]  # A, B, C, D, E veya açıklama
    question_type: str  # coktan_secmeli, acik_uclu
    topic_hints: List[str]  # Konu ipuçları
    confidence: float  # Analiz güveni


ANALYSIS_PROMPT = """Bu bir MEB müfredatına uygun soru görüntüsüdür. Aşağıdaki bilgileri çıkar:

1. **Kazanım Kodu**: Sorunun hangi kazanıma ait olduğunu belirle. Klasör adı "{folder_kazanim}" şeklinde ipucu veriyor.
2. **Zorluk Seviyesi**: kolay / orta / zor
   - kolay: Temel kavram sorusu, direkt bilgi hatırlama
   - orta: Uygulama gerektiren, çok adımlı işlem
   - zor: Analiz/sentez gerektiren, tuzak içeren, karmaşık
3. **Cevap**: Çoktan seçmeliyse A/B/C/D/E, açık uçluysa kısa cevap
4. **Soru Tipi**: coktan_secmeli veya acik_uclu
5. **Konu İpuçları**: Sorunun hangi alt konularla ilgili olduğu

JSON formatında yanıt ver:
{{
    "kazanim_code": "...",
    "difficulty": "kolay|orta|zor",
    "answer": "A|B|C|D|E veya kısa cevap",
    "question_type": "coktan_secmeli|acik_uclu",
    "topic_hints": ["konu1", "konu2"],
    "confidence": 0.0-1.0
}}

SADECE JSON döndür, başka bir şey yazma."""


class QuestionAnalyzer:
    """GPT-4o Vision ile soru görüntülerini analiz eder."""

    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            deployment_name=settings.azure_openai_chat_deployment,
            temperature=0.0,
            max_tokens=500
        )
        self.indexer = QuestionIndexer()

    def _encode_image(self, image_path: str) -> str:
        """Görüntüyü base64'e dönüştürür."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _get_image_media_type(self, image_path: str) -> str:
        """Görüntü dosya uzantısına göre media type döndürür."""
        ext = Path(image_path).suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif"
        }
        return media_types.get(ext, "image/png")

    async def analyze_question(
        self,
        image_path: str,
        folder_kazanim: Optional[str] = None
    ) -> AnalysisResult:
        """
        Tek bir soru görüntüsünü analiz eder.

        Args:
            image_path: Görüntü dosya yolu
            folder_kazanim: Klasörden çıkarılan kazanım kodu ipucu

        Returns:
            AnalysisResult
        """
        # Kazanım ipucunu çıkar
        if not folder_kazanim:
            folder_name = Path(image_path).parent.name
            folder_kazanim = self.indexer.folder_to_kazanim(folder_name)

        # Görüntüyü encode et
        image_base64 = self._encode_image(image_path)
        media_type = self._get_image_media_type(image_path)

        # Prompt oluştur
        prompt = ANALYSIS_PROMPT.format(folder_kazanim=folder_kazanim)

        # Vision API çağrısı
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_base64}",
                        "detail": "high"
                    }
                }
            ]
        )

        try:
            response = await self.llm.ainvoke([message])
            result_text = response.content.strip()

            # JSON parse
            # Bazen LLM ```json ... ``` şeklinde döndürebilir
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]

            result = json.loads(result_text)

            return AnalysisResult(
                kazanim_code=result.get("kazanim_code", folder_kazanim),
                difficulty=result.get("difficulty", "orta"),
                answer=result.get("answer"),
                question_type=result.get("question_type", "coktan_secmeli"),
                topic_hints=result.get("topic_hints", []),
                confidence=result.get("confidence", 0.7)
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}, response: {result_text}")
            return AnalysisResult(
                kazanim_code=folder_kazanim,
                difficulty="orta",
                answer=None,
                question_type="coktan_secmeli",
                topic_hints=[],
                confidence=0.3
            )
        except Exception as e:
            logger.error(f"Analiz hatası: {e}")
            raise

    async def analyze_folder(
        self,
        folder_path: str,
        force_reanalyze: bool = False
    ) -> FolderIndex:
        """
        Bir klasördeki tüm soruları analiz eder.

        Args:
            folder_path: Klasör yolu
            force_reanalyze: True ise zaten analiz edilmişleri de yeniden analiz et

        Returns:
            Güncellenmiş FolderIndex
        """
        folder_index = self.indexer.scan_folder(folder_path)

        for question in folder_index.questions:
            # Zaten analiz edilmişse atla
            if question.analyzed and not force_reanalyze:
                continue

            try:
                logger.info(f"Analiz ediliyor: {question.file_path}")
                result = await self.analyze_question(
                    question.file_path,
                    folder_index.kazanim_code
                )

                # Sonucu güncelle
                question.difficulty = result.difficulty
                question.answer = result.answer
                question.question_type = result.question_type
                question.analyzed = True

            except Exception as e:
                logger.error(f"Soru analiz hatası ({question.file_path}): {e}")
                continue

        # Zorluk sayılarını güncelle
        folder_index.difficulty_counts = {"kolay": 0, "orta": 0, "zor": 0}
        for q in folder_index.questions:
            if q.difficulty in folder_index.difficulty_counts:
                folder_index.difficulty_counts[q.difficulty] += 1

        # Index'i kaydet
        self.indexer.save_index(folder_index)

        return folder_index

    async def analyze_multiple_folders(
        self,
        kazanim_codes: List[str],
        force_reanalyze: bool = False
    ) -> Dict[str, FolderIndex]:
        """
        Birden fazla kazanım için klasörleri analiz eder.

        Args:
            kazanim_codes: Kazanım kodları listesi
            force_reanalyze: Yeniden analiz et

        Returns:
            Kazanım kodu → FolderIndex dictionary
        """
        results: Dict[str, FolderIndex] = {}

        for code in kazanim_codes:
            folder_path = self.indexer.kazanim_to_folder(code)
            try:
                folder_index = await self.analyze_folder(folder_path, force_reanalyze)
                results[code] = folder_index
            except Exception as e:
                logger.error(f"Klasör analiz hatası ({folder_path}): {e}")
                continue

        return results


async def analyze_folder(folder_path: str) -> FolderIndex:
    """
    Kolaylık fonksiyonu: Tek bir klasörü analiz eder.

    Args:
        folder_path: Klasör yolu

    Returns:
        FolderIndex
    """
    analyzer = QuestionAnalyzer()
    return await analyzer.analyze_folder(folder_path)
