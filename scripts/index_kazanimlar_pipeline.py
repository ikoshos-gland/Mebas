"""
Kazanım İndexleme Pipeline (Unified)

Bu script tek bir pipeline ile:
1. data/kazanimlar_txt/ klasöründeki temiz TXT dosyalarını okur
2. Her kazanım için kitap index'inde arama yapar
3. LLM ile anahtar kelimeler çıkarır (keyword enrichment)
4. Zenginleştirilmiş kazanımları Azure Search'e indexler

Pipeline:
    TXT Files → Parse → Textbook Search → LLM Keywords → Enriched Index

Kullanım:
    python scripts/index_kazanimlar_pipeline.py
    python scripts/index_kazanimlar_pipeline.py --reset          # Önce indexi sil
    python scripts/index_kazanimlar_pipeline.py --subject BİY    # Sadece biyoloji
    python scripts/index_kazanimlar_pipeline.py --no-enrich      # Enrichment atla (hızlı)
    python scripts/index_kazanimlar_pipeline.py --dry-run        # Test modu
"""

import sys
import os
import re
import json
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings
from config.azure_config import get_search_client
from langchain_openai import AzureChatOpenAI


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Kazanim:
    """Tek bir kazanım."""
    code: str
    description: str
    parent_code: str
    grade: int
    subject: str
    semester: int
    keywords: List[str] = field(default_factory=list)
    enriched_description: str = ""
    textbook_sources: List[str] = field(default_factory=list)


@dataclass
class PipelineStats:
    """Pipeline istatistikleri."""
    total_files: int = 0
    total_kazanimlar: int = 0
    enriched_count: int = 0
    failed_enrichment: int = 0
    indexed_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    def elapsed_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()


# ============================================================================
# CONSTANTS & MAPPINGS
# ============================================================================

# Kazanım subject kodu → Kitap index subject adı
SUBJECT_CODE_TO_NAME = {
    "BİY": "biyoloji",
    "M": "matematik",
    "FİZ": "fizik",
    "KİM": "kimya",
    "T": "turkce",
    "TAR": "tarih",
    "COĞ": "cografya",
}

