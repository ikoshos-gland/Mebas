"""
MEB RAG Sistemi - Decorators for LangGraph Nodes
Error handling and timeout decorators
"""
import asyncio
import functools
from typing import Callable, Any, Dict

from src.agents.state import QuestionAnalysisState


def with_timeout(timeout_seconds: float = 30.0):
    """
    Decorator for state-safe timeout handling on LangGraph nodes.
    
    CRITICAL: On timeout, returns a partial state update with error,
    rather than raising an exception that could break the graph.
    
    Usage:
        @with_timeout(30.0)
        async def my_node(state: QuestionAnalysisState) -> dict:
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(state: QuestionAnalysisState) -> Dict[str, Any]:
            try:
                # Run with timeout
                result = await asyncio.wait_for(
                    func(state),
                    timeout=timeout_seconds
                )
                return result
                
            except asyncio.TimeoutError:
                # Return partial state update with error
                return {
                    "error": f"Timeout: {func.__name__} {timeout_seconds}s aşıldı",
                    "status": "failed"
                }
            except Exception as e:
                # Catch all other errors
                return {
                    "error": f"Error in {func.__name__}: {str(e)}",
                    "status": "failed"
                }
        
        return wrapper
    return decorator


def with_error_handling(func: Callable):
    """
    Decorator for basic error handling on sync nodes.
    
    Catches exceptions and returns partial state with error.
    """
    @functools.wraps(func)
    def wrapper(state: QuestionAnalysisState) -> Dict[str, Any]:
        try:
            return func(state)
        except Exception as e:
            return {
                "error": f"Error in {func.__name__}: {str(e)}",
                "status": "failed"
            }
    
    return wrapper


def with_retry_tracking(func: Callable):
    """
    Decorator that increments retry count on each call.
    
    Used for nodes that may be retried on failure.
    """
    @functools.wraps(func)
    async def wrapper(state: QuestionAnalysisState) -> Dict[str, Any]:
        # Get current retry count
        current_count = state.get("retrieval_retry_count", 0)
        
        try:
            result = await func(state)
            return result
        except Exception as e:
            # Increment retry count on failure
            return {
                "error": str(e),
                "status": "needs_retry",
                "retrieval_retry_count": current_count + 1
            }
    
    return wrapper


def log_node_execution(node_name: str):
    """
    Decorator to log node execution for debugging.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(state: QuestionAnalysisState) -> Dict[str, Any]:
            analysis_id = state.get("analysis_id", "unknown")
            print(f"[{analysis_id}] Executing node: {node_name}")
            
            result = await func(state)
            
            status = result.get("status", "ok")
            error = result.get("error")
            
            if error:
                print(f"[{analysis_id}] {node_name} failed: {error}")
            else:
                print(f"[{analysis_id}] {node_name} completed: {status}")
            
            return result
        
        return wrapper
    return decorator
