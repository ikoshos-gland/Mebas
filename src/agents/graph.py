"""
MEB RAG Sistemi - LangGraph Graph Assembly
Main graph definition for question analysis workflow
"""
from typing import Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import QuestionAnalysisState
from src.agents.nodes import (
    analyze_input,
    retrieve_kazanimlar,
    retrieve_textbook,
    rerank_results,
    generate_response,
    handle_error
)
from src.agents.conditions import (
    check_analysis_success,
    check_retrieval_success
)


def create_meb_rag_graph(checkpointer=None) -> StateGraph:
    """
    Create the MEB RAG question analysis graph.
    
    Graph Flow:
    START → analyze_input → [success?]
        → YES → retrieve_kazanimlar → [success?]
            → YES → retrieve_textbook → rerank_results → generate_response → END
            → RETRY → retrieve_kazanimlar (with relaxed filters)
            → ERROR → handle_error → END
        → NO → handle_error → END
    
    Args:
        checkpointer: Optional checkpointer for state persistence
                     Use MemorySaver for dev, PostgresSaver for prod
    
    Returns:
        Compiled LangGraph
    """
    # Create graph with state type
    workflow = StateGraph(QuestionAnalysisState)
    
    # ===== ADD NODES =====
    workflow.add_node("analyze_input", analyze_input)
    workflow.add_node("retrieve_kazanimlar", retrieve_kazanimlar)
    workflow.add_node("retrieve_textbook", retrieve_textbook)
    workflow.add_node("rerank_results", rerank_results)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("handle_error", handle_error)
    
    # ===== SET ENTRY POINT =====
    workflow.set_entry_point("analyze_input")
    
    # ===== ADD CONDITIONAL EDGES =====
    
    # After analyze_input: check success
    workflow.add_conditional_edges(
        "analyze_input",
        check_analysis_success,
        {
            "continue": "retrieve_kazanimlar",
            "error": "handle_error"
        }
    )
    
    # After retrieve_kazanimlar: check success with retry
    workflow.add_conditional_edges(
        "retrieve_kazanimlar",
        check_retrieval_success,
        {
            "continue": "retrieve_textbook",
            "retry": "retrieve_kazanimlar",  # Retry loop!
            "error": "handle_error"
        }
    )
    
    # ===== ADD NORMAL EDGES =====
    workflow.add_edge("retrieve_textbook", "rerank_results")
    workflow.add_edge("rerank_results", "generate_response")
    workflow.add_edge("generate_response", END)
    workflow.add_edge("handle_error", END)
    
    # ===== COMPILE =====
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


class MebRagGraph:
    """
    Main interface for the MEB RAG graph.
    
    Handles both sync and async execution,
    with optional persistence.
    """
    
    def __init__(self, use_memory: bool = True, postgres_checkpointer=None):
        """
        Args:
            use_memory: Use in-memory checkpointing (dev mode)
            postgres_checkpointer: PostgresSaver for production
        """
        if postgres_checkpointer:
            self.checkpointer = postgres_checkpointer
        elif use_memory:
            self.checkpointer = MemorySaver()
        else:
            self.checkpointer = None
        
        self.graph = create_meb_rag_graph(self.checkpointer)
    
    async def analyze(
        self,
        question_text: str = "",
        question_image_base64: Optional[str] = None,
        user_grade: Optional[int] = None,
        user_subject: Optional[str] = None,
        is_exam_mode: bool = False,
        thread_id: Optional[str] = None
    ) -> QuestionAnalysisState:
        """
        Analyze a question (async).
        
        Args:
            question_text: Question text (or empty if image-only)
            question_image_base64: Base64 encoded image
            user_grade: User-provided grade (takes priority!)
            user_subject: User-provided subject hint
            is_exam_mode: YKS mode (True=grade le X, False=grade eq X)
            thread_id: Thread ID for checkpointing
            
        Returns:
            Final state with analysis results
        """
        from src.agents.state import create_initial_state
        
        # Create initial state
        initial_state = create_initial_state(
            question_text=question_text,
            question_image_base64=question_image_base64,
            user_grade=user_grade,
            user_subject=user_subject,
            is_exam_mode=is_exam_mode
        )
        
        # Config for checkpointing
        config = {}
        if thread_id and self.checkpointer:
            config = {"configurable": {"thread_id": thread_id}}
        
        # Run graph
        result = await self.graph.ainvoke(initial_state, config=config)
        
        return result
    
    def analyze_sync(
        self,
        question_text: str = "",
        question_image_base64: Optional[str] = None,
        user_grade: Optional[int] = None,
        user_subject: Optional[str] = None,
        is_exam_mode: bool = False,
        thread_id: Optional[str] = None
    ) -> QuestionAnalysisState:
        """
        Analyze a question (sync version).
        """
        from src.agents.state import create_initial_state
        
        initial_state = create_initial_state(
            question_text=question_text,
            question_image_base64=question_image_base64,
            user_grade=user_grade,
            user_subject=user_subject,
            is_exam_mode=is_exam_mode
        )
        
        config = {}
        if thread_id and self.checkpointer:
            config = {"configurable": {"thread_id": thread_id}}
        
        result = self.graph.invoke(initial_state, config=config)
        
        return result
    
    async def stream_analysis(
        self,
        question_text: str = "",
        question_image_base64: Optional[str] = None,
        user_grade: Optional[int] = None,
        user_subject: Optional[str] = None,
        is_exam_mode: bool = False
    ):
        """
        Stream analysis events for real-time updates.
        
        Yields events as they happen for SSE endpoints.
        """
        from src.agents.state import create_initial_state
        
        initial_state = create_initial_state(
            question_text=question_text,
            question_image_base64=question_image_base64,
            user_grade=user_grade,
            user_subject=user_subject,
            is_exam_mode=is_exam_mode
        )
        
        async for event in self.graph.astream_events(initial_state, version="v2"):
            yield event
