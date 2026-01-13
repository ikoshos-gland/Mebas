"""
MEB RAG Sistemi - Exam Generator Skill
LangGraph tool olarak sınav oluşturma skill'i.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from langchain_core.tools import tool

from .question_indexer import QuestionIndexer
from .question_selector import QuestionSelector, SelectedQuestion
from .pdf_generator import ExamPDFGenerator

logger = logging.getLogger(__name__)


@dataclass
class ExamGenerationResult:
    """Sınav oluşturma sonucu."""
    success: bool
    pdf_path: Optional[str] = None
    question_count: int = 0
    kazanimlar_covered: List[str] = None
    questions: List[Dict] = None
    error: Optional[str] = None
    skipped_kazanimlar: List[str] = None  # Soru bulunamayan kazanımlar
    warning: Optional[str] = None  # Uyarı mesajı (kısmi başarı durumunda)

    def __post_init__(self):
        if self.kazanimlar_covered is None:
            self.kazanimlar_covered = []
        if self.questions is None:
            self.questions = []
        if self.skipped_kazanimlar is None:
            self.skipped_kazanimlar = []


@tool
async def generate_exam_skill(
    kazanim_codes: List[str],
    question_count: int = 10,
    difficulty_distribution: Optional[Dict[str, float]] = None,
    title: str = "Çalışma Sınavı"
) -> Dict:
    """
    Sınav oluşturma skill'i.
    Verilen kazanımlara göre sorular seçer ve PDF oluşturur.

    Args:
        kazanim_codes: Kazanım kodları listesi (örn: ["MAT.10.1.1", "MAT.10.2.3"])
        question_count: Oluşturulacak soru sayısı (5-30 arası)
        difficulty_distribution: Zorluk dağılımı oranları (örn: {"kolay": 0.3, "orta": 0.5, "zor": 0.2})
        title: Sınav başlığı

    Returns:
        Sınav oluşturma sonucu (PDF yolu, soru detayları, kapsanan kazanımlar)
    """
    logger.info(f"Sınav oluşturuluyor: {len(kazanim_codes)} kazanım, {question_count} soru")

    try:
        # 1. Mevcut soruları index'le
        indexer = QuestionIndexer()
        available = indexer.get_questions_for_kazanimlar(kazanim_codes)

        if not available:
            return asdict(ExamGenerationResult(
                success=False,
                error="Belirtilen kazanımlar için soru bulunamadı."
            ))

        # Toplam mevcut soru sayısını kontrol et
        total_available = sum(fi.total_count for fi in available.values())
        if total_available == 0:
            return asdict(ExamGenerationResult(
                success=False,
                error="Soru klasörlerinde soru bulunamadı. Önce soruları klasörlere ekleyin."
            ))

        logger.info(f"Bulunan toplam soru: {total_available}")

        # 2. LLM ile soru seç
        selector = QuestionSelector(use_llm=True)
        selected = await selector.select(
            available=available,
            question_count=question_count,
            difficulty_distribution=difficulty_distribution or {"kolay": 0.3, "orta": 0.5, "zor": 0.2}
        )

        if not selected:
            return asdict(ExamGenerationResult(
                success=False,
                error="Soru seçimi başarısız oldu."
            ))

        logger.info(f"Seçilen soru sayısı: {len(selected)}")

        # 3. PDF oluştur
        generator = ExamPDFGenerator()
        pdf_path = generator.generate(
            questions=selected,
            title=title,
            include_answer_key=True
        )

        # 4. Sonucu döndür
        kazanimlar_covered = list(set(q.kazanim_code for q in selected))
        questions_data = [
            {
                "file": q.file_path,
                "kazanim": q.kazanim_code,
                "difficulty": q.difficulty,
                "answer": q.answer
            }
            for q in selected
        ]

        return asdict(ExamGenerationResult(
            success=True,
            pdf_path=pdf_path,
            question_count=len(selected),
            kazanimlar_covered=kazanimlar_covered,
            questions=questions_data
        ))

    except Exception as e:
        logger.error(f"Sınav oluşturma hatası: {e}", exc_info=True)
        return asdict(ExamGenerationResult(
            success=False,
            error=str(e)
        ))


class ExamGeneratorService:
    """
    Sınav oluşturma servisi.
    API ve LangGraph node'ları tarafından kullanılır.
    """

    def __init__(self):
        self.indexer = QuestionIndexer()
        self.selector = QuestionSelector(use_llm=True)
        self.generator = ExamPDFGenerator()

    async def generate(
        self,
        kazanim_codes: List[str],
        question_count: int = 10,
        difficulty_distribution: Optional[Dict[str, float]] = None,
        title: str = "Çalışma Sınavı"
    ) -> ExamGenerationResult:
        """
        Sınav oluşturur.

        Args:
            kazanim_codes: Kazanım kodları
            question_count: Soru sayısı
            difficulty_distribution: Zorluk dağılımı
            title: Sınav başlığı

        Returns:
            ExamGenerationResult
        """
        try:
            # Mevcut soruları al
            available = self.indexer.get_questions_for_kazanimlar(kazanim_codes)

            if not available:
                return ExamGenerationResult(
                    success=False,
                    error="Belirtilen kazanımlar için soru bulunamadı."
                )

            # Klasör durumlarını analiz et
            missing_folders = []
            empty_folders = []
            available_codes = []

            for code, fi in available.items():
                if not fi.folder_exists:
                    missing_folders.append(code)
                elif fi.total_count == 0:
                    empty_folders.append(code)
                else:
                    available_codes.append(code)

            total_available = sum(fi.total_count for fi in available.values())

            # Hiç soru yoksa detaylı hata ver
            if total_available == 0:
                error_parts = []
                if missing_folders:
                    # Sınıf bilgisini çıkar
                    grades = set()
                    for code in missing_folders:
                        parts = code.split(".")
                        if len(parts) >= 2:
                            try:
                                grades.add(int(parts[1]))
                            except ValueError:
                                pass
                    grade_str = ", ".join(str(g) for g in sorted(grades))
                    error_parts.append(
                        f"{len(missing_folders)} kazanım için soru klasörü bulunamadı "
                        f"(Sınıf: {grade_str}). Klasörler: {', '.join(missing_folders[:3])}"
                        f"{'...' if len(missing_folders) > 3 else ''}"
                    )
                if empty_folders:
                    error_parts.append(
                        f"{len(empty_folders)} klasör boş (soru yok)"
                    )

                return ExamGenerationResult(
                    success=False,
                    error=" | ".join(error_parts) if error_parts else "Soru klasörlerinde soru bulunamadı."
                )

            # Bazı kazanımlar eksikse uyarı logla (ama devam et)
            if missing_folders or empty_folders:
                logger.warning(
                    f"Bazı kazanımlar için soru bulunamadı. "
                    f"Eksik klasörler: {missing_folders}, Boş klasörler: {empty_folders}. "
                    f"Sadece şu kazanımlardan soru seçilecek: {available_codes}"
                )

            # Soru seç
            selected = await self.selector.select(
                available=available,
                question_count=question_count,
                difficulty_distribution=difficulty_distribution
            )

            if not selected:
                return ExamGenerationResult(
                    success=False,
                    error="Soru seçimi başarısız oldu."
                )

            # PDF oluştur
            pdf_path = self.generator.generate(
                questions=selected,
                title=title,
                include_answer_key=True
            )

            # Atlanan kazanımları belirle
            skipped = missing_folders + empty_folders
            warning_msg = None
            if skipped:
                warning_msg = (
                    f"{len(skipped)} kazanım için soru bulunamadı ve atlandı: "
                    f"{', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}"
                )

            # Sonuç
            return ExamGenerationResult(
                success=True,
                pdf_path=pdf_path,
                question_count=len(selected),
                kazanimlar_covered=list(set(q.kazanim_code for q in selected)),
                questions=[
                    {
                        "file": q.file_path,
                        "kazanim": q.kazanim_code,
                        "difficulty": q.difficulty,
                        "answer": q.answer
                    }
                    for q in selected
                ],
                skipped_kazanimlar=skipped,
                warning=warning_msg
            )

        except Exception as e:
            logger.error(f"Sınav oluşturma hatası: {e}", exc_info=True)
            return ExamGenerationResult(
                success=False,
                error=str(e)
            )

    def get_available_questions_count(self, kazanim_codes: List[str]) -> Dict[str, int]:
        """
        Kazanımlar için mevcut soru sayılarını döndürür.

        Returns:
            Kazanım kodu → soru sayısı dictionary
        """
        available = self.indexer.get_questions_for_kazanimlar(kazanim_codes)
        return {code: fi.total_count for code, fi in available.items()}
