#!/usr/bin/env python3
"""
DEBUG Indexing Script - Test PDF processing before production indexing

This script:
1. Creates TEST indexes in Azure (meb-test-kitaplar, meb-test-images)
2. Processes a sample PDF with detailed logging
3. Shows extracted chunks and images
4. Indexes to test indexes
5. Runs sample searches to verify quality

Usage:
    python scripts/debug_indexing.py
"""
import sys
import os
import asyncio
import json
import hashlib
from pathlib import Path
from dataclasses import asdict
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery

from config.settings import get_settings
from src.document_processing.layout_analyzer import LayoutAnalyzer
from src.document_processing.image_extractor import ImageExtractor
from src.document_processing.semantic_chunker import SemanticChunker
from src.vector_store.embeddings import embed_batch
from src.vector_store.index_schema import create_textbook_chunk_index_schema, create_image_index_schema

# Test index names
TEST_KITAP_INDEX = "meb-test-kitaplar"
TEST_IMAGE_INDEX = "meb-test-images"


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def parse_filename(filename: str) -> dict:
    """Parse filename to extract metadata (deterministic hash version)"""
    stem = Path(filename).stem

    # Deterministic hash using MD5
    md5_hash = hashlib.md5(stem.encode('utf-8')).hexdigest()
    textbook_id_hash = int(md5_hash[:8], 16) % (10**8)

    metadata = {
        "subject": "genel",
        "grade": 0,
        "semester": 0,
        "textbook_id": textbook_id_hash,
        "textbook_name": stem
    }

    parts = stem.split('_')
    if len(parts) >= 2:
        metadata["subject"] = parts[0]
        grade_part = parts[1].split('-')[0]  # Handle "11-150-170" format

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


def extract_chapter_id(hierarchy_path: str) -> int:
    """Extract chapter/unit number from hierarchy path"""
    if not hierarchy_path:
        return 0
    import re
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


async def create_test_indexes(settings):
    """Create test indexes in Azure"""
    print_section("Creating Test Indexes")

    index_client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )

    # Delete existing test indexes
    for index_name in [TEST_KITAP_INDEX, TEST_IMAGE_INDEX]:
        try:
            index_client.delete_index(index_name)
            print(f"  ✓ Deleted existing index: {index_name}")
        except Exception:
            pass

    # Create kitap index
    kitap_schema = create_textbook_chunk_index_schema(TEST_KITAP_INDEX)
    index_client.create_index(kitap_schema)
    print(f"  ✓ Created index: {TEST_KITAP_INDEX}")

    # Create image index
    image_schema = create_image_index_schema(TEST_IMAGE_INDEX)
    index_client.create_index(image_schema)
    print(f"  ✓ Created index: {TEST_IMAGE_INDEX}")

    return index_client


async def process_pdf(pdf_path: Path, settings):
    """Process PDF and return chunks and images"""
    print_section(f"Processing: {pdf_path.name}")

    # Read PDF
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    file_size_mb = len(pdf_bytes) / (1024 * 1024)
    print(f"  File size: {file_size_mb:.2f} MB")

    # Parse metadata
    metadata = parse_filename(pdf_path.name)
    print(f"  Metadata: {json.dumps(metadata, indent=4)}")

    # Initialize Document Intelligence client
    doc_client = DocumentIntelligenceClient(
        endpoint=settings.documentintelligence_endpoint,
        credential=AzureKeyCredential(settings.documentintelligence_api_key)
    )

    # Layout Analysis
    print_section("Layout Analysis (Azure Document Intelligence)")
    analyzer = LayoutAnalyzer()
    result = await analyzer.analyze_document(doc_client, pdf_bytes, max_retries=3)
    elements = analyzer.classify_elements(result)

    print(f"  Total elements: {len(elements)}")

    # Count by type
    type_counts = {}
    for el in elements:
        t = el.element_type.value if hasattr(el.element_type, 'value') else str(el.element_type)
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  Element types: {json.dumps(type_counts, indent=4)}")

    # Image Extraction
    print_section("Image Extraction")
    img_output_dir = Path("data/processed/test_images") / str(metadata["textbook_id"])
    img_output_dir.mkdir(parents=True, exist_ok=True)

    # Vision client for captions (async version required)
    from openai import AsyncAzureOpenAI
    vision_client = AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )

    extractor = ImageExtractor(vision_client=vision_client, output_dir=img_output_dir)
    images = extractor.extract_images_from_bytes(pdf_bytes, result.figures or [])
    print(f"  Extracted images: {len(images)}")

    # Generate captions
    if images:
        print("  Generating captions (GPT-4o Vision)...")
        images = await extractor.generate_captions(images)

        print("\n  Image Details:")
        for i, img in enumerate(images[:5]):  # Show first 5
            print(f"    [{i+1}] Page {img.page_number}: {img.image_type or 'unknown'}")
            print(f"        Size: {img.width}x{img.height}")
            print(f"        Caption: {(img.caption or 'N/A')[:80]}...")
        if len(images) > 5:
            print(f"    ... and {len(images) - 5} more images")

    # Semantic Chunking
    print_section("Semantic Chunking")
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(elements)
    chunks = chunker.merge_small_chunks(chunks)
    print(f"  Total chunks: {len(chunks)}")

    # Analyze chunks
    sidebar_count = sum(1 for c in chunks if c.is_sidebar_content)
    print(f"  Sidebar chunks: {sidebar_count}")
    print(f"  Main content chunks: {len(chunks) - sidebar_count}")

    # Show chunk types
    chunk_types = {}
    for c in chunks:
        chunk_types[c.chunk_type] = chunk_types.get(c.chunk_type, 0) + 1
    print(f"  Chunk types: {json.dumps(chunk_types, indent=4)}")

    # Show sample chunks
    print("\n  Sample Chunks:")
    for i, chunk in enumerate(chunks[:3]):
        print(f"\n    [{i+1}] ID: {chunk.chunk_id[:8]}...")
        print(f"        Type: {chunk.chunk_type}")
        print(f"        Hierarchy: {chunk.hierarchy_path or 'N/A'}")
        print(f"        Pages: {chunk.page_range[0]}-{chunk.page_range[1]}")
        print(f"        Sidebar: {chunk.is_sidebar_content}")
        print(f"        Length: {len(chunk.content)} chars")
        content_preview = chunk.content[:150].replace('\n', ' ')
        print(f"        Content: {content_preview}...")

    # Check for long chunks (potential truncation)
    long_chunks = [c for c in chunks if len(c.content) > 5500]
    if long_chunks:
        print(f"\n  ⚠️ Long chunks (>5500 chars): {len(long_chunks)}")
        for c in long_chunks[:3]:
            print(f"      - {c.chunk_id[:8]}: {len(c.content)} chars")

    return metadata, chunks, images


