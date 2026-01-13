"""
MEB RAG System - PDF Processing and Indexing Script

This script processes PDF textbooks from data/pdfs directory:
1. Analyzes layout using Azure Document Intelligence
2. Extracts images using PyMuPDF (fitz)
3. Generates semantic chunks preserving hierarchy
4. Indexes content and images to Azure AI Search

Usage:
    python scripts/process_pdfs.py
"""
import sys
import os
import asyncio
import glob
import json
import logging
from pathlib import Path
from dataclasses import asdict

# Configure logging to show retry attempts
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from config.settings import get_settings
from src.document_processing.layout_analyzer import LayoutAnalyzer
from src.document_processing.image_extractor import ImageExtractor
from src.document_processing.semantic_chunker import SemanticChunker, SemanticChunk
from src.document_processing.pdf_splitter import PDFSplitter
from src.vector_store.indexing_pipeline import IndexingPipeline


import re
import uuid
from typing import List
from src.vector_store.question_generator import SyntheticQuestionGenerator


# ============== PROCESSED FILES TRACKING ==============
PROCESSED_STATE_FILE = Path("data/.processed_pdfs.json")


def load_processed_files() -> dict:
    """Load the set of already processed PDF files."""
    if PROCESSED_STATE_FILE.exists():
        try:
            with open(PROCESSED_STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"kazanim": [], "kitap": []}
    return {"kazanim": [], "kitap": []}


