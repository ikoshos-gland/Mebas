#!/usr/bin/env python3
"""
Test script for Kazanimlar RAG System
Tests retrieval of learning outcomes (kazanımlar) for a mitosis question
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.azure_config import get_search_client
from config.settings import get_settings
from src.vector_store.parent_retriever import ParentDocumentRetriever


async def test_mitosis_query():
    """Test kazanım retrieval for a mitosis-related question"""

    settings = get_settings()

    print("=" * 60)
    print("KAZANIMLAR RAG SYSTEM TEST")
    print("=" * 60)
    print(f"\nIndex: {settings.azure_search_index_kazanim}")
    print(f"Questions Index: {settings.azure_search_index_questions}")

    # Initialize search clients
    kazanim_client = get_search_client(settings.azure_search_index_kazanim)
    questions_client = get_search_client(settings.azure_search_index_questions)

    # Create retriever
    retriever = ParentDocumentRetriever(
        search_client=questions_client,
        kazanim_client=kazanim_client
    )

    # Test query about mitosis
    test_question = "Mitoz bölünme evreleri nelerdir ve her evrede ne olur?"

    print(f"\n{'─' * 60}")
    print(f"TEST QUERY: {test_question}")
    print(f"{'─' * 60}")

    # Test 1: Direct kazanım search (biology, grade 9)
    print("\n📚 TEST 1: Direct Kazanım Search (Grade 9, Biology)")
    print("-" * 40)

    try:
        results = await retriever.search_kazanimlar_direct(
            student_question=test_question,
            grade=9,
            subject="BİY",  # Biology
            is_exam_mode=False,
            top_k=5
        )

        if results:
            print(f"✅ Found {len(results)} kazanımlar:\n")
            for i, kazanim in enumerate(results, 1):
                print(f"  {i}. [{kazanim.get('kazanim_code', 'N/A')}]")
                print(f"     Grade: {kazanim.get('grade', 'N/A')}")
                print(f"     Subject: {kazanim.get('subject', 'N/A')}")
                print(f"     Score: {kazanim.get('score', 0):.4f}")
                desc = kazanim.get('kazanim_description', 'N/A')
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"     Description: {desc}")
                print()
        else:
            print("⚠️  No results found for grade 9 biology")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Hybrid expansion search (no filters)
    print("\n📚 TEST 2: Hybrid Expansion Search (No Grade Filter)")
    print("-" * 40)

    try:
        results = await retriever.search_hybrid_expansion(
            student_question=test_question,
            grade=None,  # No grade filter
            subject=None,  # No subject filter
            is_exam_mode=False,
            top_k=5
        )

        if results:
            print(f"✅ Found {len(results)} kazanımlar:\n")
            for i, kazanim in enumerate(results, 1):
                print(f"  {i}. [{kazanim.get('kazanim_code', 'N/A')}]")
                print(f"     Grade: {kazanim.get('grade', 'N/A')}")
                print(f"     Subject: {kazanim.get('subject', 'N/A')}")
                print(f"     Score: {kazanim.get('score', 0):.4f}")
                desc = kazanim.get('kazanim_description', 'N/A')
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"     Description: {desc}")
                print()
        else:
            print("⚠️  No results found")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: YKS/Exam mode (cumulative grades)
    print("\n📚 TEST 3: YKS Mode Search (Grade ≤ 12)")
    print("-" * 40)

    try:
        results = await retriever.search_kazanimlar_direct(
            student_question=test_question,
            grade=12,
            subject="BİY",
            is_exam_mode=True,  # Cumulative: grade <= 12
            top_k=5
        )

        if results:
            print(f"✅ Found {len(results)} kazanımlar:\n")
            for i, kazanim in enumerate(results, 1):
                print(f"  {i}. [{kazanim.get('kazanim_code', 'N/A')}]")
                print(f"     Grade: {kazanim.get('grade', 'N/A')}")
                print(f"     Subject: {kazanim.get('subject', 'N/A')}")
                print(f"     Score: {kazanim.get('score', 0):.4f}")
                desc = kazanim.get('kazanim_description', 'N/A')
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                print(f"     Description: {desc}")
                print()
        else:
            print("⚠️  No results found")

    except Exception as e:
        print(f"❌ Error: {e}")

    print("=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


async def check_index_stats():
    """Check if the kazanimlar index has documents"""
    settings = get_settings()
    kazanim_client = get_search_client(settings.azure_search_index_kazanim)

    print("\n📊 INDEX STATISTICS")
    print("-" * 40)

    try:
        # Simple search to check if index is populated
        results = kazanim_client.search(
            search_text="*",
            top=1,
            include_total_count=True
        )

        count = results.get_count()
        print(f"Total documents in kazanimlar index: {count}")

        if count == 0:
            print("⚠️  Index is empty! Run 'python scripts/process_pdfs.py' first.")
            return False
        return True

    except Exception as e:
        print(f"❌ Error checking index: {e}")
        return False


async def main():
    """Main entry point"""
    # Check index first
    has_data = await check_index_stats()

    if has_data:
        await test_mitosis_query()
    else:
        print("\n❌ Cannot run RAG test - index is empty")
        print("Please run: docker compose run --rm api python scripts/process_pdfs.py")


if __name__ == "__main__":
    asyncio.run(main())
