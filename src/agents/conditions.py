"""
MEB RAG Sistemi - LangGraph Edge Conditions
Conditional routing for the state machine
"""
from typing import Literal

from src.agents.state import QuestionAnalysisState
from config.settings import get_settings

# Get settings for retry configuration
settings = get_settings()

# Export constant for backward compatibility
MAX_RETRIEVAL_RETRIES = settings.retrieval_max_retries


def check_analysis_success(
    state: QuestionAnalysisState
) -> Literal["continue", "error"]:
    """
    Check if input analysis was successful.
    
    Returns:
        "continue" → proceed to retrieval
        "error" → go to error handler
    """
    # Check for explicit error
    if state.get("error"):
        return "error"
    
    # Check if we have question text
    if not state.get("question_text"):
        return "error"
    
    return "continue"


def check_retrieval_success(
    state: QuestionAnalysisState
) -> Literal["continue", "retry", "error"]:
    """
    Check if kazanım retrieval was successful.
    
    CRITICAL: Retry logic is handled HERE at the graph level,
    NOT inside the node. This prevents infinite loops.
    
    Returns:
        "continue" → proceed to textbook retrieval
        "retry" → retry with relaxed filters
        "error" → go to error handler (max retries exceeded)
    """
    status = state.get("status", "")
    retry_count = state.get("retrieval_retry_count", 0)
    matched = state.get("matched_kazanimlar", [])
    
    # Success case
    if matched and status != "needs_retry":
        return "continue"
    
    # Check if we should retry
    if status == "needs_retry" and retry_count < settings.retrieval_max_retries:
        return "retry"
    
    # Max retries exceeded or error
    if retry_count >= settings.retrieval_max_retries:
        return "error"
    
    # If we have results, continue
    if matched:
        return "continue"
    
    # No results, try to retry
    if retry_count < settings.retrieval_max_retries:
        return "retry"
    
    return "error"


def check_has_results(
    state: QuestionAnalysisState
) -> Literal["has_results", "no_results"]:
    """
    Check if we have any retrieval results.
    
    Returns:
        "has_results" → proceed to reranking
        "no_results" → skip to response generation
    """
    matched = state.get("matched_kazanimlar", [])
    chunks = state.get("related_chunks", [])
    
    if matched or chunks:
        return "has_results"
    
    return "no_results"


def should_include_images(
    state: QuestionAnalysisState
) -> Literal["with_images", "text_only"]:
    """
    Check if we should include image references in response.
    
    Returns:
        "with_images" → include figure references
        "text_only" → text only response
    """
    images = state.get("related_images", [])
    
    if images:
        return "with_images"
    
    return "text_only"


def get_final_status(
    state: QuestionAnalysisState
) -> Literal["success", "partial", "failed"]:
    """
    Determine final status of the analysis.
    
    Returns:
        "success" → complete analysis with results
        "partial" → some results but not complete
        "failed" → no useful results
    """
    error = state.get("error")
    matched = state.get("matched_kazanimlar", [])
    response = state.get("response")
    
    if error:
        return "failed"
    
    if matched and response:
        return "success"
    
    if response:
        return "partial"
    
    return "failed"


# Condition registry for graph builder
CONDITION_REGISTRY = {
    "check_analysis_success": check_analysis_success,
    "check_retrieval_success": check_retrieval_success,
    "check_has_results": check_has_results,
    "should_include_images": should_include_images,
    "get_final_status": get_final_status
}
