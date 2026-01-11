"""
MEB RAG Sistemi - Pytest Configuration and Fixtures
Shared fixtures for all test modules
"""
import os
import pytest
import asyncio
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List

# Set test environment before importing settings - use in-memory DB to avoid permission issues
_test_db_path = ":memory:"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


# ================== Pytest Configuration ==================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ================== Mock Settings ==================

@pytest.fixture
def mock_settings():
    """Mock settings for testing without real Azure credentials."""
    settings = MagicMock()
    # Azure OpenAI
    settings.azure_openai_endpoint = "https://mock.openai.azure.com"
    settings.azure_openai_api_key = "mock-key"
    settings.azure_openai_api_version = "2024-12-01-preview"
    settings.azure_openai_chat_deployment = "gpt-4o"
    settings.azure_openai_embedding_deployment = "text-embedding-3-large"
    # Azure Search
    settings.azure_search_endpoint = "https://mock.search.azure.com"
    settings.azure_search_api_key = "mock-key"
    settings.azure_search_index_kazanim = "test-kazanim"
    settings.azure_search_index_kitap = "test-kitap"
    settings.azure_search_index_images = "test-images"
    settings.azure_search_index_questions = "test-questions"
    # RAG Settings
    settings.rag_confidence_threshold = 0.5
    settings.rag_kazanim_top_k = 5
    settings.rag_textbook_top_k = 5
    settings.rag_hybrid_kazanim_weight = 0.6
    settings.rag_hybrid_question_weight = 0.4
    settings.rag_hybrid_synergy_bonus = 0.1
    # Retrieval Settings
    settings.retrieval_max_retries = 3
    settings.retrieval_min_description_length = 10
    settings.retrieval_max_description_length = 2500
    settings.retrieval_weak_signal_threshold = 0.5
    settings.retrieval_min_kazanimlar = 3
    # Reranker Settings
    settings.reranker_max_items = 10
    settings.reranker_truncate_length = 300
    settings.reranker_score_blend_ratio = 0.5
    # Response Settings
    settings.response_max_kazanimlar = 5
    settings.response_max_textbook_sections = 5
    settings.response_content_truncate = 800
    # Timeout Settings
    settings.timeout_analyze_input = 60.0
    settings.timeout_retrieve = 30.0
    settings.timeout_rerank = 30.0
    settings.timeout_synthesize = 45.0
    settings.timeout_generate_response = 60.0
    settings.timeout_gap_finder = 15.0
    # Token Settings
    settings.token_model = "cl100k_base"
    settings.token_max_context = 128000
    settings.token_reserve_output = 4096
    settings.token_warn_threshold = 0.8
    # Circuit Breaker Settings
    settings.circuit_breaker_failure_threshold = 5
    settings.circuit_breaker_recovery_timeout = 60.0
    settings.circuit_breaker_half_open_requests = 3
    # Retry Settings
    settings.retry_max_attempts = 3
    settings.retry_base_delay = 1.0
    settings.retry_max_delay = 30.0
    settings.retry_exponential_base = 2.0
    # LLM Temperature
    settings.llm_temperature_deterministic = 0.0
    settings.llm_temperature_creative = 0.3
    settings.llm_temperature_chat = 0.7
    # Database
    settings.database_url = f"sqlite:///{_test_db_path}"
    settings.debug = True
    return settings


# ================== Mock State Fixtures ==================

@pytest.fixture
def initial_state() -> Dict[str, Any]:
    """Basic initial state for graph testing."""
    return {
        "question_text": "DNA'nin yapısını açıklayınız",
        "question_image_base64": None,
        "user_grade": 9,
        "user_subject": "B",
        "is_exam_mode": False,
        "vision_result": None,
        "ai_estimated_grade": None,
        "detected_topics": [],
        "math_expressions": [],
        "question_type": None,
        "matched_kazanimlar": [],
        "related_chunks": [],
        "related_images": [],
        "response": None,
        "prerequisite_gaps": [],
        "interdisciplinary_synthesis": None,
        "retrieval_retry_count": 0,
        "error": None,
        "status": "processing",
        "analysis_id": "test-123",
        "user_id": None,
        "conversation_id": None,
        "tracked_kazanim_codes": [],
        "chat_history": [],
        "understanding_detection": None
    }


@pytest.fixture
def state_with_kazanimlar(initial_state) -> Dict[str, Any]:
    """State with matched kazanımlar."""
    return {
        **initial_state,
        "matched_kazanimlar": [
            {
                "kazanim_code": "B.9.1.2.1",
                "kazanim_description": "DNA'nın yapısını açıklar",
                "kazanim_title": "DNA Yapısı",
                "score": 0.85,
                "grade": 9,
                "subject": "B"
            },
            {
                "kazanim_code": "B.9.1.2.2",
                "kazanim_description": "DNA replikasyonunu açıklar",
                "kazanim_title": "DNA Replikasyonu",
                "score": 0.72,
                "grade": 9,
                "subject": "B"
            }
        ],
        "status": "processing"
    }