# Dosya adı → subject/grade mapping
FILENAME_SUBJECT_MAP = {
    "biyoloji": ("Biyoloji", "BİY"),
    "matematik": ("Matematik", "M"),
    "fizik": ("Fizik", "FİZ"),
    "kimya": ("Kimya", "KİM"),
    "turkce": ("Türkçe", "T"),
    "tarih": ("Tarih", "TAR"),
    "cografya": ("Coğrafya", "COĞ"),
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def sanitize_id(code: str) -> str:
    """Azure Search için geçerli ID oluştur."""
    code_id = code.replace(".", "_").replace("-", "_")
    # Türkçe karakterleri değiştir (ç → cc to avoid collision with c)
    for tr_char, en_char in [("İ", "I"), ("ı", "i"), ("Ğ", "G"), ("ğ", "g"),
                              ("Ü", "U"), ("ü", "u"), ("Ş", "S"), ("ş", "s"),
                              ("Ö", "O"), ("ö", "o"), ("Ç", "CC"), ("ç", "cc")]:
        code_id = code_id.replace(tr_char, en_char)
    return code_id


def get_textbook_subject(kazanim_subject: str) -> str:
    """Kazanım subject kodunu kitap index subject adına çevir."""
    return SUBJECT_CODE_TO_NAME.get(kazanim_subject, kazanim_subject.lower())


def parse_metadata_from_filename(filename: str) -> dict:
    """Dosya adından metadata çıkar."""
    stem = Path(filename).stem.replace("_kazanimlar", "")
    parts = stem.split('_')

    metadata = {
        "subject": "?",
        "subject_code": "?",
        "grade": 0,
        "semester": 0
    }

    if len(parts) >= 2:
        subject_lower = parts[0].lower()
        if subject_lower in FILENAME_SUBJECT_MAP:
            metadata["subject"], metadata["subject_code"] = FILENAME_SUBJECT_MAP[subject_lower]
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


# ============================================================================
# TXT PARSING
# ============================================================================

def parse_txt_file(txt_path: Path, metadata: dict) -> List[Kazanim]:
    """
    Temiz txt dosyasını parse et ve Kazanim listesi döndür.

    Format:
        BİY.10.1.1. Ana kazanım başlığı
            a) Alt kazanım açıklaması
            b) Alt kazanım açıklaması
    """
    kazanimlar = []

    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    current_main = None
    current_main_title = None
    in_content = False

    for line in lines:
        line_stripped = line.strip()

        # Header bölümünü atla
        if line_stripped.startswith("="):
            in_content = True
            continue

        if not in_content:
            continue

        # ÖZET bölümüne geldiğinde dur
        if line_stripped == "ÖZET":
            break

        # Ana kazanım: BİY.10.1.1. Başlık
        main_match = re.match(r'^([A-ZİĞÜŞÖÇ]+\.\d+\.\d+\.\d+)\.?\s*(.+)$', line_stripped)
        if main_match:
            current_main = main_match.group(1)
            current_main_title = main_match.group(2).strip()

            # Ana kazanımı ekle
            kazanimlar.append(Kazanim(
                code=current_main,
                description=current_main_title,
                parent_code=current_main,
                grade=metadata['grade'],
                subject=metadata['subject_code'],
                semester=metadata['semester']
            ))
            continue

        # Alt kazanım: a) Açıklama
        if line.startswith("    ") and kazanimlar:
            sub_match = re.match(r'^\s+([a-zçğıöşü])\)\s*(.+)$', line)
            if sub_match:
                letter = sub_match.group(1)
                description = sub_match.group(2).strip()
                sub_code = f"{current_main}.{letter}"

                kazanimlar.append(Kazanim(
                    code=sub_code,
                    description=description,
                    parent_code=current_main,
                    grade=metadata['grade'],
                    subject=metadata['subject_code'],
                    semester=metadata['semester']
                ))

    return kazanimlar


# ============================================================================
# KEYWORD ENRICHMENT (LLM)
# ============================================================================

def get_llm():
    """Azure OpenAI LLM instance."""
    settings = get_settings()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0.3,
        max_tokens=500
    )


