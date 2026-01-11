"""
MEB RAG Sistemi - LangGraph Node Implementations
All graph nodes that return partial state updates
"""
from typing import Dict, Any
import base64

from src.agents.state import QuestionAnalysisState, get_effective_grade, get_effective_subject
from src.agents.decorators import with_timeout, log_node_execution
from config.settings import get_settings

# Get settings for RAG configuration
settings = get_settings()


@log_node_execution("analyze_input")
@with_timeout(settings.timeout_analyze_input)
async def analyze_input(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Analyze input (text or image).
    
    If image is present, uses Vision API.
    Otherwise just processes text.
    
    RETURNS: Partial state update, NOT full state!
    """
    from src.vision import QuestionAnalysisPipeline, QuestionAnalysisInput
    
    result_update: Dict[str, Any] = {}
    
    # Check if we have an image
    
    if state.get("question_image_base64"):
        # Decode and analyze with Vision
        # Handle data URL format: strip "data:image/...;base64," prefix if present
        image_data = state["question_image_base64"]
        if image_data.startswith("data:"):
            # Extract base64 part after the comma
            image_data = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(image_data)
        
        pipeline = QuestionAnalysisPipeline()
        analysis = await pipeline.analyze_from_bytes(
            image_bytes=image_bytes,
            user_grade=state.get("user_grade"),
            subject_hint=state.get("user_subject")
        )
        
        result_update.update({
            "question_text": analysis.extracted_text,
            "vision_result": {
                "question_type": analysis.question_type,
                "topics": analysis.topics,
                "math_expressions": analysis.math_expressions,
                "confidence": analysis.confidence
            },
            "ai_estimated_grade": analysis.grade if analysis.grade_source == "ai" else None,
            "detected_topics": analysis.topics,
            "math_expressions": analysis.math_expressions,
            "question_type": analysis.question_type,
            "is_exam_mode": state.get("is_exam_mode", False),
            "status": "processing"
        })
    else:
        # Text-only input
        result_update.update({
            "question_text": state.get("question_text", ""),
            "detected_topics": [],
            "is_exam_mode": state.get("is_exam_mode", False),
            "status": "processing"
        })
    
    return result_update


@log_node_execution("retrieve_kazanimlar")
@with_timeout(settings.timeout_retrieve)
async def retrieve_kazanimlar(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Retrieve matching kazanımlar using hybrid search.

    FIXED: Now searches DIRECTLY in kazanımlar index (PRIMARY source)
    instead of searching synthetic questions.

    CRITICAL: Uses effective grade (user_grade > ai_estimated_grade)

    On retry, relaxes filters.
    """
    from config.settings import get_settings
    from config.azure_config import get_search_client
    from src.vector_store import ParentDocumentRetriever

    settings = get_settings()

    # Get effective grade and subject
    grade = get_effective_grade(state)
    subject = get_effective_subject(state)

    # Get retry count for filter relaxation
    retry_count = state.get("retrieval_retry_count", 0)

    # Relax filters on retry
    if retry_count >= 1:
        grade = None  # Remove grade filter
    if retry_count >= 2:
        subject = None  # Remove subject filter too

    try:
        # PRIMARY: Search kazanımlar index directly (MEB learning objectives)
        kazanim_client = get_search_client(settings.azure_search_index_kazanim)
        # SECONDARY: Questions index for hybrid expansion
        questions_client = get_search_client(settings.azure_search_index_questions)

        retriever = ParentDocumentRetriever(
            search_client=questions_client,
            kazanim_client=kazanim_client
        )

        # HYBRID QUERY EXPANSION: Search both indexes in parallel
        # - Kazanımlar index: direct semantic match (PRIMARY)
        # - Sentetik sorular: similar questions (SECONDARY, can discover missed kazanımlar)
        results = await retriever.search_hybrid_expansion(
            student_question=state.get("question_text", ""),
            grade=grade,
            subject=subject,
            is_exam_mode=state.get("is_exam_mode", False),
            top_k=settings.rag_kazanim_top_k,
            kazanim_weight=settings.rag_hybrid_kazanim_weight,
            question_weight=settings.rag_hybrid_question_weight,
            synergy_bonus=settings.rag_hybrid_synergy_bonus
        )
        
        if not results:
            # CRITICAL: Increment retry count when returning needs_retry
            return {
                "matched_kazanimlar": [],
                "status": "needs_retry",
                "retrieval_retry_count": retry_count + 1
            }
        
        
        # Deduplicate results by kazanim_code
        seen_codes = set()
        unique_results = []
        
        print(f"DEBUG: Raw retrieval count: {len(results)}")
        
        for r in results:
            code = r.get("kazanim_code")
            desc = r.get("kazanim_description", "").strip()
            score = r.get("score", 0)
            
            # DATA CLEANING: Filter out corrupt descriptions
            # 1. Too short or garbage
            if len(desc) < settings.retrieval_min_description_length or desc.lower() in ["a-", "b-", "c-", "d-", "e-", "none"]:
                print(f"DEBUG: Dropping corrupt result (garbage): {code} | Desc: '{desc[:50]}...'")
                continue

            # 2. Too long (Omnibus Error - likely contains multiple merged kazanımlar)
            if len(desc) > settings.retrieval_max_description_length:
                print(f"DEBUG: Dropping corrupt result (too long): {code} | Len: {len(desc)}")
                continue

            # 3. Contains other kazanım headers (Omnibus Error)
            # Check for pattern like "### BİY" or just distinct kazanim codes in text
            if "### BİY" in desc or "### MAT" in desc or "### FİZ" in desc or "### KİM" in desc:
                 print(f"DEBUG: Dropping corrupt result (embedded headers): {code}")
                 continue
                 
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_results.append(r)
                print(f"DEBUG: Kept result: {code} | Score: {score}")
                
        # If filtering removed all results, retry
        if not unique_results and results:
             print(f"DEBUG: All results were filtered out. Triggering retry.")
             return {
                 "matched_kazanimlar": [],
                 "status": "needs_retry",
                 "retrieval_retry_count": retry_count + 1
             }
        
        # QUALITY CHECK: Check for weak results
        # If we have results but they are weak AND we haven't retried yet, force a retry
        # This allows switching from "strict mode" to "relaxed mode" if strict mode yields poor results
        first_score = unique_results[0]["score"] if unique_results else 0
        weak_signal = len(unique_results) < 2 or first_score < settings.retrieval_weak_signal_threshold
        
        if weak_signal and retry_count == 0:
             return {
                 "matched_kazanimlar": [],
                 "status": "needs_retry",
                 "retrieval_retry_count": retry_count + 1
             }
        
        # SIBLING RETRIEVAL: Search for "Alternative/Related" kazanımlar
        # Use the best match's code to find neighbors (12.1.1 -> 12.1.2)
        if unique_results:
            best_match = unique_results[0]
            best_code = best_match.get("kazanim_code")
            
            if best_code:
                try:
                    siblings = await retriever.search_siblings_async(
                        target_code=best_code,
                        grade=grade,
                        subject=subject
                    )
                    
                    if siblings:
                        # Append siblings to results
                        # Ensure we don't duplicate existing ones
                        existing_codes = {r.get("kazanim_code") for r in unique_results}
                        for sibling in siblings:
                            if sibling.get("kazanim_code") not in existing_codes:
                                unique_results.append(sibling)
                                
                except Exception as e:
                    print(f"Sibling search error: {e}")
                    # Don't fail the whole request, just skip siblings

        return {
            "matched_kazanimlar": unique_results,
            "status": "processing"
        }
        
    except Exception as e:
        # CRITICAL: Increment retry count on error too
        return {
            "error": f"Kazanım arama hatası: {str(e)}",
            "status": "needs_retry",
            "retrieval_retry_count": retry_count + 1
        }


@log_node_execution("retrieve_textbook")
@with_timeout(settings.timeout_retrieve)
async def retrieve_textbook(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Retrieve related textbook chunks and IMAGES for matched kazanımlar.

    CRITICAL: Uses grade/subject filtering for pedagogical correctness.
    """
    from config.settings import get_settings
    from config.azure_config import get_search_client
    from src.vector_store import ParentDocumentRetriever, ImageRetriever
    from src.agents.state import get_effective_grade

    matched = state.get("matched_kazanimlar", [])
    question_text = state.get("question_text", "")

    if not matched:
        return {
            "related_chunks": [],
            "related_images": []
        }

    try:
        settings = get_settings()

        # Get grade/subject for filtering - CRITICAL for pedagogical correctness
        grade = get_effective_grade(state)
        subject = state.get("subject")
        is_exam_mode = state.get("is_exam_mode", False)

        # 1. Retrieve Textbook Chunks
        # Create retriever with both clients for consistency
        kazanim_client = get_search_client(settings.azure_search_index_kazanim)
        questions_client = get_search_client(settings.azure_search_index_questions)
        retriever = ParentDocumentRetriever(
            search_client=questions_client,
            kazanim_client=kazanim_client
        )

        kazanim_codes = [k.get("kazanim_code") for k in matched]

        related_chunks = await retriever.search_textbook_by_kazanimlar(
            kazanim_codes=kazanim_codes,
            question_text=question_text,
            grade=grade,
            subject=subject,
            is_exam_mode=is_exam_mode,
            top_k=settings.rag_textbook_top_k
        )
        
        # 2. Retrieve Related Images
        # We search for images using the question text which describes the topic
        image_client = get_search_client(settings.azure_search_index_images)
        image_retriever = ImageRetriever(image_client)

        # Also try to use topics if available
        search_query = question_text
        if state.get("detected_topics"):
            search_query += " " + " ".join(state.get("detected_topics"))

        # CRITICAL: Apply same grade/subject filters to images
        related_images = await image_retriever.search_by_description_async(
            description=search_query,
            grade=grade,
            subject=subject,
            is_exam_mode=is_exam_mode,
            top_k=3
        )
        
        return {
            "related_chunks": related_chunks,
            "related_images": related_images
        }
        
    except Exception as e:
        print(f"Textbook retrieval error: {e}")
        return {
            "related_chunks": [],
            "related_images": []
        }


@log_node_execution("rerank_results")
@with_timeout(settings.timeout_rerank)
async def rerank_results(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Rerank retrieved results using LLM for better relevance.
    
    Uses the LLMReranker to score each kazanım's relevance
    to the question and reorders by blended score.
    """
    matched = state.get("matched_kazanimlar", [])
    question_text = state.get("question_text", "")
    
    if len(matched) <= 1:
        return {}  # No reranking needed
    
    if not question_text:
        # Can't rerank without question text
        return {"matched_kazanimlar": matched[:5]}
    
    try:
        from src.rag.reranker import LLMReranker
        
        reranker = LLMReranker()
        reranked = await reranker.rerank(
            question=question_text,
            kazanimlar=matched,
            top_k=settings.rag_kazanim_top_k,
            score_blend_ratio=settings.reranker_score_blend_ratio
        )

        # Filter by confidence threshold
        filtered = [
            k for k in reranked
            if k.get("blended_score", 0) >= settings.rag_confidence_threshold
        ]

        # Ensure minimum kazanımlar are always returned for better context
        if len(filtered) < settings.retrieval_min_kazanimlar and reranked:
            filtered = reranked[:settings.retrieval_min_kazanimlar]
        
        return {"matched_kazanimlar": filtered}

    except Exception as e:
        print(f"[rerank_results] Reranking error: {e}, using original order")
        # Fallback to original order
        return {"matched_kazanimlar": matched[:5]}


@log_node_execution("track_progress")
@with_timeout(10.0)
async def track_progress(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Auto-track high-confidence kazanımlar to user progress.

    Runs AFTER rerank_results when we have final confidence scores.
    Only tracks kazanımlar with blended_score >= CONFIDENCE_THRESHOLD (0.80).

    REQUIRES: user_id in state (from authenticated request)
    """
    CONFIDENCE_THRESHOLD = 0.80

    matched = state.get("matched_kazanimlar", [])
    user_id = state.get("user_id")
    conversation_id = state.get("conversation_id")

    # Can't track without user
    if not user_id:
        return {"tracked_kazanim_codes": []}

    # No kazanımlar to track
    if not matched:
        return {"tracked_kazanim_codes": []}

    tracked_codes = []

    try:
        from src.database.db import get_session
        from src.database.models import UserKazanimProgress
        from datetime import datetime

        db = get_session()

        for kazanim in matched:
            # Get the best available score
            score = kazanim.get("blended_score", kazanim.get("score", 0))
            code = kazanim.get("kazanim_code")

            if not code:
                continue

            # Only track high-confidence kazanımlar
            if score < CONFIDENCE_THRESHOLD:
                continue

            # Check if already tracked (idempotent)
            existing = db.query(UserKazanimProgress).filter(
                UserKazanimProgress.user_id == user_id,
                UserKazanimProgress.kazanim_code == code
            ).first()

            if existing:
                # Already tracked, skip
                continue

            # Create new progress entry
            progress = UserKazanimProgress(
                user_id=user_id,
                kazanim_code=code,
                status="tracked",
                initial_confidence_score=score,
                source_conversation_id=conversation_id,
                tracked_at=datetime.utcnow()
            )
            db.add(progress)
            tracked_codes.append(code)

        if tracked_codes:
            db.commit()
            print(f"[track_progress] Tracked {len(tracked_codes)} kazanımlar for user {user_id}: {tracked_codes}")

        db.close()

    except Exception as e:
        print(f"[track_progress] Error tracking progress: {e}")

    return {"tracked_kazanim_codes": tracked_codes}


@log_node_execution("synthesize_interdisciplinary")
@with_timeout(settings.timeout_synthesize)
async def synthesize_interdisciplinary(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Synthesize related kazanımlar and suggest learning path.

    Analyzes matched kazanımlar to find:
    - Prerequisite relationships
    - Parallel/related concepts
    - Suggested learning order with reasoning
    """
    from langchain_openai import AzureChatOpenAI
    from src.rag.output_models import InterdisciplinarySynthesis

    matched = state.get("matched_kazanimlar", [])

    if len(matched) < 2:
        # Need at least 2 kazanımlar for synthesis
        return {"interdisciplinary_synthesis": None}

    settings = get_settings()

    try:
        # Use the main chat model for synthesis
        llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=settings.llm_temperature_creative
        )

        structured_llm = llm.with_structured_output(InterdisciplinarySynthesis)

        SYNTHESIS_PROMPT = """Sen bir MEB eğitim uzmanısın. Aşağıdaki kazanımları analiz et ve aralarındaki ilişkileri bul.

## Kazanımlar
{kazanimlar}

## Görev
1. Kazanımlar arasındaki ilişkileri tespit et (ön koşul, paralel, genişleme, uygulama)
2. Öğrenci için en verimli öğrenme sırasını belirle
3. Her kazanım için öğrenme sırasını ve nedenini açıkla
4. Ortak kilit kavramları listele
5. Pratik çalışma önerileri ver

İLİŞKİ TÜRLERİ:
- prerequisite: Biri diğerinin ön koşulu (önce öğrenilmeli)
- parallel: Aynı anda öğrenilebilir, birbirini destekler
- extension: Biri diğerinin genişlemesi/derinleşmesi
- application: Biri diğerinin pratik uygulaması

ÖNEMLİ: Öğrenme sırası mantıklı ve pedagojik açıdan doğru olmalı."""

        # Format kazanımlar (limit to top 7 for token efficiency)
        kazanim_text = ""
        for i, k in enumerate(matched[:7], 1):
            code = k.get("kazanim_code", "")
            desc = k.get("kazanim_description", "")
            title = k.get("kazanim_title", "")
            grade = k.get("grade", "?")
            kazanim_text += f"{i}. [{code}] (Sınıf {grade}) {title or desc[:100]}\n"
            if title and desc:
                kazanim_text += f"   Açıklama: {desc[:200]}...\n"

        result = await structured_llm.ainvoke([
            {"role": "system", "content": "Sen bir MEB müfredat ve pedagoji uzmanısın. Kazanımlar arası ilişkileri analiz et ve öğrenme yolu öner."},
            {"role": "user", "content": SYNTHESIS_PROMPT.format(kazanimlar=kazanim_text)}
        ])

        return {"interdisciplinary_synthesis": result.model_dump()}

    except Exception as e:
        print(f"[synthesize_interdisciplinary] Error: {e}")
        return {"interdisciplinary_synthesis": None}


@log_node_execution("generate_response")
@with_timeout(settings.timeout_generate_response)
async def generate_response(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Generate final response using RAG.
    """
    from src.rag.response_generator import ResponseGenerator
    
    matched = state.get("matched_kazanimlar", [])
    
    if not matched:
        return {
            "response": {
                "message": "Maalesef bu soru için uygun bir kazanım bulunamadı.",
                "kazanimlar": [],
                "suggestions": []
            },
            "status": "success"
        }
    
    try:
        generator = ResponseGenerator()
        
        analysis_result = await generator.generate(
            question_text=state.get("question_text", ""),
            matched_kazanimlar=matched,
            related_chunks=state.get("related_chunks", []),
            related_images=state.get("related_images", []),
            detected_topics=state.get("detected_topics", [])
        )
        
        return {
            "response": analysis_result.model_dump(),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Response generation error: {e}")
        # Fallback
        return {
            "response": {
                "message": f"{len(matched)} kazanım bulundu fakat analiz üretilemedi.",
                "kazanimlar": matched,
                "error": str(e)
            },
            "status": "partial_success"
        }


@log_node_execution("find_prerequisite_gaps")
@with_timeout(settings.timeout_gap_finder)
async def find_prerequisite_gaps(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Find prerequisite knowledge gaps for matched kazanımlar.

    Uses database relationships to identify missing prerequisites.
    Falls back to heuristic-based gap finder if database is unavailable.
    """
    matched = state.get("matched_kazanimlar", [])

    if not matched:
        return {"prerequisite_gaps": []}

    grade = get_effective_grade(state)

    try:
        # Try database-backed finder first
        from src.rag.gap_finder import GapFinder
        from src.database.db import get_session

        db = get_session()
        finder = GapFinder(db)

        # Find gaps based on matched kazanımlar
        gaps = finder.find_gaps_from_analysis(matched, grade)
        db.close()

        return {"prerequisite_gaps": gaps}

    except Exception as e:
        print(f"[find_prerequisite_gaps] Database finder failed: {e}, using heuristic fallback")

        try:
            # Fallback to heuristic-based finder
            from src.rag.gap_finder import SimpleGapFinder

            finder = SimpleGapFinder()
            kazanim_codes = [k.get("kazanim_code") for k in matched if k.get("kazanim_code")]
            gaps = finder.find_gaps(kazanim_codes, grade)

            return {"prerequisite_gaps": gaps}

        except Exception as fallback_error:
            print(f"[find_prerequisite_gaps] Heuristic finder also failed: {fallback_error}")
            return {"prerequisite_gaps": []}


@log_node_execution("handle_error")
async def handle_error(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Handle error state.
    """
    error = state.get("error", "Bilinmeyen hata")

    return {
        "response": {
            "message": f"İşlem sırasında bir hata oluştu: {error}",
            "kazanimlar": [],
            "error": error
        },
        "status": "failed"
    }


# Node registry for graph builder
NODE_REGISTRY = {
    "analyze_input": analyze_input,
    "retrieve_kazanimlar": retrieve_kazanimlar,
    "retrieve_textbook": retrieve_textbook,
    "rerank_results": rerank_results,
    "track_progress": track_progress,
    "find_prerequisite_gaps": find_prerequisite_gaps,
    "synthesize_interdisciplinary": synthesize_interdisciplinary,
    "generate_response": generate_response,
    "handle_error": handle_error
}