@pytest.fixture
def state_with_chunks(state_with_kazanimlar) -> Dict[str, Any]:
    """State with textbook chunks."""
    return {
        **state_with_kazanimlar,
        "related_chunks": [
            {
                "content": "DNA çift sarmal yapıda bir nükleik asittir...",
                "hierarchy_path": "Ünite 1 > Hücre > DNA",
                "page_range": "45-48",
                "textbook_name": "Biyoloji 9",
                "grade": 9
            }
        ]
    }


# ================== Mock Azure Services ==================

@pytest.fixture
def mock_azure_search_results():
    """Mock Azure Search results."""
    return [
        {
            "@search.score": 0.85,
            "kazanim_code": "B.9.1.2.1",
            "kazanim_description": "DNA'nın yapısını açıklar",
            "kazanim_title": "DNA Yapısı",
            "grade": 9,
            "subject": "B"
        },
        {
            "@search.score": 0.72,
            "kazanim_code": "B.9.1.2.2",
            "kazanim_description": "DNA replikasyonunu açıklar",
            "kazanim_title": "DNA Replikasyonu",
            "grade": 9,
            "subject": "B"
        }
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM structured output response."""
    from src.rag.output_models import AnalysisOutput, MatchedKazanim

    return AnalysisOutput(
        summary="DNA çift sarmal yapıda bir moleküldür. Adenin-Timin ve Guanin-Sitozin bazları arasında hidrojen bağları bulunur.",
        matched_kazanimlar=[
            MatchedKazanim(
                kazanim_code="B.9.1.2.1",
                kazanim_description="DNA'nın yapısını açıklar",
                match_score=0.85,
                match_reason="Soru DNA yapısını soruyor, bu kazanım tam olarak bunu kapsar"
            )
        ],
        solution_steps=[
            "DNA'nın çift sarmal yapısını tanımla",
            "Nükleotid yapısını açıkla (fosfat, şeker, baz)",
            "Baz eşleşmelerini belirt (A-T, G-C)"
        ],
        final_answer="DNA, çift sarmal yapıda bir nükleik asittir",
        confidence=0.9
    )


@pytest.fixture
def mock_reranker_output():
    """Mock reranker structured output."""
    from src.rag.reranker import RerankerOutput, RerankedItem

    return RerankerOutput(
        ranked_items=[
            RerankedItem(
                kazanim_code="B.9.1.2.1",
                relevance_score=0.95,
                reasoning="Soru doğrudan DNA yapısını soruyor"
            ),
            RerankedItem(
                kazanim_code="B.9.1.2.2",
                relevance_score=0.65,
                reasoning="İlişkili ama dolaylı bağlantı"
            )
        ]
    )


# ================== Mock Clients ==================

@pytest.fixture
def mock_search_client(mock_azure_search_results):
    """Mock Azure Search client."""
    client = MagicMock()
    client.search.return_value = iter(mock_azure_search_results)
    return client


@pytest.fixture
def mock_openai_client():
    """Mock Azure OpenAI client."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"summary": "Test response"}'))]
    ))
    return client


# ================== Patched Module Fixtures ==================

@pytest.fixture
def patched_settings(mock_settings):
    """Patch get_settings globally."""
    with patch('config.settings.get_settings', return_value=mock_settings):
        yield mock_settings


@pytest.fixture
def patched_search_client(mock_search_client):
    """Patch Azure Search client."""
    with patch('config.azure_config.get_search_client', return_value=mock_search_client):
        yield mock_search_client


# ================== Database Fixtures ==================

@pytest.fixture
def test_db_session():
    """Create a test database session."""
    from src.database.db import init_db, get_session

    # Initialize test database
    init_db()
    session = get_session()

    yield session

    # Cleanup
    session.close()


# ================== Resilience Fixtures ==================

@pytest.fixture
def reset_circuit_breakers():
    """Reset all circuit breakers before and after test."""
    from src.utils.resilience import reset_all_circuits

    reset_all_circuits()
    yield
    reset_all_circuits()


@pytest.fixture
def mock_circuit_breaker():
    """Mock circuit breaker for testing."""
    from src.utils.resilience import CircuitBreaker, CircuitBreakerConfig

    config = CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=1.0,
        half_open_requests=1
    )
    return CircuitBreaker("test_circuit", config)


# ================== Token Manager Fixtures ==================

@pytest.fixture
def token_manager():
    """Create a token manager instance."""
    from src.utils.token_manager import TokenManager
    return TokenManager()


# ================== Utility Functions ==================

def create_mock_kazanim(
    code: str = "B.9.1.2.1",
    description: str = "Test kazanım",
    score: float = 0.85,
    grade: int = 9
) -> Dict[str, Any]:
    """Create a mock kazanım dict for testing."""
    return {
        "kazanim_code": code,
        "kazanim_description": description,
        "kazanim_title": description[:50],
        "score": score,
        "grade": grade,
        "subject": code[0] if code else "B"
    }


def create_mock_chunk(
    content: str = "Test content",
    page: str = "1-2",
    grade: int = 9
) -> Dict[str, Any]:
    """Create a mock textbook chunk for testing."""
    return {
        "content": content,
        "hierarchy_path": "Ünite > Konu > Alt Konu",
        "page_range": page,
        "textbook_name": "Test Kitabı",
        "grade": grade
    }
