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
    Expected format: subject_grade.pdf (e.g., mat_9.pdf, fiz_10.pdf)
    """
    stem = Path(filename).stem
    parts = stem.split('_')
    
    metadata = {
        "subject": "genel",
        "grade": 0,
        "textbook_id": stem
    }
    
    if len(parts) >= 2:
        metadata["subject"] = parts[0]
        try:
            metadata["grade"] = int(parts[1])
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
    # Pattern looks for M.9.1.2.3 or F.11.2.1.1 (old) and BİY.11.2.1 (new/maarif) styles
    # [Letter].[Grade].[Unit].[Topic].[Objective] (optional)
    # Updated to be space-tolerant and aggressive on lookahead to prevent swallowing next items
    print("   └─ Parsing kazanim codes...")
    kazanim_pattern = r"([A-Zİ]+\s*\.\s*\d+(?:\.\d+){2,})\.?\s+(.+?)(?=\s+[A-Zİ]+\s*\.\s*\d+(?:\.\d+){2,}|$)"
    matches = re.findall(kazanim_pattern, full_text, re.DOTALL)
    
    print(f"   └─ Found {len(matches)} potential kazanim entries")
    
    if not matches:
        print("   ⚠️ No kazanim codes found! check regex or pdf format.")
        return

    # 4. Generate Questions for each Kazanim
    print("   └─ Generating synthetic questions (GPT-4o)...")
    generator = SyntheticQuestionGenerator()
    
    all_questions = []
    
    # Process a subset for testing or all? Let's process all.
    for code, description in matches:
        description = description.strip().replace("\n", " ")
        print(f"      └─ Generating for {code}...")
        
        # Build minimal kazanim dict
        # Try to extract grade/subject from code or filename
        # Code format: M.9.1.2.3 -> M=Mat, 9=Grade
        parts = code.split('.')
        grade = 0
        if len(parts) > 1 and parts[1].isdigit():
            grade = int(parts[1])
            
        kazanim_dict = {
            "id": str(uuid.uuid4()),
            "code": code,
            "description": description,
            "grade": grade,
            "subject": parts[0] # 'M', 'F', etc.
        }
        
        # Determine number of questions (maybe less for fast processing?)
        # Default is 20, let's use 5 for this run to be faster
        qs = await generator.generate_for_kazanim_async(kazanim_dict, count=5)
        all_questions.extend(qs)

    print(f"   └─ Generated {len(all_questions)} total questions")

    # 5. Index Questions
    if all_questions:
        print("   └─ Indexing questions to Azure AI Search...")
        # Convert dataclass to dict for indexing
        q_dicts = []
        for q in all_questions:
            q_dicts.append({
                "id": str(uuid.uuid4()),
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "kazanim_code": q.parent_kazanim_code,
                "kazanim_description": description, # approximation
                "grade": grade,
                "subject": parts[0]
            })
            
        pipeline.index_kazanimlar(q_dicts, generate_questions=False) # Skip internal generation, we already did it

    print(f"✅ Completed Kazanim File: {pdf_path.name}")


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

    # 3. Image Extraction
    print("   └─ Extracting images...")
    img_output_dir = Path("data/processed/images") / metadata["textbook_id"]
    extractor = ImageExtractor(vision_client=vision_client, output_dir=img_output_dir)
    
    # Extract images using Azure coordinates
    # Note: LayoutAnalyzer returns full result which contains figures
    images = extractor.extract_images_from_bytes(pdf_bytes, result.figures or [])
    print(f"   └─ Extracted {len(images)} valid images")
    
    # Generate captions for images (Async)
    if images and vision_client:
        print("   └─ Generating image captions (GPT-4o Vision)...")
        images = await extractor.generate_captions(images)

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
        
    print(f"✅ Completed Textbook: {pdf_path.name}")


async def main():
    print("="*60)
    print("MEB RAG - PDF Ingestion Pipeline")
    print("="*60)
    
    settings = get_settings()
    
    # Validate Directories
    pdf_dir = Path("data/pdfs")
    if not pdf_dir.exists():
        print(f"❌ Directory not found: {pdf_dir}")
        return

    # Check Azure Keys
    if not settings.documentintelligence_api_key or not settings.azure_search_api_key:
        print("❌ Missing Azure API Keys in .env")
        return

    # Initialize Clients
    print("🔌 Initializing Azure Clients...")
    
    # Document Intelligence Client
    doc_client = DocumentIntelligenceClient(
        endpoint=settings.documentintelligence_endpoint,
        credential=AzureKeyCredential(settings.documentintelligence_api_key)
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
    
    # Find PDFs
    pdf_files = list(pdf_dir.rglob("*.pdf"))
    if not pdf_files:
        print("⚠️  No PDF files found in data/pdfs and its subdirectories")
        return
        
    print(f"Found {len(pdf_files)} PDF files.")
    
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
            print(f"❌ Error processing {pdf_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n🎉 All processing completed!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
