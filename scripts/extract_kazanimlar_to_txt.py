"""
MEB Kazanım PDF'lerinden Temiz TXT Çıkarma Script'i

Bu script:
1. data/pdfs/kazanimlar/ klasöründeki tüm PDF'leri okur
2. Azure Document Intelligence ile metin çıkarır
3. "Öğrenme Çıktıları ve Süreç Bileşenleri" bölümünü parse eder
4. Her PDF için temiz bir .txt dosyası oluşturur

Kullanım:
    python scripts/extract_kazanimlar_to_txt.py
    python scripts/extract_kazanimlar_to_txt.py --output data/kazanimlar_txt/
"""

import sys
import os
import re
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from config.settings import get_settings


def extract_text_from_pdf(pdf_path: Path, doc_client) -> str:
    """Azure Document Intelligence ile PDF'den metin çıkar."""
    print(f"   └─ Azure Document Intelligence ile metin çıkarılıyor...")

    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    poller = doc_client.begin_analyze_document(
        'prebuilt-layout',
        AnalyzeDocumentRequest(bytes_source=pdf_bytes)
    )
    result = poller.result()

    return result.content


def parse_metadata_from_filename(filename: str) -> dict:
    """Dosya adından metadata çıkar."""
    # biyoloji_10.1.pdf -> subject=biyoloji, grade=10, semester=1
    stem = Path(filename).stem
    parts = stem.split('_')

    metadata = {
        "subject": "bilinmiyor",
        "subject_code": "?",
        "grade": 0,
        "semester": 0
    }

    subject_map = {
        "biyoloji": ("Biyoloji", "BİY"),
        "matematik": ("Matematik", "M"),
        "fizik": ("Fizik", "FİZ"),
        "kimya": ("Kimya", "KİM"),
        "turkce": ("Türkçe", "T"),
        "tarih": ("Tarih", "TAR"),
        "cografya": ("Coğrafya", "COĞ"),
    }

    if len(parts) >= 2:
        subject_lower = parts[0].lower()
        if subject_lower in subject_map:
            metadata["subject"], metadata["subject_code"] = subject_map[subject_lower]
        else:
            metadata["subject"] = parts[0].capitalize()
            metadata["subject_code"] = parts[0][:3].upper()

        grade_part = parts[1]
        if '.' in grade_part:
            grade_semester = grade_part.split('.')
            try:
                metadata["grade"] = int(grade_semester[0])
                metadata["semester"] = int(grade_semester[1])
            except (ValueError, IndexError):
                pass
        else:
            try:
                metadata["grade"] = int(grade_part)
            except ValueError:
                pass

    return metadata


def parse_kazanimlar(text: str, metadata: dict) -> list:
    """
    Metinden kazanımları parse et.
    Sadece "Öğrenme Çıktıları ve Süreç Bileşenleri" bölümünü al.
    """
    kazanimlar = []

    # "Öğrenme Çıktıları ve Süreç Bileşenleri" bölümünü bul
    start_marker = "Öğrenme Çıktıları ve Süreç Bileşenleri"
    end_markers = ["İçerik Çerçevesi", "Öğrenme Kanıtları", "Öğrenme-Öğretme"]

    start_idx = text.find(start_marker)
    if start_idx == -1:
        print("   ⚠️ 'Öğrenme Çıktıları ve Süreç Bileşenleri' bölümü bulunamadı!")
        return kazanimlar

    # Bölümün sonunu bul
    end_idx = len(text)
    for marker in end_markers:
        idx = text.find(marker, start_idx + len(start_marker))
        if idx != -1 and idx < end_idx:
            end_idx = idx

    section_text = text[start_idx:end_idx]

    # Ana kazanım pattern: BİY.10.1.1. veya M.9.1.1. gibi
    # Format: KOD. Başlık
    main_pattern = r'([A-ZİĞÜŞÖÇ]+\.\d+\.\d+\.\d+)\.\s*(.+?)(?=\n[a-zçğıöşü]\)|\n[A-ZİĞÜŞÖÇ]+\.\d+\.\d+\.\d+\.|\Z)'

    # Alt kazanım pattern: a) metin, b) metin, ç) metin
    sub_pattern = r'([a-zçğıöşü])\)\s*(.+?)(?=\n[a-zçğıöşü]\)|\n[A-ZİĞÜŞÖÇ]+\.\d+|\nİçerik|\nÖğrenme|\Z)'

    # Satır satır işle
    lines = section_text.split('\n')
    current_main = None
    current_main_title = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Ana kazanım kontrolü
        main_match = re.match(r'^([A-ZİĞÜŞÖÇ]+\.\d+\.\d+\.\d+)\.\s*(.+)$', line)
        if main_match:
            current_main = main_match.group(1)
            current_main_title = main_match.group(2).strip()
            kazanimlar.append({
                "code": current_main,
                "title": current_main_title,
                "sub_items": []
            })
            i += 1
            continue

        # Alt kazanım kontrolü
        sub_match = re.match(r'^([a-zçğıöşü])\)\s*(.+)$', line)
        if sub_match and kazanimlar:
            letter = sub_match.group(1)
            description = sub_match.group(2).strip()

            # Sonraki satırları da kontrol et (devam eden açıklama)
            while i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Eğer yeni bir alt kazanım veya ana kazanım değilse, devamı
                if not re.match(r'^[a-zçğıöşü]\)', next_line) and not re.match(r'^[A-ZİĞÜŞÖÇ]+\.\d+', next_line):
                    if next_line and not next_line.startswith('http') and not re.match(r'^\d+/\d+$', next_line):
                        description += ' ' + next_line
                        i += 1
                    else:
                        break
                else:
                    break

            kazanimlar[-1]["sub_items"].append({
                "letter": letter,
                "description": description
            })

        i += 1

    return kazanimlar