def save_processed_file(pdf_path: Path, file_type: str):
    """Mark a PDF as processed."""
    state = load_processed_files()
    pdf_key = str(pdf_path.absolute())

    if file_type not in state:
        state[file_type] = []

    if pdf_key not in state[file_type]:
        state[file_type].append(pdf_key)

        # Ensure parent directory exists
        PROCESSED_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(PROCESSED_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        print(f"   💾 Saved progress: {pdf_path.name}")


def is_already_processed(pdf_path: Path, file_type: str) -> bool:
    """Check if a PDF has already been processed."""
    state = load_processed_files()
    pdf_key = str(pdf_path.absolute())
    return pdf_key in state.get(file_type, [])


def clear_processed_state(mode: str = "all"):
    """Clear processed files state based on mode."""
    if mode == "all":
        if PROCESSED_STATE_FILE.exists():
            PROCESSED_STATE_FILE.unlink()
            print("🗑️  Cleared ALL processed files state")
    else:
        state = load_processed_files()
        if mode in state:
            state[mode] = []
            with open(PROCESSED_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
            print(f"🗑️  Cleared {mode} processed files state")


def parse_filename(filename: str) -> dict:
    """
    Parse filename to extract metadata.
    Expected formats:
    - subject_grade.pdf (e.g., biyoloji_9.pdf)
    - subject_grade.semester.pdf (e.g., biyoloji_9.1.pdf, biyoloji_10.2.pdf)
    - subject_grade.semester_partN.pdf (e.g., biyoloji_11.1_part1.pdf)
    """
    import hashlib

    stem = Path(filename).stem  # e.g., "biyoloji_9.1" or "biyoloji_11.1_part1"

    # Check if this is a split PDF (has _partN suffix)
    split_metadata_path = Path("data/pdfs/ders_kitaplari/split_metadata.json")
    page_offset = 0

    if "_part" in stem and split_metadata_path.exists():
        # Load split metadata
        with open(split_metadata_path, "r", encoding="utf-8") as f:
            split_metadata = json.load(f)

        file_key = f"{stem}.pdf"
        if file_key in split_metadata:
            # Use original name for consistent textbook_id
            original_name = split_metadata[file_key]["original_name"]
            page_offset = split_metadata[file_key]["page_offset"]
            stem = original_name  # Override stem to use base name
            print(f"   📋 Split PDF detected: using base name '{original_name}' with page offset {page_offset}")

    # Generate DETERMINISTIC numeric textbook_id using MD5
    # Python's hash() is not deterministic across runs/systems!
    md5_hash = hashlib.md5(stem.encode('utf-8')).hexdigest()
    textbook_id_hash = int(md5_hash[:8], 16) % (10**8)  # 8-digit positive integer

    metadata = {
        "subject": "genel",
        "grade": 0,
        "semester": 0,  # 0 = unknown, 1 = 1. dönem, 2 = 2. dönem
        "textbook_id": textbook_id_hash,
        "textbook_name": stem,  # Use original name for display
        "page_offset": page_offset  # NEW: page offset for split PDFs
    }

    # Split by underscore to get subject and grade parts
    parts = stem.split('_')

    if len(parts) >= 2:
        metadata["subject"] = parts[0]  # e.g., "biyoloji"

        # The grade part might be "9" or "9.1" (grade.semester)
        grade_part = parts[1]  # e.g., "9" or "9.1"

        if '.' in grade_part:
            # Format: subject_grade.semester.pdf (e.g., biyoloji_9.1.pdf)
            grade_semester = grade_part.split('.')
            try:
                metadata["grade"] = int(grade_semester[0])
                metadata["semester"] = int(grade_semester[1])
            except (ValueError, IndexError):
                pass
        else:
            # Format: subject_grade.pdf (e.g., biyoloji_9.pdf)
            try:
                metadata["grade"] = int(grade_part)
            except ValueError:
                pass

    return metadata


async def extract_kazanimlar_with_llm(full_text: str, grade: int, subject: str, semester: int) -> List[dict]:
    """
    Use LLM to intelligently extract kazanımlar from PDF text.
    This method understands document structure and extracts only actual
    kazanım definitions from "Öğrenme Çıktıları ve Süreç Bileşenleri" section,
    ignoring teaching instructions.
    """
    from langchain_openai import AzureChatOpenAI
    from config.settings import get_settings
    import json

    settings = get_settings()

    llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        deployment_name=settings.azure_openai_chat_deployment,
        temperature=0
    )

    # Truncate text if too long (keep first ~50k chars which should have kazanım definitions)
    text_for_llm = full_text[:50000] if len(full_text) > 50000 else full_text

    prompt = f"""Aşağıdaki MEB müfredat PDF metninden SADECE "Öğrenme Çıktıları ve Süreç Bileşenleri" bölümündeki kazanımları çıkar.

DİKKAT:
- "Öğrenme-Öğretme Uygulamaları" bölümünü ATLA (bu öğretim talimatlarıdır, kazanım değil)
- Her kazanım kodu (örn: BİY.10.1.1) ve alt öğeleri (a, b, c, ç, d) ayrı ayrı çıkar
- Açıklama olarak SADECE kazanımın kısa tanımını yaz (örn: "Canlıların yaşamına devam edebilmesi için enerjinin gerekliliğiyle ilgili merakını ifade eder.")
- Öğretim talimatları, etkinlik açıklamaları veya (E1.1), (OB1) gibi referansları DAHİL ETME

JSON formatında döndür:
{{
  "kazanimlar": [
    {{
      "code": "BİY.10.1.1.a",
      "parent_code": "BİY.10.1.1",
      "title": "Ana kazanım başlığı",
      "description": "Alt öğe açıklaması (kısa, tek cümle)"
    }}
  ]
}}

PDF Metni:
{text_for_llm}
"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            kazanimlar = data.get("kazanimlar", [])

            # Add metadata
            result = []
            seen_codes = set()
            for k in kazanimlar:
                code = k.get("code", "")
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                # Generate deterministic ID (remove all Turkish special chars)
                code_id = code.replace(".", "_").replace("-", "_")
                # Replace Turkish chars (both upper and lower case)
                for tr_char, en_char in [("İ", "I"), ("ı", "i"), ("Ğ", "G"), ("ğ", "g"), ("Ü", "U"), ("ü", "u"), ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"), ("Ç", "C"), ("ç", "c")]:
                    code_id = code_id.replace(tr_char, en_char)

                result.append({
                    "id": code_id,
                    "code": code,
                    "parent_code": k.get("parent_code", code),
                    "description": k.get("description", ""),
                    "title": k.get("title", ""),
                    "grade": grade,
                    "subject": subject,
                    "semester": semester
                })

            print(f"   └─ LLM extracted {len(result)} kazanımlar")
            return result
        else:
            print("   ⚠️ LLM response did not contain valid JSON")
            return []
    except Exception as e:
        print(f"   ⚠️ LLM extraction failed: {e}")
        return []


def clean_kazanim_description(content: str) -> str:
    """
    Clean kazanım description by extracting only the actual learning objective.
    Removes teaching instructions, markers like (E1.1), (OB1), etc.
    """
    # Remove common teaching instruction markers
    # These appear in Turkish curriculum documents as pedagogical references
    markers_pattern = r'\s*\([A-ZÇĞİÖŞÜ]+\d+(?:\.\d+)*\)\s*'
    content = re.sub(markers_pattern, ' ', content)

    # Remove patterns like "E1.1", "OB1", "D20.2" without parentheses
    content = re.sub(r'\b[A-ZÇĞİÖŞÜ]+\d+(?:\.\d+)*\b', '', content)

    # Clean up multiple spaces
    content = re.sub(r'\s+', ' ', content).strip()

    # Extract first sentence (ends with period followed by space or end)
    # Turkish sentences end with . ! or ?
    first_sentence_match = re.match(r'^(.+?[.!?])(?:\s|$)', content)
    if first_sentence_match:
        first_sentence = first_sentence_match.group(1).strip()
        # If first sentence is reasonable length, use it
        if 20 <= len(first_sentence) <= 500:
            return first_sentence

    # If no good first sentence found, take first 300 chars at word boundary
    if len(content) > 300:
        # Find the last space before 300 chars
        truncated = content[:300]
        last_space = truncated.rfind(' ')
        if last_space > 200:
            return truncated[:last_space] + '...'
        return truncated + '...'

    return content


async def process_kazanim_pdf(
    pdf_path: Path,
    settings,
    doc_client,
    pipeline,
    use_llm: bool = False
):
    """
    Process kazanım PDF files.

    Args:
        use_llm: If True, use LLM to intelligently extract kazanımlar.
                 This is more accurate but slower and costs API calls.
                 If False, use regex-based extraction (faster but less accurate).
    """
    print(f"\n📑 Processing Kazanim File: {pdf_path.name}")
    print(f"   └─ Extraction mode: {'LLM (intelligent)' if use_llm else 'Regex (fast)'}")
    
    # Extract semester from filename
    file_metadata = parse_filename(pdf_path.name)
    semester = file_metadata.get("semester", 0)
    print(f"   └─ Semester: {semester if semester > 0 else 'Unknown'}")
    
    # 1. Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    # 2. Extract Text (Simple Layout Analysis)
    print("   └─ Extracting text (Azure Document Intelligence)...")
    analyzer = LayoutAnalyzer()
    result = await analyzer.analyze_document(doc_client, pdf_bytes)
    
    # Simple text extraction for regex parsing
    full_text = ""
    if result.content:
        full_text = result.content
    
    print(f"   └─ Extracted Text Snippet: {full_text[:500]!r}")

    # 3. Extract Kazanımlar - either with LLM or Regex
    # Extract grade and subject from filename for LLM mode
    parts = file_metadata.get("subject", "").upper().split("_")
    subject_from_file = parts[0] if parts else "UNKNOWN"
    grade_from_file = file_metadata.get("grade", 0)

    # Map Turkish subject names to codes
    subject_map = {
        "BIYOLOJI": "BİY",
        "BİYOLOJİ": "BİY",
        "MATEMATIK": "M",
        "FIZIK": "FİZ",
        "FİZİK": "FİZ",
        "KIMYA": "KİM",
        "KİMYA": "KİM",
    }
    subject_code = subject_map.get(subject_from_file.upper(), subject_from_file)

    if use_llm:
        # LLM-based extraction (more accurate but slower)
        print("   └─ Extracting kazanımlar with LLM...")
        kazanim_dicts = await extract_kazanimlar_with_llm(
            full_text,
            grade=grade_from_file,
            subject=subject_code,
            semester=semester
        )

        if not kazanim_dicts:
            print("   ⚠️ LLM extraction failed, falling back to regex...")
            use_llm = False  # Fall through to regex

    if not use_llm:
        # Regex-based extraction (faster but less accurate)
        # Format: BİY.9.1.1. Title text
        #         a) sub-item
        #         b) sub-item
        #         BİY.9.1.2. Next kazanim...
        print("   └─ Parsing kazanim codes with regex...")

        # NEW APPROACH: Parse sub-items (a, b, c, ç, d) separately for granular indexing
        # Each sub-item is a distinct, measurable learning outcome

        # Step 1: Find all main kazanım codes and their blocks
        # Pattern captures: CODE + everything until next CODE
        kazanim_block_pattern = r"([A-ZİĞÜŞÖÇ]+\.\d+(?:\.\d+)+)\.?\s+([\s\S]+?)(?=\n[A-ZİĞÜŞÖÇ]+\.\d+(?:\.\d+)+\.|$)"
        blocks = re.findall(kazanim_block_pattern, full_text)

        print(f"   └─ Found {len(blocks)} kazanim blocks")

        if not blocks:
            print("   ⚠️ No kazanim codes found! check regex or pdf format.")
            return

        # Step 2: Parse each block to extract sub-items (a, b, c, ç, d) or combined (a-b)
        # Sub-item pattern: letter or letter-range followed by ) and text
        # Handles: a) text, b) text, a-b) text, ç) text
        sub_item_pattern = r"([a-zçğıöşü](?:-[a-zçğıöşü])?)\)\s*(.+?)(?=\n[a-zçğıöşü](?:-[a-zçğıöşü])?\)|\n\n|\n[A-ZİĞÜŞÖÇ]+\.\d|$)"

        kazanim_dicts = []
        total_sub_items = 0
        seen_codes = set()  # Track codes to prevent duplicates

        for code, block_content in blocks:
            # Extract the title (first line before any sub-items)
            title_match = re.match(r"^([^\n]+?)(?=\n[a-zçğıöşü](?:-[a-zçğıöşü])?\)|$)", block_content.strip())
            title = title_match.group(1).strip() if title_match else block_content.split('\n')[0].strip()

            # Parse code parts
            parts = code.split('.')
            grade = 0
            if len(parts) > 1 and parts[1].isdigit():
                grade = int(parts[1])
            subject = parts[0]  # 'BİY', 'M', etc.

            # Find all sub-items in this block (DOTALL allows . to match newlines)
            sub_items = re.findall(sub_item_pattern, block_content, re.DOTALL)

            if sub_items:
                # Index each sub-item separately with parent code reference
                for letter, content in sub_items:
                    content = content.strip().replace("\n", " ").replace("  ", " ")
                    if len(content) < 10:  # Skip empty/invalid sub-items
                        continue

                    # CLEAN DESCRIPTION: Extract only the actual kazanım definition
                    # Remove teaching instruction markers and limit to first sentence
                    clean_desc = clean_kazanim_description(content)
                    if len(clean_desc) < 10:
                        continue

                    sub_code = f"{code}.{letter}"  # e.g., BİY.9.1.1.a or BİY.9.1.1.a-b

                    # Skip if we already have this code (keep first occurrence)
                    if sub_code in seen_codes:
                        continue
                    seen_codes.add(sub_code)
                    total_sub_items += 1

                    # Use code-based ID to prevent duplicates
                    # Same code = same document (will be updated instead of duplicated)
                    code_id = sub_code.replace(".", "_").replace("-", "_")
                    for tr_char, en_char in [("İ", "I"), ("ı", "i"), ("Ğ", "G"), ("ğ", "g"), ("Ü", "U"), ("ü", "u"), ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"), ("Ç", "C"), ("ç", "c")]:
                        code_id = code_id.replace(tr_char, en_char)
                    kazanim_dicts.append({
                        "id": code_id,
                        "code": sub_code,
                        "parent_code": code,
                        "description": clean_desc,
                        "title": title,  # Parent kazanım title for context
                        "grade": grade,
                        "subject": subject,
                        "semester": semester
                    })
            else:
                # No sub-items found, index the main kazanım title
                # Skip if we already have this code
                if code in seen_codes:
                    continue
                seen_codes.add(code)

                description = clean_kazanim_description(title) if len(title) < 500 else clean_kazanim_description(title[:500])
                code_id = code.replace(".", "_").replace("-", "_")
                for tr_char, en_char in [("İ", "I"), ("ı", "i"), ("Ğ", "G"), ("ğ", "g"), ("Ü", "U"), ("ü", "u"), ("Ş", "S"), ("ş", "s"), ("Ö", "O"), ("ö", "o"), ("Ç", "C"), ("ç", "c")]:
                    code_id = code_id.replace(tr_char, en_char)
                kazanim_dicts.append({
                    "id": code_id,
                    "code": code,
                    "parent_code": code,
                    "description": description,
                    "title": title,
                    "grade": grade,
                    "subject": subject,
                    "semester": semester
                })

        print(f"   └─ Parsed {total_sub_items} sub-items from {len(blocks)} kazanim blocks")

    print(f"   └─ Total kazanımlar to index: {len(kazanim_dicts)}")

    # Debug: Show sample parsed items
    if kazanim_dicts:
        sample = kazanim_dicts[0]
        print(f"   └─ Sample: {sample['code']} - {sample['description'][:80]}...")

    # 4. INDEX KAZANIMLAR TO PRIMARY INDEX (This is the main curriculum data!)
    print("   └─ Indexing kazanımlar to PRIMARY index (meb-kazanimlar-index)...")
    pipeline.index_kazanimlar_raw(kazanim_dicts)

    # 5. Synthetic Question Generation - DISABLED FOR NOW
    # Uncomment below to enable synthetic question generation after kazanım index is stable
    # This adds significant time and API cost, so we skip it during initial setup
    print("   └─ Skipping synthetic question generation (disabled)")

    # TODO: Re-enable when kazanım index is verified correct
    # generator = SyntheticQuestionGenerator()
    # ... (synthetic question generation code)

    # Mark as processed AFTER successful completion
    save_processed_file(pdf_path, "kazanim")
    print(f"[OK] Completed Kazanim File: {pdf_path.name}")


async def process_single_pdf(
    pdf_path: Path,
    settings,
    doc_client,
    vision_client,
    pipeline,
    use_llm: bool = False
):
    # Check if this is a kazanim file
    if "kazanim" in str(pdf_path).lower() or "kazanım" in str(pdf_path).lower():
        await process_kazanim_pdf(pdf_path, settings, doc_client, pipeline, use_llm=use_llm)
        return

    print(f"\n📘 Processing Textbook: {pdf_path.name}")
    
    # 1. Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    metadata = parse_filename(pdf_path.name)
    print(f"   └─ Metadata: {metadata}")

    # 2. Layout Analysis with automatic PDF splitting for large files
    file_size_mb = len(pdf_bytes) / (1024 * 1024)
    print(f"   └─ Analyzing layout (Azure Document Intelligence)... [{file_size_mb:.1f} MB]")

    analyzer = LayoutAnalyzer()

    # Check if PDF should be split to avoid timeouts
    splitter = PDFSplitter(max_chunk_size_mb=35, pages_per_chunk=25)

    if splitter.should_split(pdf_bytes):
        print(f"   └─ 🔪 Dosya çok büyük ({file_size_mb:.1f}MB) - parçalara ayrılıyor...")

        # Split PDF into manageable chunks
        chunks = splitter.split_pdf(pdf_bytes)
        print(f"   └─ {len(chunks)} parçaya ayrıldı")

        # Process each chunk
        chunk_results = []
        chunk_page_offsets = []

        for i, (chunk_bytes, start_page, end_page) in enumerate(chunks, 1):
            chunk_size_mb = len(chunk_bytes) / (1024 * 1024)
            print(f"   └─ Parça {i}/{len(chunks)} işleniyor: sayfa {start_page}-{end_page} ({chunk_size_mb:.1f}MB)")

            try:
                # Analyze this chunk with generous timeout
                chunk_result = await analyzer.analyze_document(
                    doc_client,
                    chunk_bytes,
                    max_retries=5,
                    initial_delay=90.0
                )
                chunk_results.append(chunk_result)
                chunk_page_offsets.append(start_page)
                print(f"      ✅ Parça {i} tamamlandı")

            except Exception as e:
                print(f"      ❌ Parça {i} başarısız: {e}")
                # If a chunk fails, we can't continue with this PDF
                raise Exception(f"Failed to process chunk {i}/{len(chunks)}: {e}")

        # Merge results from all chunks
        print(f"   └─ Tüm parçalar birleştiriliyor...")
        result = PDFSplitter.merge_analyze_results(chunk_results, chunk_page_offsets)
        print(f"   └─ ✅ Birleştirme tamamlandı")

    else:
        # Process normally for smaller files
        if file_size_mb > 30:
            print(f"   └─ Büyük dosya - uzatılmış timeout kullanılacak")

        result = await analyzer.analyze_document(
            doc_client,
            pdf_bytes,
            max_retries=5,
            initial_delay=90.0
        )

    elements = analyzer.classify_elements(result)
    print(f"   └─ Found {len(elements)} layout elements")
    if result.figures:
        print(f"   └─ Azure found {len(result.figures)} figures in total")
    else:
        print(f"   └─ Azure found 0 figures")

    # 3. Image Extraction
    print("   └─ Extracting images...")
    # Convert textbook_id to string for path composition
    img_output_dir = Path("data/processed/images") / str(metadata["textbook_id"])
    extractor = ImageExtractor(vision_client=vision_client, output_dir=img_output_dir)
    
    # Extract images using Azure coordinates
    # Note: LayoutAnalyzer returns full result which contains figures
    images = extractor.extract_images_from_bytes(pdf_bytes, result.figures or [])
    print(f"   └─ Extracted {len(images)} valid images")
    
    # Generate captions for images (Async)
    if images and vision_client:
        print("   └─ Generating image captions (GPT-4o Vision)...")
        images = await extractor.generate_captions(images)
        
        # Log summary of types
        type_counts = {}
        for img in images:
            t = img.image_type or "unknown"
            type_counts[t] = type_counts.get(t, 0) + 1
        print(f"   └─ Image Analysis Summary: {len(images)} images -> {type_counts}")

    # 4. Semantic Chunking
    print("   └─ Creating semantic chunks...")
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(elements)
    chunks = chunker.merge_small_chunks(chunks)
    print(f"   └─ Created {len(chunks)} chunks")

    # 5. Indexing
    print("   └─ Indexing to Azure AI Search...")

    # Helper: Extract chapter number from hierarchy_path
    def extract_chapter_id(hierarchy_path: str) -> int:
        """Extract chapter/unit number from hierarchy path like 'Ünite 1/Konu 2'"""
        if not hierarchy_path:
            return 0
        import re
        # Match patterns like "Ünite 1", "Bölüm 2", "Unit 3", "1. Ünite"
        patterns = [
            r'[Üü]nite\s*(\d+)',
            r'[Bb]ölüm\s*(\d+)',
            r'[Uu]nit\s*(\d+)',
            r'^(\d+)\.\s*[Üü]nite',
        ]
        for pattern in patterns:
            match = re.search(pattern, hierarchy_path, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0

    # Build page-to-chunk mapping for linking images to chunks
    page_to_chunks = {}
    for chunk in chunks:
        start_page, end_page = chunk.page_range
        for page in range(start_page, end_page + 1):
            if page not in page_to_chunks:
                page_to_chunks[page] = []
            page_to_chunks[page].append(chunk)

    # Prepare chunk dicts with page offset for split PDFs
    chunk_dicts = []
    page_offset = metadata.get("page_offset", 0)

    for chunk in chunks:
        # Apply page offset to get correct page numbers
        adjusted_start = chunk.page_range[0] + page_offset
        adjusted_end = chunk.page_range[1] + page_offset

        c_dict = {
            "id": chunk.chunk_id,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type,
            "hierarchy_path": chunk.hierarchy_path,
            "page_range": f"{adjusted_start}-{adjusted_end}",  # Adjusted page numbers
            "is_sidebar": chunk.is_sidebar_content,
            "textbook_id": metadata["textbook_id"],
            "textbook_name": metadata["textbook_name"],
            "chapter_id": extract_chapter_id(chunk.hierarchy_path),
            "grade": metadata["grade"],
            "subject": metadata["subject"],
            "semester": metadata["semester"],
        }
        chunk_dicts.append(c_dict)

    # Prepare image dicts with chunk linkage
    image_dicts = []
    for img in images:
        # Find the best matching chunk for this image based on page number
        matching_chunks = page_to_chunks.get(img.page_number, [])

        # Get the first non-sidebar chunk, or any chunk if none available
        best_chunk = None
        for c in matching_chunks:
            if not c.is_sidebar_content:
                best_chunk = c
                break
        if not best_chunk and matching_chunks:
            best_chunk = matching_chunks[0]

        # Extract related text (first 300 chars of matching chunk)
        related_text = ""
        chunk_id = ""
        hierarchy_path = img.hierarchy_path or ""

        if best_chunk:
            chunk_id = best_chunk.chunk_id
            hierarchy_path = best_chunk.hierarchy_path or hierarchy_path
            # Get a preview of the related text (clean it up)
            content_preview = best_chunk.content[:300].replace('\n', ' ').strip()
            if len(best_chunk.content) > 300:
                content_preview += "..."
            related_text = content_preview

        i_dict = {
            "id": img.image_id,
            "caption": img.caption or "Görsel",
            "image_type": img.image_type or "unknown",
            "page_number": img.page_number + page_offset,  # Adjusted page number
            "chunk_id": chunk_id,  # NEW: Link to chunk
            "related_text": related_text,  # NEW: Context from chunk
            "hierarchy_path": hierarchy_path,  # NEW: Inherit from chunk if not set
            "image_path": str(img.image_path) if img.image_path else "",
            "width": img.width if hasattr(img, 'width') else 0,
            "height": img.height if hasattr(img, 'height') else 0,
            "textbook_id": metadata["textbook_id"],
            "grade": metadata["grade"],
            "subject": metadata["subject"]
        }
        image_dicts.append(i_dict)

    print(f"   └─ Linked {sum(1 for i in image_dicts if i['chunk_id'])} images to chunks")

    # Convert sync methods to async run where necessary or run directly if pipeline supports it
    # ensure pipeline uses correct index names
    
    # Index Chunks
    if chunk_dicts:
        pipeline.index_textbook_chunks(chunk_dicts)
    
    # Index Images
    if image_dicts:
        pipeline.index_images(image_dicts)

    # Mark as processed AFTER successful completion
    save_processed_file(pdf_path, "kitap")
    print(f"[OK] Completed Textbook: {pdf_path.name}")


async def main(process_mode: str = "all", reset: str = None, parallel_count: int = 1, use_llm: bool = False):
    """
    Main processing function.

    Args:
        process_mode: "all", "kazanim", or "kitap" - determines which PDFs to process
        reset: Index deletion mode - "all", "kazanim", "kitap", or None (no deletion)
        parallel_count: Number of PDFs to process in parallel (default: 1)
        use_llm: If True, use LLM for intelligent kazanım extraction (slower but more accurate)
    """
    print("="*60)
    print("MEB RAG - PDF Ingestion Pipeline")
    print(f"Mode: {process_mode.upper()}")
    if use_llm:
        print("🤖 LLM Extraction: ENABLED (GPT-4o will extract kazanımlar)")
    print("="*60)
    
    settings = get_settings()
    
    # ... (Directories check omitted for brevity in replace, assume handled or no change needed to top part)
    # Actually I need to keep the function body intact or be careful with replace range.
    # I will target specific blocks.

    # Validate Directories
    pdf_dir = Path("data/pdfs")
    if not pdf_dir.exists():
        print(f"[ERROR] Directory not found: {pdf_dir}")
        return

    # Check Azure Keys
    if not settings.documentintelligence_api_key or not settings.azure_search_api_key:
        print("[ERROR] Missing Azure API Keys in .env")
        return

    # Initialize Clients
    print("[INFO] Initializing Azure Clients...")

    # Document Intelligence Client with extended timeouts for large PDFs
    # Use retry_total and per_retry_timeout for robust handling of large files
    from azure.core.pipeline.policies import RetryPolicy

    doc_client = DocumentIntelligenceClient(
        endpoint=settings.documentintelligence_endpoint,
        credential=AzureKeyCredential(settings.documentintelligence_api_key),
        retry_total=5,  # Total retry attempts
        retry_backoff_factor=2,  # Exponential backoff
        retry_backoff_max=120,  # Max 2 minutes between retries
    )
    
    # Azure OpenAI Client (for Vision)
    from openai import AsyncAzureOpenAI
    vision_client = AsyncAzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint
    )

    # Indexing Pipeline
    pipeline = IndexingPipeline()
    
    # RESET IF REQUESTED
    if reset:
        # Pass the reset mode (can be different from process_mode)
        pipeline.delete_indexes(reset)
        # Also clear the processed files state
        clear_processed_state(reset)

    # Ensure indexes exist
    pipeline.create_all_indexes()
    
    # Find PDFs based on mode
    if process_mode == "kazanim":
        pdf_files = list(Path("data/pdfs/kazanimlar").rglob("*.pdf"))
        print(f"📑 Sadece kazanımlar işlenecek: {len(pdf_files)} dosya")
    elif process_mode == "kitap":
        pdf_files = list(Path("data/pdfs/ders_kitaplari").rglob("*.pdf"))
        print(f"📘 Sadece ders kitapları işlenecek: {len(pdf_files)} dosya")
    else:
        pdf_files = list(pdf_dir.rglob("*.pdf"))
        print(f"📚 Tüm PDF'ler işlenecek: {len(pdf_files)} dosya")
    
    if not pdf_files:
        print("⚠️  No PDF files found!")
        return

    # Check for already processed files
    skipped_count = 0
    to_process = []

    for pdf_file in pdf_files:
        # Determine file type based on path or content
        is_kazanim = "kazanim" in str(pdf_file).lower() or "kazanım" in str(pdf_file).lower()
        file_type = "kazanim" if is_kazanim else "kitap"

        if is_already_processed(pdf_file, file_type):
            skipped_count += 1
            print(f"⏭️  Skipping (already processed): {pdf_file.name}")
        else:
            to_process.append(pdf_file)

    if skipped_count > 0:
        print(f"\n📊 {skipped_count} dosya zaten işlenmiş, {len(to_process)} dosya işlenecek\n")

    if not to_process:
        print("✅ Tüm dosyalar zaten işlenmiş!")
        return

    # Process PDFs (parallel or sequential based on parallel_count)

    if parallel_count > 1:
        print(f"\n🚀 Paralel işlem modu: {parallel_count} PDF aynı anda işlenecek")

        # Semaphore for limiting concurrent processing
        semaphore = asyncio.Semaphore(parallel_count)

        # Track progress
        completed = {"count": 0, "success": 0, "failed": 0}
        total = len(to_process)

        async def process_with_limit(pdf_file, index):
            async with semaphore:
                try:
                    # Calculate timeout based on file size
                    # With PDF splitting, large files take longer but are more reliable
                    file_size_mb = pdf_file.stat().st_size / (1024 * 1024)
                    if file_size_mb > 100:
                        timeout = 7200  # 2 saat for >100MB files (might be split into multiple chunks)
                        timeout_str = "2 saat"
                    elif file_size_mb > 50:
                        timeout = 5400  # 90 dakika for >50MB files
                        timeout_str = "90 dakika"
                    elif file_size_mb > 30:
                        timeout = 3600  # 60 dakika for >30MB files
                        timeout_str = "60 dakika"
                    else:
                        timeout = 2400  # 40 dakika for smaller files
                        timeout_str = "40 dakika"

                    print(f"\n[{index}/{total}] 🔄 Starting: {pdf_file.name} ({file_size_mb:.1f}MB, timeout: {timeout_str})")
                    await asyncio.wait_for(
                        process_single_pdf(
                            pdf_file,
                            settings,
                            doc_client,
                            vision_client,
                            pipeline,
                            use_llm=use_llm
                        ),
                        timeout=timeout
                    )
                    completed["success"] += 1
                    print(f"[{index}/{total}] ✅ Completed: {pdf_file.name}")
                except asyncio.TimeoutError:
                    completed["failed"] += 1
                    print(f"[{index}/{total}] ⏰ TIMEOUT: {pdf_file.name} (timeout aşıldı)")
                except Exception as e:
                    completed["failed"] += 1
                    print(f"[{index}/{total}] ❌ ERROR: {pdf_file.name}: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    completed["count"] += 1
                    remaining = total - completed["count"]
                    print(f"📊 İlerleme: {completed['count']}/{total} tamamlandı, {remaining} kaldı")

        # Create tasks for all PDFs
        tasks = [
            process_with_limit(pdf_file, i)
            for i, pdf_file in enumerate(to_process, 1)
        ]

        # Run all tasks concurrently (semaphore limits actual parallelism)
        await asyncio.gather(*tasks, return_exceptions=True)

        print(f"\n{'='*60}")
        print(f"📊 SONUÇ: {completed['success']} başarılı, {completed['failed']} başarısız")
        print(f"{'='*60}")
    else:
        # Sequential processing (original behavior)
        for i, pdf_file in enumerate(to_process, 1):
            print(f"\n[{i}/{len(to_process)}] Processing...")
            try:
                await process_single_pdf(
                    pdf_file,
                    settings,
                    doc_client,
                    vision_client,
                    pipeline,
                    use_llm=use_llm
                )
            except Exception as e:
                print(f"[ERROR] Error processing {pdf_file.name}: {e}")
                import traceback
                traceback.print_exc()
                # Don't mark as processed if there was an error!

    print("\n[DONE] All processing completed!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MEB RAG - PDF Processing and Indexing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/process_pdfs.py                        # Tüm PDF'leri işle
  python scripts/process_pdfs.py --reset                # Önce tüm indexleri sil sonra işle
  python scripts/process_pdfs.py -k -r                  # Sadece kazanımları işle ve önce sil
  python scripts/process_pdfs.py -k -r --llm            # Kazanımları LLM ile akıllı çıkar (önerilen)
  python scripts/process_pdfs.py -t --reset-kitap       # Kitapları işle, sadece kitap indexini sil
  python scripts/process_pdfs.py -t --reset-kitap -p 3  # 3 kitabı paralel işle (önerilen)
  python scripts/process_pdfs.py --reset-kitap          # Sadece kitap indexini sil (işlem yapmadan)
  python scripts/process_pdfs.py --reset-kazanim        # Sadece kazanım indexini sil (işlem yapmadan)
        """
    )

    # Processing mode (what to process)
    process_group = parser.add_mutually_exclusive_group()
    process_group.add_argument(
        "--kazanim", "-k",
        action="store_true",
        help="Sadece kazanım PDF'lerini işle (data/pdfs/kazanimlar/)"
    )
    process_group.add_argument(
        "--kitap", "-t",
        action="store_true",
        help="Sadece ders kitaplarını işle (data/pdfs/ders_kitaplari/)"
    )

    # Reset options (what to delete)
    reset_group = parser.add_mutually_exclusive_group()
    reset_group.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Tüm indexleri SİL ve baştan oluştur."
    )
    reset_group.add_argument(
        "--reset-kitap",
        action="store_true",
        help="Sadece kitap (chunks + images) indexlerini SİL."
    )
    reset_group.add_argument(
        "--reset-kazanim",
        action="store_true",
        help="Sadece kazanım/soru indexini SİL."
    )

    parser.add_argument(
        "--delete-only",
        action="store_true",
        help="Sadece index sil, PDF işleme yapma (--reset-* ile birlikte kullan)."
    )

    parser.add_argument(
        "--parallel", "-p",
        type=int,
        default=1,
        metavar="N",
        help="N adet PDF'i paralel işle (varsayılan: 1, önerilen: 2-3)"
    )

    parser.add_argument(
        "--llm",
        action="store_true",
        help="Kazanımları LLM ile akıllı çıkar (daha yavaş ama daha doğru). Regex yerine GPT-4o kullanır."
    )

    args = parser.parse_args()

    # Determine processing mode
    if args.kazanim:
        mode = "kazanim"
    elif args.kitap:
        mode = "kitap"
    else:
        mode = "all"

    # Determine reset mode
    if args.reset:
        reset_mode = mode  # Reset matches processing mode
    elif args.reset_kitap:
        reset_mode = "kitap"
    elif args.reset_kazanim:
        reset_mode = "kazanim"
    else:
        reset_mode = None

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Handle delete-only mode
    if args.delete_only:
        if not reset_mode:
            print("[ERROR] --delete-only requires a reset flag (--reset, --reset-kitap, or --reset-kazanim)")
            sys.exit(1)
        # Just delete indexes without processing
        from src.vector_store.indexing_pipeline import IndexingPipeline
        pipeline = IndexingPipeline()
        pipeline.delete_indexes(reset_mode)
        print("[DONE] Index deletion completed.")
    else:
        asyncio.run(main(mode, reset=reset_mode, parallel_count=args.parallel, use_llm=args.llm))

