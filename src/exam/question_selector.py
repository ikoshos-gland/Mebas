"""
MEB RAG Sistemi - Question Selector
LLM destekli akıllı soru seçimi.
"""
import json
import logging
import random
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import get_settings
from .question_indexer import QuestionIndexer, QuestionInfo, FolderIndex

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SelectedQuestion:
    """Seçilen soru bilgisi"""
    file_path: str
    kazanim_code: str
    difficulty: str
    answer: Optional[str]
    question_number: int


SELECTOR_SYSTEM_PROMPT = """Sen bir eğitim uzmanısın. Verilen kazanımlar ve mevcut soru havuzundan
en uygun soruları seçeceksin.

Seçim kriterleri:
1. Kazanım çeşitliliği: Mümkün olduğunca farklı kazanımlardan soru seç
2. Zorluk dengesi: İstenen zorluk dağılımına uy
3. Soru kalitesi: Analiz edilmiş (analyzed=true) soruları tercih et
4. Tekrar önleme: Aynı dosyadan birden fazla soru seçme

JSON formatında yanıt ver."""

SELECTOR_USER_PROMPT = """Aşağıdaki kazanımlara uygun {count} soru seç.

KAZANIMLAR (öğrencinin çalıştığı konular):
{kazanimlar}

MEVCUT SORU HAVUZU:
{available_questions}

ZORLUK DAĞILIMI (hedef):
- Kolay: %{easy} ({easy_count} soru)
- Orta: %{medium} ({medium_count} soru)
- Zor: %{hard} ({hard_count} soru)

JSON formatında yanıt ver (sadece JSON, başka bir şey yazma):
{{
    "selected": [
        {{"file_path": "...", "kazanim_code": "...", "difficulty": "...", "answer": "..."}}
    ],
    "selection_reasoning": "Kısa açıklama"
}}"""