async def search_textbook_for_kazanim(
    kazanim: Kazanim,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Kazanım için kitap index'inde arama yap."""
    settings = get_settings()
    client = get_search_client(settings.azure_search_index_kitap)

    search_text = f"{kazanim.description} {kazanim.code}"
    textbook_subject = get_textbook_subject(kazanim.subject)

    # Grade filter: Kazanımın sınıfı ve bir önceki sınıf
    min_grade = max(9, kazanim.grade - 1)
    filter_str = f"grade ge {min_grade} and grade le {kazanim.grade} and subject eq '{textbook_subject}'"

    try:
        results = client.search(
            search_text=search_text,
            filter=filter_str,
            query_type="semantic",
            semantic_configuration_name="semantic-config",
            top=top_k,
            select=["content", "hierarchy_path", "page_range", "grade", "textbook_name"]
        )

        return [
            {
                "content": r.get("content", "")[:2000],
                "hierarchy_path": r.get("hierarchy_path", ""),
                "page_range": r.get("page_range", ""),
                "grade": r.get("grade"),
                "textbook": r.get("textbook_name", "")
            }
            for r in results
        ]
    except Exception as e:
        print(f"      ⚠️ Kitap araması hatası: {e}")
        return []


async def extract_keywords_with_llm(
    kazanim: Kazanim,
    textbook_contents: List[Dict[str, Any]],
    llm: AzureChatOpenAI
) -> List[str]:
    """LLM kullanarak kitap içeriklerinden anahtar kelimeleri çıkar."""
    if not textbook_contents:
        return []

    content_text = "\n\n---\n\n".join([
        f"[{c['hierarchy_path']} - Sayfa {c['page_range']}]\n{c['content']}"
        for c in textbook_contents
    ])

    prompt = f"""Sen bir MEB müfredat uzmanısın. Aşağıdaki kazanım ve ilgili ders kitabı içeriklerini analiz et.

KAZANIM:
Kod: {kazanim.code}
Açıklama: {kazanim.description}

DERS KİTABI İÇERİKLERİ:
{content_text}

GÖREV:
Bu kazanımı öğrencilerin sorularıyla eşleştirmek için kullanılacak ANAHTAR KELİMELER listesi oluştur.

KURALLAR:
1. Kitap içeriklerinden SOMUT terimler çıkar (örn: "kalp", "kapakçık", "biküspit", "aort")
2. Soyut/genel terimlerden kaçın (örn: "sistem", "süreç", "model")
3. Türkçe ve Latince/bilimsel terimlerin ikisini de dahil et
4. 10-20 arasında anahtar kelime ver
5. Kelimeler küçük harfle, virgülle ayrılmış olsun

SADECE anahtar kelimeleri virgülle ayırarak yaz, başka bir şey yazma.
Örnek format: kalp, kapakçık, biküspit, triküspit, aort, pulmoner"""

    try:
        response = await asyncio.to_thread(llm.invoke, prompt)
        keywords_text = response.content.strip()
        keywords = [k.strip().lower() for k in keywords_text.split(",")]
        keywords = [k for k in keywords if len(k) > 2]
        return keywords[:20]
    except Exception as e:
        print(f"      ⚠️ LLM hatası: {e}")
        return []


async def enrich_kazanim(
    kazanim: Kazanim,
    llm: AzureChatOpenAI,
    verbose: bool = False
) -> bool:
    """
    Tek bir kazanımı zenginleştir.
    Returns True if successful, False otherwise.
    """
    # 1. Kitap araması
    textbook_results = await search_textbook_for_kazanim(kazanim)

    if not textbook_results:
        if verbose:
            print(f"      ⚠️ Kitap içeriği bulunamadı")
        return False

    # 2. LLM ile keyword extraction
    keywords = await extract_keywords_with_llm(kazanim, textbook_results, llm)

    if not keywords:
        if verbose:
            print(f"      ⚠️ Keyword çıkarılamadı")
        return False

    # 3. Kazanımı güncelle
    kazanim.keywords = keywords
    kazanim.enriched_description = f"{kazanim.description} | Anahtar Kavramlar: {', '.join(keywords)}"
    kazanim.textbook_sources = [
        f"{r['textbook']} - {r['hierarchy_path']} (s.{r['page_range']})"
        for r in textbook_results
    ]

    if verbose:
        print(f"      ✅ {len(keywords)} keyword: {', '.join(keywords[:5])}...")

    return True


# ============================================================================
# INDEXING
# ============================================================================

def index_kazanimlar_batch(kazanimlar: List[Kazanim], use_enriched: bool = True) -> int:
    """Kazanımları Azure Search'e batch olarak indexle."""
    from src.vector_store.indexing_pipeline import IndexingPipeline

    pipeline = IndexingPipeline()

    docs = []
    for k in kazanimlar:
        # Use enriched description if available, otherwise original
        description = k.enriched_description if (use_enriched and k.enriched_description) else k.description

        docs.append({
            "id": sanitize_id(k.code),
            "code": k.code,
            "parent_code": k.parent_code,
            "description": description,
            "title": k.description,  # Original description as title
            "grade": k.grade,
            "subject": k.subject,
            "semester": k.semester
        })

    # Index
    if docs:
        pipeline.index_kazanimlar_raw(docs)

    return len(docs)


# ============================================================================
# MAIN PIPELINE
# ============================================================================

async def process_single_file(
    txt_path: Path,
    llm: Optional[AzureChatOpenAI],
    stats: PipelineStats,
    enrich: bool = True,
    verbose: bool = False
) -> List[Kazanim]:
    """Tek bir TXT dosyasını işle."""
    print(f"\n📄 {txt_path.name}")

    # 1. Parse metadata
    metadata = parse_metadata_from_filename(txt_path.name)
    print(f"   Ders: {metadata['subject']} ({metadata['subject_code']}), "
          f"Sınıf: {metadata['grade']}, Dönem: {metadata['semester']}")

    # 2. Parse kazanımlar
    kazanimlar = parse_txt_file(txt_path, metadata)
    main_count = len([k for k in kazanimlar if k.code == k.parent_code])
    sub_count = len(kazanimlar) - main_count
    print(f"   └─ {main_count} ana + {sub_count} alt = {len(kazanimlar)} kazanım parse edildi")

    stats.total_kazanimlar += len(kazanimlar)

    # 3. Enrich with keywords (optional)
    if enrich and llm:
        print(f"   └─ Keyword enrichment başlıyor...")
        enriched = 0
        failed = 0

        for i, kazanim in enumerate(kazanimlar):
            if verbose:
                print(f"      [{i+1}/{len(kazanimlar)}] {kazanim.code}")

            success = await enrich_kazanim(kazanim, llm, verbose)
            if success:
                enriched += 1
            else:
                failed += 1

            # Rate limiting
            await asyncio.sleep(0.3)

            # Progress indicator
            if not verbose and (i + 1) % 10 == 0:
                print(f"      İlerleme: {i+1}/{len(kazanimlar)}")

        print(f"   └─ Enrichment: {enriched} başarılı, {failed} başarısız")
        stats.enriched_count += enriched
        stats.failed_enrichment += failed

    return kazanimlar


async def run_pipeline(args):
    """Ana pipeline."""
    print("=" * 70)
    print("KAZANIM İNDEXLEME PİPELİNE")
    print("TXT → LLM Enrichment → Azure Search")
    print("=" * 70)

    stats = PipelineStats()

    # 1. TXT dosyalarını bul
    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"\n❌ Klasör bulunamadı: {input_dir}")
        print("Önce extract_kazanimlar_to_txt.py çalıştırın.")
        return

    txt_files = sorted(input_dir.glob("*_kazanimlar.txt"))

    # Subject filter
    if args.subject:
        subject_lower = args.subject.lower()
        txt_files = [f for f in txt_files if subject_lower in f.name.lower()]

    if not txt_files:
        print("\n❌ TXT dosyası bulunamadı!")
        return

    stats.total_files = len(txt_files)
    print(f"\n📚 {len(txt_files)} TXT dosyası işlenecek")

    # 2. LLM hazırla (enrichment için)
    llm = None
    if not args.no_enrich:
        print("\n🤖 LLM hazırlanıyor...")
        llm = get_llm()
        print("   └─ ✅ Azure OpenAI bağlantısı kuruldu")
    else:
        print("\n⚡ Enrichment atlanıyor (--no-enrich)")

    # 3. Index reset (optional)
    if args.reset and not args.dry_run:
        print("\n🗑️ Kazanım indexi sıfırlanıyor...")
        from src.vector_store.indexing_pipeline import IndexingPipeline
        pipeline = IndexingPipeline()
        pipeline.delete_indexes("kazanim")
        pipeline.create_all_indexes()
        print("   └─ ✅ Index yeniden oluşturuldu")

    # 4. Her dosyayı işle
    all_kazanimlar: List[Kazanim] = []

    for txt_path in txt_files:
        try:
            kazanimlar = await process_single_file(
                txt_path=txt_path,
                llm=llm,
                stats=stats,
                enrich=not args.no_enrich,
                verbose=args.verbose
            )
            all_kazanimlar.extend(kazanimlar)
        except Exception as e:
            print(f"   └─ ❌ Hata: {e}")
            import traceback
            traceback.print_exc()

    # 5. Index
    if args.dry_run:
        print("\n🔍 DRY RUN - Index işlemi yapılmayacak")
        print(f"   Toplam {len(all_kazanimlar)} kazanım indexlenecekti")

        # Show sample
        enriched_samples = [k for k in all_kazanimlar if k.keywords][:3]
        if enriched_samples:
            print("\n   Örnek zenginleştirilmiş kazanımlar:")
            for k in enriched_samples:
                print(f"\n   {k.code}:")
                print(f"   Original: {k.description[:60]}...")
                print(f"   Keywords: {', '.join(k.keywords[:8])}...")
    else:
        print(f"\n📤 Azure Search'e indexleniyor...")
        indexed = index_kazanimlar_batch(all_kazanimlar, use_enriched=not args.no_enrich)
        stats.indexed_count = indexed
        print(f"   └─ ✅ {indexed} kazanım indexlendi")

    # 6. Rapor kaydet
    if not args.dry_run:
        report_path = Path(args.output)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_files": stats.total_files,
                "total_kazanimlar": stats.total_kazanimlar,
                "enriched_count": stats.enriched_count,
                "failed_enrichment": stats.failed_enrichment,
                "indexed_count": stats.indexed_count,
                "elapsed_seconds": stats.elapsed_seconds()
            },
            "kazanimlar": [
                {
                    "code": k.code,
                    "description": k.description,
                    "keywords": k.keywords,
                    "enriched": bool(k.keywords),
                    "grade": k.grade,
                    "subject": k.subject
                }
                for k in all_kazanimlar
            ]
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 Rapor kaydedildi: {report_path}")

    # 7. Özet
    print("\n" + "=" * 70)
    print("ÖZET")
    print("=" * 70)
    print(f"İşlenen dosya: {stats.total_files}")
    print(f"Toplam kazanım: {stats.total_kazanimlar}")
    if not args.no_enrich:
        print(f"Zenginleştirilen: {stats.enriched_count}")
        print(f"Enrichment başarısız: {stats.failed_enrichment}")
    if not args.dry_run:
        print(f"İndexlenen: {stats.indexed_count}")
    print(f"Süre: {stats.elapsed_seconds():.1f} saniye")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Kazanım İndexleme Pipeline (TXT → LLM Enrichment → Azure Search)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/index_kazanimlar_pipeline.py                    # Tüm pipeline
  python scripts/index_kazanimlar_pipeline.py --reset            # Önce indexi sil
  python scripts/index_kazanimlar_pipeline.py --subject BİY      # Sadece biyoloji
  python scripts/index_kazanimlar_pipeline.py --no-enrich        # Enrichment atla (hızlı)
  python scripts/index_kazanimlar_pipeline.py --dry-run          # Test modu
  python scripts/index_kazanimlar_pipeline.py --verbose          # Detaylı çıktı

Pipeline Adımları:
  1. TXT dosyalarını oku (data/kazanimlar_txt/)
  2. Kazanımları parse et
  3. Her kazanım için kitap araması yap
  4. LLM ile anahtar kelimeler çıkar
  5. Zenginleştirilmiş kazanımları indexle
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        default="data/kazanimlar_txt",
        help="TXT dosyalarının klasörü (varsayılan: data/kazanimlar_txt)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/kazanim_pipeline_report.json",
        help="Rapor dosyası (varsayılan: data/kazanim_pipeline_report.json)"
    )

    parser.add_argument(
        "--subject", "-s",
        type=str,
        help="Sadece belirli ders (örn: BİY, biyoloji)"
    )

    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Önce kazanım indexini sil"
    )

    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="LLM keyword enrichment atla (hızlı indexleme)"
    )

    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Index işlemi yapmadan test et"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Detaylı çıktı göster"
    )

    args = parser.parse_args()
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
