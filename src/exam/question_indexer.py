"""
MEB RAG Sistemi - Question Indexer
Kazanım kodlarına göre soru klasörlerini tarar ve index oluşturur.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
import logging

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def parse_question_filename(filename: str) -> dict:
    """
    Dosya adından zorluk ve cevap bilgisini çıkarır.

    Format örnekleri:
        Soru1_Kolay_B.png → {"difficulty": "kolay", "answer": "B", "number": 1}
        Soru5_Zor_A.png → {"difficulty": "zor", "answer": "A", "number": 5}
        Screenshot from 2026-01-12.png → {"difficulty": "orta", "answer": None, "number": None}

    Args:
        filename: Dosya adı (uzantılı veya uzantısız)

    Returns:
        Dict with difficulty, answer, number
    """
    # Varsayılan değerler
    result = {"difficulty": "orta", "answer": None, "number": None}

    # Uzantıyı kaldır
    name = Path(filename).stem

    # Pattern: Soru{numara}_{zorluk}_{cevap}
    # Örnek: Soru1_Kolay_B, Soru10_Zor_C
    pattern = r'[Ss]oru(\d+)_([Kk]olay|[Oo]rta|[Zz]or)_([A-Ea-e])'
    match = re.search(pattern, name)

    if match:
        result["number"] = int(match.group(1))
        result["difficulty"] = match.group(2).lower()
        result["answer"] = match.group(3).upper()
    else:
        # Alternatif pattern: sadece zorluk ve cevap
        # Örnek: Kolay_B, Zor_A
        alt_pattern = r'([Kk]olay|[Oo]rta|[Zz]or)_([A-Ea-e])'
        alt_match = re.search(alt_pattern, name)
        if alt_match:
            result["difficulty"] = alt_match.group(1).lower()
            result["answer"] = alt_match.group(2).upper()

    return result


@dataclass
class QuestionInfo:
    """Soru bilgisi"""
    file_path: str
    kazanim_code: str
    difficulty: str = "orta"  # kolay, orta, zor
    answer: Optional[str] = None
    question_type: str = "coktan_secmeli"  # coktan_secmeli, acik_uclu
    analyzed: bool = False


@dataclass
class FolderIndex:
    """Klasör index bilgisi"""
    folder_path: str
    kazanim_code: str
    questions: List[QuestionInfo] = field(default_factory=list)
    total_count: int = 0
    difficulty_counts: Dict[str, int] = field(default_factory=lambda: {"kolay": 0, "orta": 0, "zor": 0})
    last_updated: str = ""
    folder_exists: bool = True  # Klasör var mı?


class QuestionIndexer:
    """Kazanım kodlarına göre soru klasörlerini tarar ve index oluşturur."""

    # Desteklenen görüntü uzantıları
    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    def __init__(self, questions_dir: Optional[str] = None):
        """
        Args:
            questions_dir: Soru klasörlerinin bulunduğu ana dizin
        """
        self.questions_dir = Path(questions_dir or getattr(settings, "exam_questions_dir", "sorular"))
        self._index_cache: Dict[str, FolderIndex] = {}

    def kazanim_to_folder(self, code: str) -> str:
        """
        Kazanım kodunu klasör adına dönüştürür.

        Örnekler:
            BIY.10.1.1.a → sorular/BIY_10_1_1/
            MAT.9.2.3.5 → sorular/MAT_9_2_3/
            FIZ.11.4.2.b → sorular/FIZ_11_4_2/

        Args:
            code: Kazanım kodu (örn: "BIY.10.1.1.a")

        Returns:
            Klasör yolu (örn: "sorular/BIY_10_1_1/")
        """
        # Nokta veya alt çizgi ile ayrılmış parçaları al
        parts = re.split(r'[._]', code)

        # İlk 4 parçayı al (ders_sınıf_ünite_konu)
        if len(parts) >= 4:
            folder_name = "_".join(parts[:4])
        else:
            folder_name = "_".join(parts)

        return str(self.questions_dir / folder_name)

    def folder_to_kazanim(self, folder_name: str) -> str:
        """
        Klasör adından kazanım kodu çıkarır.

        Args:
            folder_name: Klasör adı (örn: "BIY_10_1_1")

        Returns:
            Kazanım kodu (örn: "BIY.10.1.1")
        """
        parts = folder_name.split("_")
        return ".".join(parts)

    def scan_folder(self, folder_path: str) -> FolderIndex:
        """
        Belirli bir klasörü tarar ve index oluşturur.

        Args:
            folder_path: Taranacak klasör yolu

        Returns:
            FolderIndex nesnesi
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.warning(f"Klasör bulunamadı: {folder_path}")
            return FolderIndex(
                folder_path=folder_path,
                kazanim_code=self.folder_to_kazanim(folder.name),
                folder_exists=False  # Klasör yok işareti
            )

        kazanim_code = self.folder_to_kazanim(folder.name)
        questions: List[QuestionInfo] = []

        # Mevcut index.json varsa oku
        index_file = folder / "index.json"
        existing_index: Dict[str, QuestionInfo] = {}

        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for q in data.get("questions", []):
                        existing_index[q["file_path"]] = QuestionInfo(**q)
            except Exception as e:
                logger.warning(f"Index dosyası okunamadı: {e}")

        # Klasördeki görüntü dosyalarını tara
        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in folder.glob(f"*{ext}"):
                file_str = str(file_path)

                # Mevcut index'te varsa kullan, yoksa yeni oluştur
                if file_str in existing_index:
                    questions.append(existing_index[file_str])
                else:
                    # Dosya adından zorluk ve cevap bilgisi çıkar
                    parsed = parse_question_filename(file_path.name)
                    questions.append(QuestionInfo(
                        file_path=file_str,
                        kazanim_code=kazanim_code,
                        difficulty=parsed["difficulty"],
                        answer=parsed["answer"],
                        analyzed=True if parsed["answer"] else False
                    ))

        # Zorluk sayılarını hesapla
        difficulty_counts = {"kolay": 0, "orta": 0, "zor": 0}
        for q in questions:
            if q.difficulty in difficulty_counts:
                difficulty_counts[q.difficulty] += 1

        return FolderIndex(
            folder_path=folder_path,
            kazanim_code=kazanim_code,
            questions=questions,
            total_count=len(questions),
            difficulty_counts=difficulty_counts,
            last_updated=str(Path(folder_path).stat().st_mtime) if folder.exists() else ""
        )

    def save_index(self, folder_index: FolderIndex) -> None:
        """
        Index'i klasördeki index.json dosyasına kaydeder.

        Args:
            folder_index: Kaydedilecek FolderIndex
        """
        folder = Path(folder_index.folder_path)
        folder.mkdir(parents=True, exist_ok=True)

        index_file = folder / "index.json"
        data = {
            "kazanim_code": folder_index.kazanim_code,
            "total_count": folder_index.total_count,
            "difficulty_counts": folder_index.difficulty_counts,
            "last_updated": folder_index.last_updated,
            "questions": [asdict(q) for q in folder_index.questions]
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Index kaydedildi: {index_file}")

    def get_questions_for_kazanimlar(
        self,
        kazanim_codes: List[str],
        refresh: bool = False
    ) -> Dict[str, FolderIndex]:
        """
        Verilen kazanım kodları için mevcut soruları döndürür.

        Args:
            kazanim_codes: Kazanım kodları listesi
            refresh: True ise cache'i yenile

        Returns:
            Kazanım kodu → FolderIndex dictionary
        """
        results: Dict[str, FolderIndex] = {}

        for code in kazanim_codes:
            folder_path = self.kazanim_to_folder(code)

            # Cache kontrolü
            if not refresh and folder_path in self._index_cache:
                results[code] = self._index_cache[folder_path]
                continue

            # Klasörü tara
            folder_index = self.scan_folder(folder_path)

            # Cache'e ekle
            self._index_cache[folder_path] = folder_index
            results[code] = folder_index

        return results

    def get_all_available_questions(self) -> Dict[str, FolderIndex]:
        """
        Tüm mevcut soru klasörlerini tarar.

        Returns:
            Kazanım kodu → FolderIndex dictionary
        """
        results: Dict[str, FolderIndex] = {}

        if not self.questions_dir.exists():
            logger.warning(f"Soru dizini bulunamadı: {self.questions_dir}")
            return results

        for folder in self.questions_dir.iterdir():
            if folder.is_dir() and not folder.name.startswith("."):
                folder_index = self.scan_folder(str(folder))
                if folder_index.total_count > 0:
                    results[folder_index.kazanim_code] = folder_index

        return results

    def get_questions_by_difficulty(
        self,
        kazanim_codes: List[str],
        difficulty: str
    ) -> List[QuestionInfo]:
        """
        Belirli zorluk seviyesindeki soruları döndürür.

        Args:
            kazanim_codes: Kazanım kodları
            difficulty: Zorluk seviyesi (kolay, orta, zor)

        Returns:
            QuestionInfo listesi
        """
        all_indexes = self.get_questions_for_kazanimlar(kazanim_codes)
        questions: List[QuestionInfo] = []

        for folder_index in all_indexes.values():
            for q in folder_index.questions:
                if q.difficulty == difficulty:
                    questions.append(q)

        return questions

    def update_question_info(
        self,
        file_path: str,
        difficulty: Optional[str] = None,
        answer: Optional[str] = None,
        question_type: Optional[str] = None
    ) -> bool:
        """
        Soru bilgisini günceller ve index'i kaydeder.

        Args:
            file_path: Soru dosya yolu
            difficulty: Zorluk seviyesi
            answer: Cevap
            question_type: Soru tipi

        Returns:
            Başarılı ise True
        """
        folder_path = str(Path(file_path).parent)
        folder_index = self.scan_folder(folder_path)

        for q in folder_index.questions:
            if q.file_path == file_path:
                if difficulty:
                    q.difficulty = difficulty
                if answer:
                    q.answer = answer
                if question_type:
                    q.question_type = question_type
                q.analyzed = True

                # Index'i kaydet
                self.save_index(folder_index)

                # Cache'i güncelle
                self._index_cache[folder_path] = folder_index
                return True

        return False