class QuestionSelector:
    """LLM destekli akıllı soru seçici."""

    def __init__(self, use_llm: bool = True):
        """
        Args:
            use_llm: True ise LLM kullan, False ise basit random seçim
        """
        self.use_llm = use_llm
        self.indexer = QuestionIndexer()

        if use_llm:
            self.llm = AzureChatOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                deployment_name="gpt-4o-mini",  # Maliyet optimizasyonu
                temperature=0.3,
                max_tokens=2000
            )

    def _calculate_difficulty_counts(
        self,
        total: int,
        distribution: Dict[str, float]
    ) -> Dict[str, int]:
        """
        Toplam soru sayısı ve dağılıma göre her zorluk seviyesinden kaç soru seçileceğini hesaplar.

        Args:
            total: Toplam soru sayısı
            distribution: Zorluk dağılımı oranları

        Returns:
            Zorluk → sayı dictionary
        """
        counts = {
            "kolay": int(total * distribution.get("kolay", 0.3)),
            "orta": int(total * distribution.get("orta", 0.5)),
            "zor": int(total * distribution.get("zor", 0.2))
        }

        # Yuvarlama hatalarını düzelt
        diff = total - sum(counts.values())
        if diff > 0:
            counts["orta"] += diff

        return counts

    def _simple_select(
        self,
        available: Dict[str, FolderIndex],
        question_count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[SelectedQuestion]:
        """
        Basit random seçim (LLM kullanmadan).

        Args:
            available: Mevcut soru havuzu
            question_count: Seçilecek soru sayısı
            difficulty_distribution: Zorluk dağılımı

        Returns:
            SelectedQuestion listesi
        """
        difficulty_counts = self._calculate_difficulty_counts(
            question_count, difficulty_distribution
        )

        selected: List[SelectedQuestion] = []
        used_files: set = set()

        # Her zorluk seviyesi için soru seç
        for difficulty, count in difficulty_counts.items():
            # Bu zorluk seviyesindeki tüm soruları topla
            pool: List[QuestionInfo] = []
            for folder_index in available.values():
                for q in folder_index.questions:
                    if q.difficulty == difficulty and q.file_path not in used_files:
                        pool.append(q)

            # Random seç
            random.shuffle(pool)
            for q in pool[:count]:
                selected.append(SelectedQuestion(
                    file_path=q.file_path,
                    kazanim_code=q.kazanim_code,
                    difficulty=q.difficulty,
                    answer=q.answer,
                    question_number=len(selected) + 1
                ))
                used_files.add(q.file_path)

        # Eksik soru varsa herhangi zorluktakilerden tamamla
        if len(selected) < question_count:
            remaining_pool: List[QuestionInfo] = []
            for folder_index in available.values():
                for q in folder_index.questions:
                    if q.file_path not in used_files:
                        remaining_pool.append(q)

            random.shuffle(remaining_pool)
            for q in remaining_pool:
                if len(selected) >= question_count:
                    break
                selected.append(SelectedQuestion(
                    file_path=q.file_path,
                    kazanim_code=q.kazanim_code,
                    difficulty=q.difficulty,
                    answer=q.answer,
                    question_number=len(selected) + 1
                ))
                used_files.add(q.file_path)

        return selected

    async def select(
        self,
        available: Dict[str, FolderIndex],
        question_count: int,
        difficulty_distribution: Optional[Dict[str, float]] = None
    ) -> List[SelectedQuestion]:
        """
        Verilen havuzdan soru seçer.

        Args:
            available: Kazanım kodu → FolderIndex dictionary
            question_count: Seçilecek soru sayısı
            difficulty_distribution: Zorluk dağılımı oranları

        Returns:
            SelectedQuestion listesi
        """
        if not available:
            logger.warning("Soru havuzu boş!")
            return []

        distribution = difficulty_distribution or {"kolay": 0.3, "orta": 0.5, "zor": 0.2}

        # Toplam mevcut soru sayısını kontrol et
        total_available = sum(fi.total_count for fi in available.values())
        if total_available == 0:
            logger.warning("Mevcut soru yok!")
            return []

        # İstenen sayı mevcut sayıdan fazlaysa sınırla
        actual_count = min(question_count, total_available)
        if actual_count < question_count:
            logger.warning(
                f"İstenen soru sayısı ({question_count}) mevcut sayıdan ({total_available}) fazla. "
                f"{actual_count} soru seçilecek."
            )

        # LLM kullanmıyorsa basit seçim yap
        if not self.use_llm:
            return self._simple_select(available, actual_count, distribution)

        # LLM ile akıllı seçim
        try:
            return await self._llm_select(available, actual_count, distribution)
        except Exception as e:
            logger.error(f"LLM seçim hatası, basit seçime dönülüyor: {e}")
            return self._simple_select(available, actual_count, distribution)

    async def _llm_select(
        self,
        available: Dict[str, FolderIndex],
        question_count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[SelectedQuestion]:
        """
        LLM ile akıllı soru seçimi.
        """
        difficulty_counts = self._calculate_difficulty_counts(
            question_count, difficulty_distribution
        )

        # Kazanımları listele
        kazanimlar_str = "\n".join([
            f"- {code}: {fi.total_count} soru mevcut"
            for code, fi in available.items()
        ])

        # Soru havuzunu JSON'a dönüştür (özet)
        questions_summary = []
        for code, fi in available.items():
            for q in fi.questions:
                questions_summary.append({
                    "file_path": q.file_path,
                    "kazanim_code": q.kazanim_code,
                    "difficulty": q.difficulty,
                    "answer": q.answer,
                    "analyzed": q.analyzed
                })

        # Prompt oluştur
        user_prompt = SELECTOR_USER_PROMPT.format(
            count=question_count,
            kazanimlar=kazanimlar_str,
            available_questions=json.dumps(questions_summary, ensure_ascii=False, indent=2),
            easy=int(difficulty_distribution.get("kolay", 0.3) * 100),
            medium=int(difficulty_distribution.get("orta", 0.5) * 100),
            hard=int(difficulty_distribution.get("zor", 0.2) * 100),
            easy_count=difficulty_counts["kolay"],
            medium_count=difficulty_counts["orta"],
            hard_count=difficulty_counts["zor"]
        )

        messages = [
            SystemMessage(content=SELECTOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        response = await self.llm.ainvoke(messages)
        result_text = response.content.strip()

        # JSON parse
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        result = json.loads(result_text)

        # SelectedQuestion listesine dönüştür
        selected: List[SelectedQuestion] = []
        for i, item in enumerate(result.get("selected", []), 1):
            selected.append(SelectedQuestion(
                file_path=item["file_path"],
                kazanim_code=item["kazanim_code"],
                difficulty=item["difficulty"],
                answer=item.get("answer"),
                question_number=i
            ))

        logger.info(f"LLM seçim tamamlandı: {len(selected)} soru, sebep: {result.get('selection_reasoning', 'N/A')}")

        return selected

    async def select_for_kazanimlar(
        self,
        kazanim_codes: List[str],
        question_count: int = 10,
        difficulty_distribution: Optional[Dict[str, float]] = None
    ) -> List[SelectedQuestion]:
        """
        Verilen kazanım kodları için soru seçer.

        Args:
            kazanim_codes: Kazanım kodları listesi
            question_count: Seçilecek soru sayısı
            difficulty_distribution: Zorluk dağılımı

        Returns:
            SelectedQuestion listesi
        """
        # Mevcut soruları al
        available = self.indexer.get_questions_for_kazanimlar(kazanim_codes)

        return await self.select(available, question_count, difficulty_distribution)
