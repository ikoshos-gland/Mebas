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
from src.vector_store.indexing_pipeline import IndexingPipeline


import re
import uuid
from src.vector_store.question_generator import SyntheticQuestionGenerator

def parse_filename(filename: str) -> dict:
    """
    Parse filename to extract metadata.
    Expected formats:
    - subject_grade.pdf (e.g., biyoloji_9.pdf)
    - subject_grade.semester.pdf (e.g., biyoloji_9.1.pdf, biyoloji_10.2.pdf)
    """
    stem = Path(filename).stem  # e.g., "biyoloji_9.1" or "biyoloji_9"
    
    # Generate numeric textbook_id from hash (schema requires Int32)
    textbook_id_hash = abs(hash(stem)) % (10**8)  # 8-digit positive integer
    
    metadata = {
        "subject": "genel",
        "grade": 0,
        "semester": 0,  # 0 = unknown, 1 = 1. dönem, 2 = 2. dönem
        "textbook_id": textbook_id_hash,
        "textbook_name": stem  # Keep original name for reference
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


async def process_kazanim_pdf(
    pdf_path: Path,
    settings,
    doc_client,
    pipeline
):
    print(f"\n📑 Processing Kazanim File: {pdf_path.name}")
    
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
    
    # 3. Parse Kazanim Codes with Regex
    # Format: BİY.9.1.1. Title text
    #         a) sub-item
    #         b) sub-item
    #         BİY.9.1.2. Next kazanim...
    print("   └─ Parsing kazanim codes...")

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

    # Step 2: Parse each block to extract sub-items (a, b, c, ç, d)
    # Sub-item pattern: letter followed by ) and text until next sub-item or double newline or new kazanim
    sub_item_pattern = r"([a-zçğıöşü])\)\s*(.+?)(?=\n[a-zçğıöşü]\)|\n\n|\n[A-ZİĞÜŞÖÇ]+\.\d|$)"

    kazanim_dicts = []
    total_sub_items = 0

    for code, block_content in blocks:
        # Extract the title (first line before any sub-items)
        title_match = re.match(r"^([^\n]+?)(?=\n[a-zçğıöşü]\)|$)", block_content.strip())
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

                sub_code = f"{code}.{letter}"  # e.g., BİY.9.1.1.a
                total_sub_items += 1

                kazanim_dicts.append({
                    "id": str(uuid.uuid4()),
                    "code": sub_code,
                    "parent_code": code,
                    "description": content,
                    "title": title,  # Parent kazanım title for context
                    "grade": grade,
                    "subject": subject,
                    "semester": semester
                })
        else:
            # No sub-items found, index the main kazanım title
            description = title if len(title) < 500 else title[:500]
            kazanim_dicts.append({
                "id": str(uuid.uuid4()),
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

    # 5. Generate Synthetic Questions for each Kazanim (PARALLEL)
    # These are used for example question generation, NOT for curriculum retrieval
    print(f"   └─ Generating synthetic questions (GPT-4o) - {len(kazanim_dicts)} kazanımlar...")
    generator = SyntheticQuestionGenerator()

    # Parallel generation with semaphore to respect rate limits
    PARALLEL_LIMIT = 5  # Process 5 at a time to avoid rate limits
    semaphore = asyncio.Semaphore(PARALLEL_LIMIT)

    async def generate_with_limit(kazanim):
        async with semaphore:
            print(f"      └─ Generating questions for {kazanim['code']}...")
            return await generator.generate_for_kazanim_async(kazanim, count=5)

    # Run all in parallel
    tasks = [generate_with_limit(k) for k in kazanim_dicts]
    results = await asyncio.gather(*tasks)

    # Flatten results
    all_questions = []
    for qs in results:
        all_questions.extend(qs)

    print(f"   └─ Generated {len(all_questions)} total synthetic questions")

    # 6. Index Synthetic Questions (secondary index for example questions)
    if all_questions:
        print("   └─ Indexing synthetic questions to meb-sentetik-sorular-index...")

        # Build lookup for kazanim metadata
        kazanim_lookup = {k["code"]: k for k in kazanim_dicts}

        # Convert dataclass to dict for indexing
        q_dicts = []
        for q in all_questions:
            # Get the kazanim metadata for this question
            kaz = kazanim_lookup.get(q.parent_kazanim_code, {})
            q_dicts.append({
                "id": str(uuid.uuid4()),
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "code": q.parent_kazanim_code,  # pipeline expects 'code'
                "description": kaz.get("description", ""),  # pipeline expects 'description'
                "grade": kaz.get("grade", 0),
                "subject": kaz.get("subject", ""),
                "semester": kaz.get("semester", 0)
            })

        pipeline.index_kazanimlar(q_dicts, generate_questions=False)  # Skip internal generation

    print(f"[OK] Completed Kazanim File: {pdf_path.name}")


async def process_single_pdf(
    pdf_path: Path, 
    settings, 
    doc_client, 
    vision_client,
    pipeline
):
    # Check if this is a kazanim file
    if "kazanim" in str(pdf_path).lower() or "kazanım" in str(pdf_path).lower():
        await process_kazanim_pdf(pdf_path, settings, doc_client, pipeline)
        return

    print(f"\n📘 Processing Textbook: {pdf_path.name}")
    
    # 1. Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    metadata = parse_filename(pdf_path.name)
    print(f"   └─ Metadata: {metadata}")

    # 2. Layout Analysis with retry support for large PDFs
    file_size_mb = len(pdf_bytes) / (1024 * 1024)
    print(f"   └─ Analyzing layout (Azure Document Intelligence)... [{file_size_mb:.1f} MB]")
    if file_size_mb > 50:
        print(f"   └─ Large file detected - may take several minutes with auto-retry on timeout")

    analyzer = LayoutAnalyzer()
    result = await analyzer.analyze_document(doc_client, pdf_bytes, max_retries=3, initial_delay=30.0)
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
    
    # Prepare chunk dicts
    chunk_dicts = []
    for chunk in chunks:
        c_dict = {
            "id": chunk.chunk_id,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type,
            "hierarchy_path": chunk.hierarchy_path,
            "page_range": f"{chunk.page_range[0]}-{chunk.page_range[1]}",
            "is_sidebar": chunk.is_sidebar_content,
            "textbook_id": metadata["textbook_id"],
            "textbook_name": metadata["textbook_name"],  # Kitap adı (örn: biyoloji_9)
            "grade": metadata["grade"],
            "subject": metadata["subject"],
            "semester": metadata["semester"],  # CRITICAL: Include semester for curriculum alignment
        }
        chunk_dicts.append(c_dict)

    # Prepare image dicts
    image_dicts = []
    for img in images:
        i_dict = {
            "id": img.image_id,
            "caption": img.caption or "Görsel",
            "image_type": img.image_type or "unknown",
            "page_number": img.page_number,
            "hierarchy_path": img.hierarchy_path, # Image extractor might not set this yet
            "image_path": str(img.image_path) if img.image_path else "",
            "textbook_id": metadata["textbook_id"],
             # Additional fields for image index if schema requires
            "grade": metadata["grade"],
            "subject": metadata["subject"]
        }
        image_dicts.append(i_dict)

    # Convert sync methods to async run where necessary or run directly if pipeline supports it
    # ensure pipeline uses correct index names
    
    # Index Chunks
    if chunk_dicts:
        pipeline.index_textbook_chunks(chunk_dicts)
    
    # Index Images
    if image_dicts:
        pipeline.index_images(image_dicts)
        
    print(f"[OK] Completed Textbook: {pdf_path.name}")


async def main(process_mode: str = "all", reset: str = None):
    """
    Main processing function.

    Args:
        process_mode: "all", "kazanim", or "kitap" - determines which PDFs to process
        reset: Index deletion mode - "all", "kazanim", "kitap", or None (no deletion)
    """
    print("="*60)
    print("MEB RAG - PDF Ingestion Pipeline")
    print(f"Mode: {process_mode.upper()}")
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
    
    # Process each PDF
    for pdf_file in pdf_files:
        try:
            await process_single_pdf(
                pdf_file, 
                settings, 
                doc_client, 
                vision_client,
                pipeline
            )
        except Exception as e:
            print(f"[ERROR] Error processing {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n[DONE] All processing completed!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MEB RAG - PDF Processing and Indexing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python scripts/process_pdfs.py                    # Tüm PDF'leri işle
  python scripts/process_pdfs.py --reset            # Önce tüm indexleri sil sonra işle
  python scripts/process_pdfs.py -k -r              # Sadece kazanımları işle ve önce sil
  python scripts/process_pdfs.py -t --reset-kitap   # Kitapları işle, sadece kitap indexini sil
  python scripts/process_pdfs.py --reset-kitap      # Sadece kitap indexini sil (işlem yapmadan)
  python scripts/process_pdfs.py --reset-kazanim    # Sadece kazanım indexini sil (işlem yapmadan)
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
        asyncio.run(main(mode, reset=reset_mode))

