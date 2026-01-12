#!/usr/bin/env python3
"""
Test script for Full RAG + LLM Pipeline
Tests: Kazanim Retrieval → Response Generation → Structured Output Validation
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.azure_config import get_search_client
from config.settings import get_settings
from src.vector_store.parent_retriever import ParentDocumentRetriever
from src.rag.response_generator import ResponseGenerator
from src.rag.output_models import AnalysisOutput


async def test_full_pipeline():
    """Test the complete RAG → LLM pipeline with mitosis query"""

    settings = get_settings()

    print("=" * 70)
    print("FULL RAG + LLM PIPELINE TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    # =========================================================================
    # PHASE 1: KAZANIM RETRIEVAL (RAG)
    # =========================================================================
    print("\n" + "─" * 70)
    print("PHASE 1: KAZANIM RETRIEVAL (RAG)")
    print("─" * 70)

    kazanim_client = get_search_client(settings.azure_search_index_kazanim)
    questions_client = get_search_client(settings.azure_search_index_questions)

    retriever = ParentDocumentRetriever(
        search_client=questions_client,
        kazanim_client=kazanim_client
    )

    test_question = "Mitoz bölünme evreleri nelerdir ve her evrede ne olur?"

    print(f"\nTest Question: {test_question}")
    print("\nSearching kazanimlar...")

    try:
        kazanimlar = await retriever.search_hybrid_expansion(
            student_question=test_question,
            grade=None,  # No filter to get all results
            subject=None,
            is_exam_mode=False,
            top_k=5
        )

        if not kazanimlar:
            print("❌ No kazanimlar found! Cannot proceed with LLM test.")
            return

        print(f"✅ Retrieved {len(kazanimlar)} kazanimlar\n")

        for i, k in enumerate(kazanimlar, 1):
            print(f"  {i}. [{k.get('kazanim_code')}] Score: {k.get('score', 0):.4f}")
            desc = k.get('kazanim_description', '')[:80]
            print(f"     {desc}...")

    except Exception as e:
        print(f"❌ Retrieval Error: {e}")
        return

    # =========================================================================
    # PHASE 2: RESPONSE GENERATION (LLM with Structured Output)
    # =========================================================================
    print("\n" + "─" * 70)
    print("PHASE 2: RESPONSE GENERATION (LLM Structured Output)")
    print("─" * 70)

    print(f"\nModel: {settings.azure_openai_chat_deployment}")
    print("Generating response with structured output...")

    try:
        generator = ResponseGenerator()

        result: AnalysisOutput = await generator.generate(
            question_text=test_question,
            matched_kazanimlar=kazanimlar,
            related_chunks=[],  # No textbook chunks for this test
            related_images=[],
            detected_topics=["mitoz", "hücre bölünmesi", "biyoloji"]
        )

        print("✅ Response generated successfully!\n")

    except Exception as e:
        print(f"❌ LLM Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # =========================================================================
    # PHASE 3: STRUCTURED OUTPUT VALIDATION
    # =========================================================================
    print("\n" + "─" * 70)
    print("PHASE 3: STRUCTURED OUTPUT VALIDATION")
    print("─" * 70)

    validation_results = []

    # Check 1: Summary exists and is non-empty
    check_summary = bool(result.summary and len(result.summary) > 10)
    validation_results.append(("Summary exists", check_summary))

    # Check 2: Solution steps exist
    check_steps = len(result.solution_steps) >= 1
    validation_results.append(("Solution steps exist", check_steps))

    # Check 3: Matched kazanimlar populated
    check_kazanimlar = len(result.matched_kazanimlar) >= 1
    validation_results.append(("Matched kazanimlar populated", check_kazanimlar))

    # Check 4: Each kazanim has required fields
    kazanim_fields_valid = True
    for mk in result.matched_kazanimlar:
        if not mk.kazanim_code or not mk.kazanim_description or not mk.match_reason:
            kazanim_fields_valid = False
            break
    validation_results.append(("Kazanim fields complete", kazanim_fields_valid))

    # Check 5: Confidence score in valid range
    check_confidence = 0.0 <= result.confidence <= 1.0
    validation_results.append(("Confidence in valid range", check_confidence))

    # Check 6: Output is valid Pydantic model
    try:
        json_output = result.model_dump_json()
        check_json = True
    except Exception:
        check_json = False
    validation_results.append(("Valid JSON serialization", check_json))

    # Print validation results
    print("\nValidation Results:")
    all_passed = True
    for name, passed in validation_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False

    # =========================================================================
    # PHASE 4: DETAILED OUTPUT REPORT
    # =========================================================================
    print("\n" + "─" * 70)
    print("PHASE 4: DETAILED OUTPUT REPORT")
    print("─" * 70)

    print(f"\n📝 SUMMARY ({len(result.summary)} chars):")
    print("-" * 40)
    print(result.summary[:500] + "..." if len(result.summary) > 500 else result.summary)

    print(f"\n📋 SOLUTION STEPS ({len(result.solution_steps)} steps):")
    print("-" * 40)
    for step in result.solution_steps[:5]:  # Show first 5 steps
        print(f"  Step {step.step_number}: {step.description[:100]}...")
        if step.result:
            print(f"    → Result: {step.result[:80]}...")

    if result.final_answer:
        print(f"\n🎯 FINAL ANSWER:")
        print("-" * 40)
        print(f"  {result.final_answer}")

    print(f"\n📚 MATCHED KAZANIMLAR ({len(result.matched_kazanimlar)} items):")
    print("-" * 40)
    for mk in result.matched_kazanimlar:
        print(f"  [{mk.kazanim_code}] Score: {mk.match_score:.2f} | Type: {mk.match_type.value}")
        print(f"    Reason: {mk.match_reason[:100]}...")
        if mk.bloom_level:
            print(f"    Bloom Level: {mk.bloom_level.value}")
        print()

    print(f"\n📊 METADATA:")
    print("-" * 40)
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Difficulty: {result.difficulty_estimate.value if result.difficulty_estimate else 'N/A'}")
    print(f"  Topics: {', '.join(result.detected_topics) if result.detected_topics else 'N/A'}")

    if result.study_suggestions:
        print(f"\n💡 STUDY SUGGESTIONS:")
        print("-" * 40)
        for suggestion in result.study_suggestions[:3]:
            print(f"  • {suggestion}")

    if result.prerequisite_gaps:
        print(f"\n⚠️  PREREQUISITE GAPS ({len(result.prerequisite_gaps)} items):")
        print("-" * 40)
        for gap in result.prerequisite_gaps:
            print(f"  [{gap.missing_kazanim_code}] {gap.missing_kazanim_description[:60]}...")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    if all_passed:
        print("\n✅ ALL VALIDATIONS PASSED!")
        print("   The RAG → LLM pipeline is working correctly.")
        print("   Structured output is valid and complete.")
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED!")
        print("   Check the detailed output above for issues.")

    # Output stats
    print(f"\nOutput Statistics:")
    print(f"  • Summary length: {len(result.summary)} chars")
    print(f"  • Solution steps: {len(result.solution_steps)}")
    print(f"  • Matched kazanimlar: {len(result.matched_kazanimlar)}")
    print(f"  • Prerequisite gaps: {len(result.prerequisite_gaps)}")
    print(f"  • Textbook references: {len(result.textbook_references)}")
    print(f"  • Image references: {len(result.image_references)}")
    print(f"  • Study suggestions: {len(result.study_suggestions)}")

    return result


async def main():
    """Main entry point"""
    print("\nStarting full pipeline test...\n")
    result = await test_full_pipeline()

    if result:
        # Save full JSON output for inspection
        output_file = project_root / "scripts" / "test_output.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📁 Full JSON output saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
