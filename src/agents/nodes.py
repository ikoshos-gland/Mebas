"""
MEB RAG Sistemi - LangGraph Node Implementations
All graph nodes that return partial state updates
"""
from typing import Dict, Any
import base64

from src.agents.state import QuestionAnalysisState, get_effective_grade, get_effective_subject
from src.agents.decorators import with_timeout, log_node_execution


@log_node_execution("analyze_input")
@with_timeout(60.0)
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
        image_bytes = base64.b64decode(state["question_image_base64"])
        
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
            "status": "processing"
        })
    else:
        # Text-only input
        result_update.update({
            "question_text": state.get("question_text", ""),
            "detected_topics": [],
            "status": "processing"
        })
    
    return result_update


@log_node_execution("retrieve_kazanimlar")
@with_timeout(30.0)
async def retrieve_kazanimlar(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Retrieve matching kazanımlar using hybrid search.
    
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
        search_client = get_search_client(settings.azure_search_index_questions)
        retriever = ParentDocumentRetriever(search_client)
        
        results = await retriever.search_async(
            student_question=state.get("question_text", ""),
            grade=grade,
            subject=subject,
            is_exam_mode=state.get("is_exam_mode", False),
            top_k=10
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
        for r in results:
            code = r.get("kazanim_code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                unique_results.append(r)
        
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
@with_timeout(30.0)
async def retrieve_textbook(state: QuestionAnalysisState) -> Dict[str, Any]:
    """
    Node: Retrieve related textbook chunks and IMAGES for matched kazanımlar.
    """
    from config.settings import get_settings
    from config.azure_config import get_search_client
    from src.vector_store import ParentDocumentRetriever, ImageRetriever

    matched = state.get("matched_kazanimlar", [])
    question_text = state.get("question_text", "")
    
    if not matched:
        return {
            "related_chunks": [],
            "related_images": []
        }
    
    try:
        settings = get_settings()
        
        # 1. Retrieve Textbook Chunks
        search_client = get_search_client(settings.azure_search_index_questions)
        retriever = ParentDocumentRetriever(search_client)
        
        kazanim_codes = [k.get("kazanim_code") for k in matched]
        
        related_chunks = await retriever.search_textbook_by_kazanimlar(
            kazanim_codes=kazanim_codes,
            question_text=question_text,
            top_k=3
        )
        
        # 2. Retrieve Related Images
        # We search for images using the question text which describes the topic
        image_client = get_search_client(settings.azure_search_index_images)
        image_retriever = ImageRetriever(image_client)
        
        # Also try to use topics if available
        search_query = question_text
        if state.get("detected_topics"):
            search_query += " " + " ".join(state.get("detected_topics"))
            
        related_images = await image_retriever.search_by_description_async(
            description=search_query,
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
@with_timeout(30.0)  # Increased timeout for LLM call
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
            top_k=5,
            score_blend_ratio=0.5  # 50% original, 50% LLM score
        )
        
        return {"matched_kazanimlar": reranked}
        
    except Exception as e:
        print(f"[rerank_results] Reranking error: {e}, using original order")
        # Fallback to original order
        return {"matched_kazanimlar": matched[:5]}


@log_node_execution("generate_response")
@with_timeout(60.0)
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
    "generate_response": generate_response,
    "handle_error": handle_error
}