async def index_to_azure(settings, metadata, chunks, images):
    """Index chunks and images to test indexes"""
    print_section("Indexing to Azure")

    # Build page-to-chunk mapping
    page_to_chunks = {}
    for chunk in chunks:
        start_page, end_page = chunk.page_range
        for page in range(start_page, end_page + 1):
            if page not in page_to_chunks:
                page_to_chunks[page] = []
            page_to_chunks[page].append(chunk)

    # Prepare chunk documents
    chunk_dicts = []
    for chunk in chunks:
        chunk_dicts.append({
            "id": chunk.chunk_id,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type,
            "hierarchy_path": chunk.hierarchy_path,
            "page_range": f"{chunk.page_range[0]}-{chunk.page_range[1]}",
            "is_sidebar": chunk.is_sidebar_content,
            "textbook_id": metadata["textbook_id"],
            "textbook_name": metadata["textbook_name"],
            "chapter_id": extract_chapter_id(chunk.hierarchy_path),
            "grade": metadata["grade"],
            "subject": metadata["subject"],
            "semester": metadata["semester"],
        })

    # Prepare image documents with chunk linkage
    image_dicts = []
    for img in images:
        matching_chunks = page_to_chunks.get(img.page_number, [])
        best_chunk = None
        for c in matching_chunks:
            if not c.is_sidebar_content:
                best_chunk = c
                break
        if not best_chunk and matching_chunks:
            best_chunk = matching_chunks[0]

        related_text = ""
        chunk_id = ""
        hierarchy_path = img.hierarchy_path or ""

        if best_chunk:
            chunk_id = best_chunk.chunk_id
            hierarchy_path = best_chunk.hierarchy_path or hierarchy_path
            content_preview = best_chunk.content[:300].replace('\n', ' ').strip()
            if len(best_chunk.content) > 300:
                content_preview += "..."
            related_text = content_preview

        image_dicts.append({
            "id": img.image_id,
            "caption": img.caption or "Görsel",
            "image_type": img.image_type or "unknown",
            "page_number": img.page_number,
            "chunk_id": chunk_id,
            "related_text": related_text,
            "hierarchy_path": hierarchy_path,
            "image_path": str(img.image_path) if img.image_path else "",
            "width": img.width,
            "height": img.height,
            "textbook_id": metadata["textbook_id"],
            "grade": metadata["grade"],
            "subject": metadata["subject"]
        })

    linked_images = sum(1 for i in image_dicts if i["chunk_id"])
    print(f"  Images linked to chunks: {linked_images}/{len(image_dicts)}")

    # Generate embeddings for chunks
    print("\n  Generating embeddings for chunks...")
    contents = []
    for c in chunk_dicts:
        hierarchy = c.get("hierarchy_path", "")
        content = c.get("content", "")

        if len(content) > 5500:
            mid_start = len(content) // 2 - 500
            content = (
                content[:3000] +
                "\n[...]\n" +
                content[mid_start:mid_start + 1000] +
                "\n[...]\n" +
                content[-1500:]
            )
            print(f"    ⚠️ Truncated: {c['id'][:8]}...")

        embed_text = f"{hierarchy}\n\n{content}" if hierarchy else content
        contents.append(embed_text[:6000])

    chunk_embeddings = embed_batch(contents)
    print(f"  Generated {len(chunk_embeddings)} chunk embeddings")

    # Generate embeddings for images (from captions)
    print("  Generating embeddings for images...")
    image_contents = [i["caption"] for i in image_dicts]
    image_embeddings = embed_batch(image_contents) if image_contents else []
    print(f"  Generated {len(image_embeddings)} image embeddings")

    # Upload to Azure
    print("\n  Uploading to Azure...")

    # Upload chunks
    kitap_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=TEST_KITAP_INDEX,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )

    chunk_docs = []
    for chunk, emb in zip(chunk_dicts, chunk_embeddings):
        chunk_docs.append({**chunk, "embedding": emb})

    result = kitap_client.upload_documents(chunk_docs)
    success_count = sum(1 for r in result if r.succeeded)
    print(f"  ✓ Uploaded {success_count}/{len(chunk_docs)} chunks to {TEST_KITAP_INDEX}")

    # Upload images
    if image_dicts:
        image_client = SearchClient(
            endpoint=settings.azure_search_endpoint,
            index_name=TEST_IMAGE_INDEX,
            credential=AzureKeyCredential(settings.azure_search_api_key)
        )

        image_docs = []
        for img, emb in zip(image_dicts, image_embeddings):
            image_docs.append({**img, "embedding": emb})

        result = image_client.upload_documents(image_docs)
        success_count = sum(1 for r in result if r.succeeded)
        print(f"  ✓ Uploaded {success_count}/{len(image_docs)} images to {TEST_IMAGE_INDEX}")

    return chunk_dicts, image_dicts