def format_output(kazanimlar: list, metadata: dict) -> str:
    """Kazanımları temiz formatta string'e çevir."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"{metadata['subject'].upper()} {metadata['grade']}. SINIF - {metadata['semester']}. DÖNEM")
    lines.append("KAZANIM LİSTESİ (Öğrenme Çıktıları ve Süreç Bileşenleri)")
    lines.append("=" * 80)
    lines.append("")

    # Kazanımlar
    total_sub = 0
    for kaz in kazanimlar:
        lines.append(f"{kaz['code']}. {kaz['title']}")
        for sub in kaz['sub_items']:
            lines.append(f"    {sub['letter']}) {sub['description']}")
            total_sub += 1
        lines.append("")

    # Summary
    lines.append("=" * 80)
    lines.append("ÖZET")
    lines.append("=" * 80)
    lines.append(f"Toplam Ana Kazanım: {len(kazanimlar)}")
    lines.append(f"Toplam Alt Kazanım: {total_sub}")
    lines.append("")
    lines.append("Kazanım Dağılımı:")
    for kaz in kazanimlar:
        sub_letters = ", ".join([s['letter'] for s in kaz['sub_items']])
        lines.append(f"  - {kaz['code']}: {len(kaz['sub_items'])} alt kazanım ({sub_letters})")
    lines.append("=" * 80)

    return "\n".join(lines)


def process_single_pdf(pdf_path: Path, doc_client, output_dir: Path) -> dict:
    """Tek bir PDF'i işle ve txt oluştur."""
    print(f"\n📑 İşleniyor: {pdf_path.name}")

    # Metadata
    metadata = parse_metadata_from_filename(pdf_path.name)
    print(f"   └─ Ders: {metadata['subject']}, Sınıf: {metadata['grade']}, Dönem: {metadata['semester']}")

    # Metin çıkar
    text = extract_text_from_pdf(pdf_path, doc_client)
    print(f"   └─ {len(text)} karakter metin çıkarıldı")

    # Kazanımları parse et
    kazanimlar = parse_kazanimlar(text, metadata)
    total_sub = sum(len(k['sub_items']) for k in kazanimlar)
    print(f"   └─ {len(kazanimlar)} ana kazanım, {total_sub} alt kazanım bulundu")

    # Format ve kaydet
    output_text = format_output(kazanimlar, metadata)

    output_filename = pdf_path.stem + "_kazanimlar.txt"
    output_path = output_dir / output_filename

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_text)

    print(f"   └─ ✅ Kaydedildi: {output_path}")

    return {
        "file": pdf_path.name,
        "main_count": len(kazanimlar),
        "sub_count": total_sub,
        "output": str(output_path)
    }


def main():
    parser = argparse.ArgumentParser(
        description="MEB Kazanım PDF'lerinden temiz TXT çıkarma",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        default="data/pdfs/kazanimlar",
        help="Kazanım PDF'lerinin bulunduğu klasör (varsayılan: data/pdfs/kazanimlar)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/kazanimlar_txt",
        help="Çıktı TXT dosyalarının kaydedileceği klasör (varsayılan: data/kazanimlar_txt)"
    )

    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Sadece belirli bir PDF'i işle"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("MEB Kazanım PDF -> TXT Çıkarma")
    print("=" * 60)

    # Azure client
    settings = get_settings()
    doc_client = DocumentIntelligenceClient(
        endpoint=settings.documentintelligence_endpoint,
        credential=AzureKeyCredential(settings.documentintelligence_api_key)
    )

    # Output klasörü
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # PDF'leri bul
    if args.file:
        pdf_files = [Path(args.file)]
    else:
        input_dir = Path(args.input)
        pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print("⚠️ PDF dosyası bulunamadı!")
        return

    print(f"\n📚 {len(pdf_files)} PDF işlenecek\n")

    # İşle
    results = []
    for pdf_path in pdf_files:
        try:
            result = process_single_pdf(pdf_path, doc_client, output_dir)
            results.append(result)
        except Exception as e:
            print(f"   └─ ❌ Hata: {e}")
            import traceback
            traceback.print_exc()

    # Özet
    print("\n" + "=" * 60)
    print("SONUÇ")
    print("=" * 60)

    total_main = sum(r['main_count'] for r in results)
    total_sub = sum(r['sub_count'] for r in results)

    print(f"İşlenen PDF: {len(results)}")
    print(f"Toplam Ana Kazanım: {total_main}")
    print(f"Toplam Alt Kazanım: {total_sub}")
    print(f"Çıktı klasörü: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
