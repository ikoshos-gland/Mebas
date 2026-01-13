#!/usr/bin/env python3
"""
Test Script: Exam Generator
LLM kullanmadan doğrudan PDF oluşturmayı test eder.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exam.question_indexer import QuestionIndexer, QuestionInfo
from src.exam.question_selector import SelectedQuestion
from src.exam.pdf_generator import ExamPDFGenerator, parse_question_filename


def test_direct_pdf_generation():
    """
    LLM olmadan doğrudan PDF oluşturma testi.
    sorular/10_sinif_1_1 klasöründeki görselleri kullanır.
    """
    print("=" * 60)
    print("EXAM GENERATOR TEST - Doğrudan PDF Oluşturma")
    print("=" * 60)

    # 1. Klasördeki görselleri bul
    source_folder = project_root / "sorular" / "BİY_12_1_1"

    if not source_folder.exists():
        print(f"HATA: Klasör bulunamadı: {source_folder}")
        return False

    print(f"\n[1] Kaynak klasör: {source_folder}")

    # PNG dosyalarını listele (doğal sıralama ile - Soru1, Soru2, ... Soru10)
    import re
    def natural_sort_key(path):
        """Dosya adındaki sayıları doğru sıralar: Soru1 < Soru2 < Soru10"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', path.name)]

    image_files = sorted([
        f for f in source_folder.iterdir()
        if f.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}
    ], key=natural_sort_key)

    print(f"    Bulunan görsel sayısı: {len(image_files)}")

    if not image_files:
        print("HATA: Klasörde görsel bulunamadı!")
        return False

    for i, img in enumerate(image_files[:5], 1):  # İlk 5'i göster
        print(f"    {i}. {img.name}")
    if len(image_files) > 5:
        print(f"    ... ve {len(image_files) - 5} görsel daha")

    # 2. SelectedQuestion listesi oluştur (dosya adından zorluk/cevap parse et)
    print("\n[2] Soru listesi oluşturuluyor (dosya adından parse)...")

    questions = []
    for i, img_path in enumerate(image_files, 1):
        # Dosya adından zorluk ve cevap çıkar
        parsed = parse_question_filename(img_path.name)

        questions.append(SelectedQuestion(
            file_path=str(img_path),
            kazanim_code="BIY.10.1.1",  # Klasör adından alınabilir
            difficulty=parsed["difficulty"],
            answer=parsed["answer"],
            question_number=parsed["number"] or i
        ))

        print(f"    {i}. {img_path.name} → Zorluk: {parsed['difficulty']}, Cevap: {parsed['answer'] or 'N/A'}")

    print(f"\n    Toplam: {len(questions)} soru hazırlandı")

    # 3. PDF Generator'ı oluştur ve çalıştır
    print("\n[3] PDF oluşturuluyor...")

    generator = ExamPDFGenerator()

    try:
        pdf_path = generator.generate(
            questions=questions,
            title="10. Sınıf Biyoloji Test Sınavı",
            include_answer_key=True
        )

        print(f"    PDF başarıyla oluşturuldu!")
        print(f"    Dosya: {pdf_path}")

        # Dosya boyutunu kontrol et
        pdf_size = os.path.getsize(pdf_path)
        print(f"    Boyut: {pdf_size / 1024:.1f} KB")

        return True

    except Exception as e:
        print(f"HATA: PDF oluşturulamadı: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_question_indexer():
    """
    QuestionIndexer'ı test eder.
    """
    print("\n" + "=" * 60)
    print("QUESTION INDEXER TEST")
    print("=" * 60)

    indexer = QuestionIndexer()

    # Kazanım kodu → klasör dönüşümü
    test_codes = [
        "BIY.10.1.1",
        "MAT.9.2.3.5",
        "FIZ.11.4.2.b",
    ]

    print("\n[1] Kazanım kodu → Klasör dönüşüm testi:")
    for code in test_codes:
        folder = indexer.kazanim_to_folder(code)
        print(f"    {code} → {folder}")

    # Mevcut klasörleri tara
    print("\n[2] Mevcut soru klasörlerini tarama:")
    all_questions = indexer.get_all_available_questions()

    if all_questions:
        for code, folder_index in all_questions.items():
            print(f"    {code}: {folder_index.total_count} soru")
            print(f"        Zorluk dağılımı: {folder_index.difficulty_counts}")
    else:
        print("    Henüz indekslenmiş soru yok.")

    return True


def test_pdf_generator_fonts():
    """
    PDF Generator'ın font desteğini test eder.
    """
    print("\n" + "=" * 60)
    print("PDF GENERATOR FONT TEST")
    print("=" * 60)

    from src.exam.pdf_generator import register_fonts, FONT_PATHS

    print("\n[1] Kullanılabilir font yolları:")
    for path in FONT_PATHS:
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"    {status} {path}")

    print("\n[2] Font kaydı:")
    font_name = register_fonts()
    print(f"    Kullanılan font: {font_name}")

    return True


def main():
    """Ana test fonksiyonu."""
    print("\n" + "=" * 60)
    print("MEB RAG - EXAM GENERATOR TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Font kontrolü
    results.append(("Font Test", test_pdf_generator_fonts()))

    # Test 2: Question Indexer
    results.append(("Question Indexer", test_question_indexer()))

    # Test 3: PDF Generation
    results.append(("PDF Generation", test_direct_pdf_generation()))

    # Sonuçlar
    print("\n" + "=" * 60)
    print("TEST SONUÇLARI")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"    {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("TÜM TESTLER BAŞARILI!")
    else:
        print("BAZI TESTLER BAŞARISIZ!")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