async def test_search(settings):
    """Run sample searches on test indexes"""
    print_section("Search Tests")

    kitap_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=TEST_KITAP_INDEX,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )

    # Test queries
    test_queries = [
        "hücre bölünmesi",
        "mitoz",
        "kromozom",
        "DNA replikasyonu"
    ]

    for query in test_queries:
        print(f"\n  Query: '{query}'")

        # Generate query embedding
        query_emb = embed_batch([query])[0]

        # Hybrid search
        results = kitap_client.search(
            search_text=query,
            vector_queries=[
                VectorizedQuery(
                    vector=query_emb,
                    k_nearest_neighbors=3,
                    fields="embedding"
                )
            ],
            top=3,
            select=["id", "hierarchy_path", "page_range", "chunk_type"]
        )

        found = False
        for i, r in enumerate(results):
            found = True
            print(f"    [{i+1}] Score: {r['@search.score']:.4f}")
            print(f"        Hierarchy: {r.get('hierarchy_path', 'N/A')}")
            print(f"        Pages: {r.get('page_range', 'N/A')}")
            print(f"        Type: {r.get('chunk_type', 'N/A')}")

        if not found:
            print("    No results found")

    # Test image search
    print_section("Image Search Test")

    image_client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=TEST_IMAGE_INDEX,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )

    # Count images
    all_images = list(image_client.search(search_text="*", top=100, select=["id", "caption", "image_type", "page_number", "chunk_id"]))
    print(f"  Total images indexed: {len(all_images)}")

    if all_images:
        print("\n  Sample images:")
        for i, img in enumerate(all_images[:5]):
            linked = "✓" if img.get("chunk_id") else "✗"
            print(f"    [{i+1}] Page {img.get('page_number')}: {img.get('image_type', 'unknown')} [{linked} linked]")
            print(f"        Caption: {img.get('caption', 'N/A')[:60]}...")


async def main():
    """Main entry point"""
    print_header("DEBUG INDEXING PIPELINE")
    print(f"Timestamp: {datetime.now().isoformat()}")

    settings = get_settings()
    pdf_path = Path("book_ex/biyoloji_11-150-170.pdf")

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return

    # Create test indexes
    await create_test_indexes(settings)

    # Process PDF
    metadata, chunks, images = await process_pdf(pdf_path, settings)

    # Index to Azure
    chunk_dicts, image_dicts = await index_to_azure(settings, metadata, chunks, images)

    # Wait a bit for indexing to complete
    print("\n  Waiting for indexing to complete...")
    await asyncio.sleep(3)

    # Run search tests
    await test_search(settings)

    # Summary
    print_header("SUMMARY")
    print(f"""
  PDF: {pdf_path.name}
  Grade: {metadata['grade']}
  Subject: {metadata['subject']}
  Textbook ID: {metadata['textbook_id']}

  Chunks: {len(chunks)}
    - Sidebar: {sum(1 for c in chunks if c.is_sidebar_content)}
    - Main content: {sum(1 for c in chunks if not c.is_sidebar_content)}

  Images: {len(images)}
    - Linked to chunks: {sum(1 for i in image_dicts if i['chunk_id'])}

  Test Indexes:
    - Chunks: {TEST_KITAP_INDEX}
    - Images: {TEST_IMAGE_INDEX}

  Next Steps:
    1. Check Azure Portal for index contents
    2. Run manual searches to verify quality
    3. If satisfied, run full indexing
""")


if __name__ == "__main__":
    asyncio.run(main())
