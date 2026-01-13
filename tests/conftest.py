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
    """
    Create a test database session with isolated SQLite.
    Uses a named in-memory database with shared cache for connection sharing.
    This fixture ensures all tables are created in a fresh database.
    """
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from src.database.models import Base

    # Use StaticPool to ensure the same connection is reused
    # This is necessary because SQLite in-memory databases are connection-specific
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session bound to this engine
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


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


# ================== FastAPI Test Client Fixtures ==================

@pytest.fixture
def test_client(test_db_session, patched_settings):
    """
    FastAPI TestClient with mocked dependencies.
    Use for synchronous API endpoint testing.

    NOTE: This fixture provides a basic test client with database override.
    For authenticated tests, use mock_firebase_verify fixture alongside.
    """
    from fastapi.testclient import TestClient
    from api.main import app
    from src.database.db import get_db

    # Override database dependency to use test session
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Don't close - let fixture handle it

    app.dependency_overrides[get_db] = override_get_db

    # Disable lifespan to avoid Firebase/Graph initialization during tests
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(test_db_session, mock_firebase_token, patched_settings):
    """
    FastAPI TestClient with authentication pre-configured.
    Returns (client, user) tuple for authenticated endpoint testing.
    """
    from fastapi.testclient import TestClient
    from api.main import app
    from src.database.db import get_db
    from api.auth.deps import get_current_user, get_current_active_user
    from src.database.models import User, Subscription

    # Check if user already exists (idempotency)
    existing = test_db_session.query(User).filter(
        User.firebase_uid == mock_firebase_token["uid"]
    ).first()

    if existing:
        test_user = existing
    else:
        # Create user in the test session
        test_user = User(
            firebase_uid=mock_firebase_token["uid"],
            email=mock_firebase_token["email"],
            full_name=mock_firebase_token["name"],
            avatar_url=mock_firebase_token.get("picture"),
            role="student",
            grade=10,
            is_active=True,
            is_verified=True,
            profile_complete=True
        )
        test_db_session.add(test_user)
        test_db_session.flush()

        # Create subscription
        subscription = Subscription(
            user_id=test_user.id,
            plan="free",
            questions_limit=10,
            images_limit=0
        )
        test_db_session.add(subscription)
        test_db_session.commit()
        test_db_session.refresh(test_user)

    # Override database - MUST use a generator that yields the SAME session
    def override_get_db():
        yield test_db_session

    # Override auth to return test user directly
    async def override_get_current_user():
        return test_user

    async def override_get_current_active_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    client = TestClient(app, raise_server_exceptions=False)
    yield client, test_user, test_db_session

    app.dependency_overrides.clear()


@pytest.fixture
async def async_test_client(test_db_session, patched_settings):
    """
    Async HTTP client for testing streaming endpoints.
    Use for async API endpoint testing.
    """
    from httpx import AsyncClient, ASGITransport
    from api.main import app
    from src.database.db import get_db

    # Override database dependency
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ================== Firebase Mock Fixtures ==================

@pytest.fixture
def mock_firebase_token():
    """Mock decoded Firebase ID token."""
    return {
        "uid": "test-firebase-uid-123",
        "email": "test@example.com",
        "email_verified": True,
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg",
        "firebase": {
            "sign_in_provider": "password"
        }
    }


@pytest.fixture
def mock_firebase_verify(mock_firebase_token):
    """
    Patch Firebase token verification to return mock token.
    Use this fixture to bypass Firebase authentication in tests.
    Patches in both locations: where defined and where imported.
    """
    with patch('api.auth.firebase.verify_firebase_token', return_value=mock_firebase_token):
        with patch('api.auth.deps.verify_firebase_token', return_value=mock_firebase_token):
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                yield mock_firebase_token


@pytest.fixture
def mock_firebase_verify_expired():
    """Mock Firebase verification that raises ExpiredIdTokenError."""
    from firebase_admin.auth import ExpiredIdTokenError

    with patch('api.auth.firebase.verify_firebase_token', side_effect=ExpiredIdTokenError("Token expired", None)):
        with patch('api.auth.deps.verify_firebase_token', side_effect=ExpiredIdTokenError("Token expired", None)):
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                yield


@pytest.fixture
def mock_firebase_verify_invalid():
    """Mock Firebase verification that raises InvalidIdTokenError."""
    from firebase_admin.auth import InvalidIdTokenError

    with patch('api.auth.firebase.verify_firebase_token', side_effect=InvalidIdTokenError("Invalid token", None)):
        with patch('api.auth.deps.verify_firebase_token', side_effect=InvalidIdTokenError("Invalid token", None)):
            with patch('api.auth.firebase.get_firebase_app', return_value=MagicMock()):
                yield


# ================== Test User Fixtures ==================

@pytest.fixture
def test_user(test_db_session, mock_firebase_token):
    """
    Create a test user in the database with subscription.
    Returns a fully set up user for authenticated endpoint testing.
    """
    from src.database.models import User, Subscription

    # Check if user already exists (idempotency)
    existing = test_db_session.query(User).filter(
        User.firebase_uid == mock_firebase_token["uid"]
    ).first()

    if existing:
        return existing

    user = User(
        firebase_uid=mock_firebase_token["uid"],
        email=mock_firebase_token["email"],
        full_name=mock_firebase_token["name"],
        avatar_url=mock_firebase_token.get("picture"),
        role="student",
        grade=10,
        is_active=True,
        is_verified=True,
        profile_complete=True
    )
    test_db_session.add(user)
    test_db_session.flush()

    # Create subscription
    subscription = Subscription(
        user_id=user.id,
        plan="free",
        questions_limit=10,
        images_limit=0
    )
    test_db_session.add(subscription)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture
def test_user_incomplete_profile(test_db_session):
    """Create a test user with incomplete profile (no grade/role set)."""
    from src.database.models import User, Subscription

    user = User(
        firebase_uid="incomplete-profile-uid",
        email="incomplete@example.com",
        full_name="Incomplete User",
        role="student",
        grade=None,
        is_active=True,
        is_verified=False,
        profile_complete=False
    )
    test_db_session.add(user)
    test_db_session.flush()

    subscription = Subscription(
        user_id=user.id,
        plan="free",
        questions_limit=10,
        images_limit=0
    )
    test_db_session.add(subscription)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


@pytest.fixture
def test_user_inactive(test_db_session):
    """Create an inactive test user."""
    from src.database.models import User, Subscription

    user = User(
        firebase_uid="inactive-user-uid",
        email="inactive@example.com",
        full_name="Inactive User",
        role="student",
        grade=10,
        is_active=False,  # Inactive!
        is_verified=True,
        profile_complete=True
    )
    test_db_session.add(user)
    test_db_session.flush()

    subscription = Subscription(
        user_id=user.id,
        plan="free",
        questions_limit=10,
        images_limit=0
    )
    test_db_session.add(subscription)
    test_db_session.commit()
    test_db_session.refresh(user)

    return user


# ================== Auth Headers Fixture ==================

@pytest.fixture
def auth_headers():
    """Authorization headers for authenticated requests."""
    return {"Authorization": "Bearer mock-firebase-token"}


# ================== Rate Limiter Mock ==================

@pytest.fixture(autouse=False)
def disable_rate_limiter():
    """
    Disable rate limiting in tests.
    Use this fixture when testing endpoints with rate limits.
    Note: Not autouse - enable explicitly when needed.
    """
    with patch('api.limiter.limiter.limit', return_value=lambda f: f):
        yield


# ================== RAG Graph Mock Fixtures ==================

@pytest.fixture
def mock_graph_analyze():
    """Mock the RAG graph analyze method."""
    mock_result = {
        "analysis_id": "test-analysis-123",
        "status": "success",
        "question_text": "DNA'nin yapısını açıklayınız",
        "matched_kazanimlar": [
            {
                "kazanim_code": "B.9.1.2.1",
                "kazanim_description": "DNA'nın yapısını açıklar",
                "score": 0.85,
                "grade": 9,
                "subject": "B"
            }
        ],
        "related_chunks": [
            {
                "content": "DNA çift sarmal yapıda...",
                "hierarchy_path": "Ünite 1 > Hücre > DNA",
                "page_range": "45-48",
                "textbook_name": "Biyoloji 9",
                "grade": 9
            }
        ],
        "prerequisite_gaps": [],
        "response": {
            "summary": "DNA çift sarmal yapıda bir moleküldür.",
            "confidence": 0.9,
            "solution_steps": ["Adım 1", "Adım 2"]
        }
    }

    with patch('api.routes.analysis.get_graph') as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.analyze = AsyncMock(return_value=mock_result)
        mock_get_graph.return_value = mock_graph
        yield mock_result


# ================== Conversation Fixtures ==================

@pytest.fixture
def test_conversation(test_db_session, test_user):
    """Create a test conversation for the test user."""
    from src.database.models import Conversation, Message
    import uuid

    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        title="Test Conversation",
        subject="Biyoloji",
        grade=10
    )
    test_db_session.add(conversation)
    test_db_session.commit()
    test_db_session.refresh(conversation)

    return conversation


@pytest.fixture
def test_conversation_with_messages(test_db_session, test_conversation):
    """Create a test conversation with sample messages."""
    from src.database.models import Message

    # Add user message
    user_msg = Message(
        conversation_id=test_conversation.id,
        role="user",
        content="DNA'nin yapısı nedir?"
    )
    test_db_session.add(user_msg)

    # Add assistant message
    assistant_msg = Message(
        conversation_id=test_conversation.id,
        role="assistant",
        content="DNA çift sarmal yapıda bir moleküldür.",
        analysis_id="test-analysis-123"
    )
    test_db_session.add(assistant_msg)

    test_db_session.commit()
    test_db_session.refresh(test_conversation)

    return test_conversation


# ================== Progress Fixtures ==================

@pytest.fixture
def test_kazanim_progress(test_db_session, test_user):
    """Create test kazanim progress entries for the test user."""
    from src.database.models import UserKazanimProgress

    progress_entries = [
        UserKazanimProgress(
            user_id=test_user.id,
            kazanim_code="B.9.1.2.1",
            status="tracked",
            initial_confidence_score=0.85
        ),
        UserKazanimProgress(
            user_id=test_user.id,
            kazanim_code="B.9.1.2.2",
            status="in_progress",
            initial_confidence_score=0.72
        ),
        UserKazanimProgress(
            user_id=test_user.id,
            kazanim_code="B.9.1.3.1",
            status="understood",
            initial_confidence_score=0.90,
            understanding_confidence=0.95
        )
    ]

    for entry in progress_entries:
        test_db_session.add(entry)

    test_db_session.commit()

    return progress_entries
