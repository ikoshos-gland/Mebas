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
from pathlib import Path
from dataclasses import asdict

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
    
    # Pattern: Capture code and everything until next code or end
    # Lookahead ensures we stop before the next kazanim code
    kazanim_pattern = r"([A-ZİĞÜŞÖÇ]+\.\d+(?:\.\d+)+)\.?\s+([\s\S]+?)(?=\n[A-ZİĞÜŞÖÇ]+\.\d+(?:\.\d+)+\.|$)"
    matches = re.findall(kazanim_pattern, full_text)
    
    print(f"   └─ Found {len(matches)} potential kazanim entries")
    
    if not matches:
        print("   ⚠️ No kazanim codes found! check regex or pdf format.")
        return

    # 4. Generate Questions for each Kazanim (PARALLEL)
    print(f"   └─ Generating synthetic questions (GPT-4o) - {len(matches)} kazanim in parallel...")
    generator = SyntheticQuestionGenerator()
    
    # Build kazanim dicts first
    kazanim_dicts = []
    for code, description in matches:
        description = description.strip().replace("\n", " ")
        parts = code.split('.')
        grade = 0
        if len(parts) > 1 and parts[1].isdigit():
            grade = int(parts[1])
            
        kazanim_dicts.append({
            "id": str(uuid.uuid4()),
            "code": code,
            "description": description,
            "grade": grade,
            "subject": parts[0],  # 'BİY', 'M', etc.
            "semester": semester
        })
    
    # Parallel generation with semaphore to respect rate limits
    PARALLEL_LIMIT = 5  # Process 5 at a time to avoid rate limits
    semaphore = asyncio.Semaphore(PARALLEL_LIMIT)
    
    async def generate_with_limit(kazanim):
        async with semaphore:
            print(f"      └─ Generating for {kazanim['code']}...")
            return await generator.generate_for_kazanim_async(kazanim, count=5)
    
    # Run all in parallel
    tasks = [generate_with_limit(k) for k in kazanim_dicts]
    results = await asyncio.gather(*tasks)
    
    # Flatten results
    all_questions = []
    for qs in results:
        all_questions.extend(qs)

    print(f"   └─ Generated {len(all_questions)} total questions")

    # 5. Index Questions
    if all_questions:
        print("   └─ Indexing questions to Azure AI Search...")
        
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
            
        pipeline.index_kazanimlar(q_dicts, generate_questions=False) # Skip internal generation, we already did it

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

    # 2. Layout Analysis
    print("   └─ Analyzing layout (Azure Document Intelligence)...")
    analyzer = LayoutAnalyzer()
    result = await analyzer.analyze_document(doc_client, pdf_bytes)
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
            "grade": metadata["grade"],
            "subject": metadata["subject"],
            # Flatten metadata if needed or keep as extra field
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


async def main(process_mode: str = "all"):
    """
    Main processing function.
    
    Args:
        process_mode: "all", "kazanim", or "kitap"
    """
    print("="*60)
    print("MEB RAG - PDF Ingestion Pipeline")
    print(f"Mode: {process_mode.upper()}")
    print("="*60)
    
    settings = get_settings()
    
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
    
    # Document Intelligence Client
    doc_client = DocumentIntelligenceClient(
        endpoint=settings.documentintelligence_endpoint,
        credential=AzureKeyCredential(settings.documentintelligence_api_key),
        # Increase timeout for large PDF uploads (180MB+)
        connection_timeout=300,  # 5 minutes connect
        read_timeout=300         # 5 minutes read
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
  python scripts/process_pdfs.py              # Tüm PDF'leri işle
  python scripts/process_pdfs.py --kazanim    # Sadece kazanımları işle
  python scripts/process_pdfs.py --kitap      # Sadece ders kitaplarını işle
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--kazanim", "-k",
        action="store_true",
        help="Sadece kazanım PDF'lerini işle (data/pdfs/kazanimlar/)"
    )
    group.add_argument(
        "--kitap", "-t",
        action="store_true", 
        help="Sadece ders kitaplarını işle (data/pdfs/ders_kitaplari/)"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.kazanim:
        mode = "kazanim"
    elif args.kitap:
        mode = "kitap"
    else:
        mode = "all"
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main(mode))

