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
    track_progress,
    find_prerequisite_gaps,
    synthesize_interdisciplinary,
    generate_response,
    handle_chat,
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
    START → analyze_input → [message_type?]
        → CHAT (greeting/general) → handle_chat → END
        → ACADEMIC → retrieve_kazanimlar → [success?]
            → YES → retrieve_textbook → rerank_results → track_progress
                  → find_prerequisite_gaps → synthesize_interdisciplinary → generate_response → END
            → RETRY → retrieve_kazanimlar (with relaxed filters)
            → ERROR → handle_error → END
        → ERROR → handle_error → END

    track_progress node: Auto-tracks high-confidence kazanımlar (>=80%) to user's progress.
    find_prerequisite_gaps node: Identifies prerequisite knowledge gaps for matched kazanımlar.
    handle_chat node: Handles greetings and general chat without RAG overhead.

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
    workflow.add_node("track_progress", track_progress)
    workflow.add_node("find_prerequisite_gaps", find_prerequisite_gaps)
    workflow.add_node("synthesize_interdisciplinary", synthesize_interdisciplinary)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("handle_chat", handle_chat)
    workflow.add_node("handle_error", handle_error)

    # ===== SET ENTRY POINT =====
    workflow.set_entry_point("analyze_input")

    # ===== ADD CONDITIONAL EDGES =====

    # After analyze_input: check message type and route accordingly
    workflow.add_conditional_edges(
        "analyze_input",
        check_analysis_success,
        {
            "continue": "retrieve_kazanimlar",  # Academic question → RAG pipeline
            "chat": "handle_chat",              # Greeting/chat → Simple response
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
    workflow.add_edge("rerank_results", "track_progress")
    workflow.add_edge("track_progress", "find_prerequisite_gaps")
    workflow.add_edge("find_prerequisite_gaps", "synthesize_interdisciplinary")
    workflow.add_edge("synthesize_interdisciplinary", "generate_response")
    workflow.add_edge("generate_response", END)
    workflow.add_edge("handle_chat", END)  # Chat responses go directly to END
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
        thread_id: Optional[str] = None,
        user_id: Optional[int] = None,
        conversation_id: Optional[str] = None
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
            user_id: User ID for progress tracking (auto-tracks high-confidence kazanımlar)
            conversation_id: Conversation ID for source tracking

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
            is_exam_mode=is_exam_mode,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Config for checkpointing - always provide thread_id if checkpointer exists
        config = {}
        if self.checkpointer:
            import uuid
            # Use provided thread_id or generate a new one
            effective_thread_id = thread_id if thread_id else str(uuid.uuid4())
            config = {"configurable": {"thread_id": effective_thread_id}}

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
        thread_id: Optional[str] = None,
        user_id: Optional[int] = None,
        conversation_id: Optional[str] = None
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
            is_exam_mode=is_exam_mode,
            user_id=user_id,
            conversation_id=conversation_id
        )

        # Config for checkpointing - always provide thread_id if checkpointer exists
        config = {}
        if self.checkpointer:
            import uuid
            effective_thread_id = thread_id if thread_id else str(uuid.uuid4())
            config = {"configurable": {"thread_id": effective_thread_id}}

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
