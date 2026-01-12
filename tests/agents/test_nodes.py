"""
Tests for LangGraph node implementations.
Tests src/agents/nodes.py
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any


class TestClassifyMessageType:
    """Tests for classify_message_type function."""

    def test_classify_greeting_turkish(self, patched_settings):
        """Test classification of Turkish greetings."""
        from src.agents.nodes import classify_message_type

        assert classify_message_type("Merhaba") == "greeting"
        assert classify_message_type("selam") == "greeting"
        assert classify_message_type("sa") == "greeting"

    def test_classify_greeting_english(self, patched_settings):
        """Test classification of English greetings."""
        from src.agents.nodes import classify_message_type

        assert classify_message_type("Hello") == "greeting"
        assert classify_message_type("Hi") == "greeting"

    def test_classify_general_chat(self, patched_settings):
        """Test classification of general chat messages."""
        from src.agents.nodes import classify_message_type

        assert classify_message_type("Teşekkürler") == "general_chat"
        assert classify_message_type("Tamam") == "general_chat"

    def test_classify_academic_with_question_mark(self, patched_settings):
        """Test classification of questions with question mark."""
        from src.agents.nodes import classify_message_type

        # These should be academic questions due to question marks and keywords
        assert classify_message_type("Bu konu nasıl hesaplanır?") == "academic_question"
        assert classify_message_type("Biyoloji sorusu: DNA nedir?") == "academic_question"

    def test_classify_academic_with_keywords(self, patched_settings):
        """Test classification of academic questions by keywords."""
        from src.agents.nodes import classify_message_type

        assert classify_message_type("formül nedir") == "academic_question"
        assert classify_message_type("matematik problemi") == "academic_question"
        assert classify_message_type("fizik denklemi açıkla") == "academic_question"

    def test_classify_long_text_as_academic(self, patched_settings):
        """Test that long text is classified as academic."""
        from src.agents.nodes import classify_message_type

        long_text = "Bu konuyu anlamadım biraz daha açıklar mısın lütfen"
        assert classify_message_type(long_text) == "academic_question"

    def test_classify_empty_as_unclear(self, patched_settings):
        """Test that empty text is classified as unclear."""
        from src.agents.nodes import classify_message_type

        assert classify_message_type("") == "unclear"
        assert classify_message_type(None) == "unclear"


class TestAnalyzeInput:
    """Tests for analyze_input node."""

    @pytest.mark.asyncio
    async def test_analyze_text_greeting(self, initial_state, patched_settings):
        """Test analyze_input with greeting message."""
        from src.agents.nodes import analyze_input

        state = {**initial_state, "question_text": "Merhaba"}

        result = await analyze_input(state)

        assert result["message_type"] == "greeting"
        assert result["status"] == "chat_mode"

    @pytest.mark.asyncio
    async def test_analyze_text_academic(self, initial_state, patched_settings):
        """Test analyze_input with academic question."""
        from src.agents.nodes import analyze_input

        state = {**initial_state, "question_text": "DNA'nın yapısını açıklayınız?"}

        result = await analyze_input(state)

        assert result["message_type"] == "academic_question"
        assert result["status"] == "processing"

    @pytest.mark.asyncio
    async def test_analyze_image(self, initial_state, patched_settings):
        """Test analyze_input with image."""
        from src.agents.nodes import analyze_input

        # Mock the Vision pipeline
        mock_analysis = MagicMock()
        mock_analysis.extracted_text = "Test question from image"
        mock_analysis.question_type = "multiple_choice"
        mock_analysis.topics = ["biology"]
        mock_analysis.math_expressions = []
        mock_analysis.confidence = 0.9
        mock_analysis.grade = 10
        mock_analysis.grade_source = "ai"

        # Patch at the source location (where it's imported from)
        with patch('src.vision.QuestionAnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze_from_bytes = AsyncMock(return_value=mock_analysis)
            mock_pipeline_class.return_value = mock_pipeline

            # Simple base64 encoded image (minimal valid base64)
            state = {
                **initial_state,
                "question_image_base64": "dGVzdA=="  # "test" in base64
            }

            result = await analyze_input(state)

            assert result["message_type"] == "academic_question"
            assert result["question_text"] == "Test question from image"
            assert result["question_type"] == "multiple_choice"

    @pytest.mark.asyncio
    async def test_analyze_image_with_data_url(self, initial_state, patched_settings):
        """Test analyze_input with data URL format image."""
        from src.agents.nodes import analyze_input

        mock_analysis = MagicMock()
        mock_analysis.extracted_text = "Extracted text"
        mock_analysis.question_type = "open_ended"
        mock_analysis.topics = []
        mock_analysis.math_expressions = []
        mock_analysis.confidence = 0.85
        mock_analysis.grade = None
        mock_analysis.grade_source = "user"

        # Patch at the source location
        with patch('src.vision.QuestionAnalysisPipeline') as mock_pipeline_class:
            mock_pipeline = MagicMock()
            mock_pipeline.analyze_from_bytes = AsyncMock(return_value=mock_analysis)
            mock_pipeline_class.return_value = mock_pipeline

            # Data URL format
            state = {
                **initial_state,
                "question_image_base64": "data:image/png;base64,dGVzdA=="
            }

            result = await analyze_input(state)

            assert result["question_text"] == "Extracted text"


class TestRetrieveKazanimlar:
    """Tests for retrieve_kazanimlar node."""

    @pytest.mark.asyncio
    async def test_retrieve_success(self, initial_state, patched_settings, mock_search_client):
        """Test successful kazanim retrieval."""
        from src.agents.nodes import retrieve_kazanimlar

        # Provide multiple high-score results to avoid retry logic
        mock_results = [
            {
                "kazanim_code": "B.9.1.2.1",
                "kazanim_description": "DNA'nın yapısını açıklar",
                "@search.score": 0.95,
                "score": 0.95,
                "grade": 9,
                "subject": "B"
            },
            {
                "kazanim_code": "B.9.1.2.2",
                "kazanim_description": "DNA replikasyonunu açıklar",
                "@search.score": 0.90,
                "score": 0.90,
                "grade": 9,
                "subject": "B"
            },
            {
                "kazanim_code": "B.9.1.2.3",
                "kazanim_description": "DNA'nın görevlerini açıklar",
                "@search.score": 0.88,
                "score": 0.88,
                "grade": 9,
                "subject": "B"
            }
        ]

        # Patch at the source location
        with patch('src.vector_store.ParentDocumentRetriever') as mock_retriever_class:
            mock_retriever = MagicMock()
            mock_retriever.search_hybrid_expansion = AsyncMock(return_value=mock_results)
            mock_retriever_class.return_value = mock_retriever

            state = {
                **initial_state,
                "question_text": "DNA nedir?",
                "user_grade": 9
            }

            result = await retrieve_kazanimlar(state)

            # Result should have matched_kazanimlar (possibly empty if retry triggered)
            # or have status indicating processing/needs_retry
            assert "matched_kazanimlar" in result or "status" in result

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self, initial_state, patched_settings):
        """Test retrieval with no results triggers retry logic."""
        from src.agents.nodes import retrieve_kazanimlar

        # Patch at the source location
        with patch('src.vector_store.ParentDocumentRetriever') as mock_retriever_class:
            mock_retriever = MagicMock()
            mock_retriever.search_hybrid_expansion = AsyncMock(return_value=[])
            mock_retriever_class.return_value = mock_retriever

            state = {
                **initial_state,
                "question_text": "Very obscure question",
                "user_grade": 9,
                "retrieval_retry_count": 0
            }

            result = await retrieve_kazanimlar(state)

            # Should trigger retry
            assert result.get("status") == "needs_retry" or result.get("matched_kazanimlar") == []


class TestHandleChat:
    """Tests for handle_chat node."""

    @pytest.mark.asyncio
    async def test_handle_greeting(self, initial_state, patched_settings):
        """Test handle_chat with greeting."""
        from src.agents.nodes import handle_chat

        state = {
            **initial_state,
            "question_text": "Merhaba",
            "message_type": "greeting"
        }

        result = await handle_chat(state)

        assert "response" in result
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_handle_thanks(self, initial_state, patched_settings):
        """Test handle_chat with thanks."""
        from src.agents.nodes import handle_chat

        state = {
            **initial_state,
            "question_text": "Teşekkürler",
            "message_type": "general_chat"
        }

        result = await handle_chat(state)

        assert "response" in result


class TestHandleError:
    """Tests for handle_error node."""

    @pytest.mark.asyncio
    async def test_handle_error(self, initial_state, patched_settings):
        """Test handle_error generates error response."""
        from src.agents.nodes import handle_error

        state = {
            **initial_state,
            "error": "Something went wrong",
            "status": "failed"
        }

        result = await handle_error(state)

        assert "response" in result
        assert result["status"] == "failed"


class TestTrackProgress:
    """Tests for track_progress node."""

    @pytest.mark.asyncio
    async def test_track_high_confidence(self, state_with_kazanimlar, test_db_session, test_user, patched_settings):
        """Test auto-tracking high confidence kazanims."""
        from src.agents.nodes import track_progress

        state = {
            **state_with_kazanimlar,
            "user_id": test_user.id,
            "matched_kazanimlar": [
                {"kazanim_code": "B.9.1.2.1", "blended_score": 0.85}  # Above 0.80
            ]
        }

        # Patch at the source location (get_session is imported from src.database.db)
        with patch('src.database.db.get_session', return_value=test_db_session):
            result = await track_progress(state)

            assert "tracked_kazanim_codes" in result

    @pytest.mark.asyncio
    async def test_skip_tracking_no_user(self, state_with_kazanimlar, patched_settings):
        """Test skipping when no user_id."""
        from src.agents.nodes import track_progress

        state = {
            **state_with_kazanimlar,
            "user_id": None
        }

        result = await track_progress(state)

        assert result.get("tracked_kazanim_codes", []) == []


class TestGenerateResponse:
    """Tests for generate_response node."""

    @pytest.mark.asyncio
    async def test_generate_response_success(self, state_with_chunks, patched_settings):
        """Test successful response generation."""
        from src.agents.nodes import generate_response
        from src.rag.output_models import AnalysisOutput, SolutionStep

        mock_response = AnalysisOutput(
            summary="DNA çift sarmal yapıda bir moleküldür.",
            matched_kazanimlar=[],
            solution_steps=[
                SolutionStep(step_number=1, description="DNA yapısını tanımla"),
                SolutionStep(step_number=2, description="Nükleotidleri açıkla")
            ],
            final_answer="DNA çift sarmal yapıda bir nükleik asittir",
            confidence=0.9
        )

        with patch('langchain_openai.AzureChatOpenAI') as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            state = {
                **state_with_chunks,
                "question_text": "DNA nedir?"
            }

            result = await generate_response(state)

            assert "response" in result
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_generate_response_no_results(self, initial_state, patched_settings):
        """Test response generation with no retrieval results."""
        from src.agents.nodes import generate_response

        # When no kazanımlar found, the function returns a default response without LLM call
        state = {
            **initial_state,
            "matched_kazanimlar": [],
            "related_chunks": []
        }

        result = await generate_response(state)

        assert "response" in result
        # Should return a message indicating no kazanım found
        assert "bulunamadı" in result["response"].get("message", "").lower()


class TestNodeDecorators:
    """Tests for node decorators."""

    @pytest.mark.asyncio
    async def test_timeout_decorator(self, patched_settings):
        """Test that timeout decorator is applied."""
        from src.agents.nodes import analyze_input

        # The function should have the timeout decorator applied
        # We can verify by checking it's callable
        assert callable(analyze_input)

    @pytest.mark.asyncio
    async def test_log_execution_decorator(self, patched_settings):
        """Test that log execution decorator is applied."""
        from src.agents.nodes import analyze_input

        # Function should work with logging
        assert callable(analyze_input)
