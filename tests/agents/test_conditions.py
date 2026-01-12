"""
Tests for LangGraph edge conditions.
Tests src/agents/conditions.py
"""
import pytest
from unittest.mock import patch, MagicMock


class TestCheckAnalysisSuccess:
    """Tests for check_analysis_success condition."""

    def test_route_to_continue_for_academic(self, patched_settings):
        """Test routing academic questions to RAG pipeline."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "DNA'nin yapısını açıklayın",
            "message_type": "academic_question",
            "error": None
        }

        result = check_analysis_success(state)
        assert result == "continue"

    def test_route_to_chat_for_greeting(self, patched_settings):
        """Test routing greetings to chat handler."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "Merhaba",
            "message_type": "greeting",
            "error": None
        }

        result = check_analysis_success(state)
        assert result == "chat"

    def test_route_to_chat_for_general_chat(self, patched_settings):
        """Test routing general chat to chat handler."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "Nasılsın?",
            "message_type": "general_chat",
            "error": None
        }

        result = check_analysis_success(state)
        assert result == "chat"

    def test_route_to_error_on_error(self, patched_settings):
        """Test routing to error handler when error exists."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "Test",
            "message_type": "academic_question",
            "error": "Some error occurred"
        }

        result = check_analysis_success(state)
        assert result == "error"

    def test_route_to_error_no_question(self, patched_settings):
        """Test routing to error when no question text."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "",
            "message_type": "academic_question",
            "error": None
        }

        result = check_analysis_success(state)
        assert result == "error"

    def test_route_continue_for_unclear_message(self, patched_settings):
        """Test that unclear messages proceed with RAG."""
        from src.agents.conditions import check_analysis_success

        state = {
            "question_text": "Some text",
            "message_type": "unclear",
            "error": None
        }

        result = check_analysis_success(state)
        assert result == "continue"


class TestCheckRetrievalSuccess:
    """Tests for check_retrieval_success condition."""

    def test_continue_with_results(self, patched_settings):
        """Test continuing when results are found."""
        from src.agents.conditions import check_retrieval_success

        state = {
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "status": "processing",
            "retrieval_retry_count": 0
        }

        result = check_retrieval_success(state)
        assert result == "continue"

    def test_retry_on_needs_retry(self, patched_settings):
        """Test retry when status is needs_retry."""
        from src.agents.conditions import check_retrieval_success

        state = {
            "matched_kazanimlar": [],
            "status": "needs_retry",
            "retrieval_retry_count": 1
        }

        result = check_retrieval_success(state)
        assert result == "retry"

    def test_error_on_max_retries(self, patched_settings):
        """Test error when max retries exceeded."""
        from src.agents.conditions import check_retrieval_success

        state = {
            "matched_kazanimlar": [],
            "status": "needs_retry",
            "retrieval_retry_count": 3  # Max retries
        }

        result = check_retrieval_success(state)
        assert result == "error"

    def test_continue_with_results_despite_needs_retry(self, patched_settings):
        """Test continuing when results exist even if status suggests retry."""
        from src.agents.conditions import check_retrieval_success

        state = {
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "status": "processing",  # Not needs_retry
            "retrieval_retry_count": 0
        }

        result = check_retrieval_success(state)
        assert result == "continue"

    def test_retry_on_no_results_first_attempt(self, patched_settings):
        """Test retry on first attempt with no results."""
        from src.agents.conditions import check_retrieval_success

        state = {
            "matched_kazanimlar": [],
            "status": "processing",
            "retrieval_retry_count": 0
        }

        result = check_retrieval_success(state)
        assert result == "retry"


class TestCheckHasResults:
    """Tests for check_has_results condition."""

    def test_has_results_with_kazanimlar(self, patched_settings):
        """Test has_results when kazanimlar found."""
        from src.agents.conditions import check_has_results

        state = {
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "related_chunks": []
        }

        result = check_has_results(state)
        assert result == "has_results"

    def test_has_results_with_chunks(self, patched_settings):
        """Test has_results when chunks found."""
        from src.agents.conditions import check_has_results

        state = {
            "matched_kazanimlar": [],
            "related_chunks": [{"content": "Some chunk"}]
        }

        result = check_has_results(state)
        assert result == "has_results"

    def test_has_results_with_both(self, patched_settings):
        """Test has_results when both kazanimlar and chunks found."""
        from src.agents.conditions import check_has_results

        state = {
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "related_chunks": [{"content": "Some chunk"}]
        }

        result = check_has_results(state)
        assert result == "has_results"

    def test_no_results(self, patched_settings):
        """Test no_results when nothing found."""
        from src.agents.conditions import check_has_results

        state = {
            "matched_kazanimlar": [],
            "related_chunks": []
        }

        result = check_has_results(state)
        assert result == "no_results"


class TestShouldIncludeImages:
    """Tests for should_include_images condition."""

    def test_with_images(self, patched_settings):
        """Test with_images when images exist."""
        from src.agents.conditions import should_include_images

        state = {
            "related_images": [{"id": "img1", "caption": "Figure 1"}]
        }

        result = should_include_images(state)
        assert result == "with_images"

    def test_text_only(self, patched_settings):
        """Test text_only when no images."""
        from src.agents.conditions import should_include_images

        state = {
            "related_images": []
        }

        result = should_include_images(state)
        assert result == "text_only"

    def test_text_only_missing_key(self, patched_settings):
        """Test text_only when related_images key is missing."""
        from src.agents.conditions import should_include_images

        state = {}

        result = should_include_images(state)
        assert result == "text_only"


class TestGetFinalStatus:
    """Tests for get_final_status condition."""

    def test_success_with_results_and_response(self, patched_settings):
        """Test success when both kazanimlar and response exist."""
        from src.agents.conditions import get_final_status

        state = {
            "error": None,
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "response": {"summary": "DNA is..."}
        }

        result = get_final_status(state)
        assert result == "success"

    def test_partial_with_response_only(self, patched_settings):
        """Test partial when only response exists (no kazanimlar)."""
        from src.agents.conditions import get_final_status

        state = {
            "error": None,
            "matched_kazanimlar": [],
            "response": {"summary": "I can help with that..."}
        }

        result = get_final_status(state)
        assert result == "partial"

    def test_failed_on_error(self, patched_settings):
        """Test failed when error exists."""
        from src.agents.conditions import get_final_status

        state = {
            "error": "Something went wrong",
            "matched_kazanimlar": [{"kazanim_code": "B.9.1.2.1"}],
            "response": {"summary": "DNA is..."}
        }

        result = get_final_status(state)
        assert result == "failed"

    def test_failed_no_response(self, patched_settings):
        """Test failed when no response generated."""
        from src.agents.conditions import get_final_status

        state = {
            "error": None,
            "matched_kazanimlar": [],
            "response": None
        }

        result = get_final_status(state)
        assert result == "failed"


class TestConditionRegistry:
    """Tests for condition registry."""

    def test_all_conditions_registered(self, patched_settings):
        """Test that all conditions are registered."""
        from src.agents.conditions import CONDITION_REGISTRY

        expected_conditions = [
            "check_analysis_success",
            "check_retrieval_success",
            "check_has_results",
            "should_include_images",
            "get_final_status"
        ]

        for condition in expected_conditions:
            assert condition in CONDITION_REGISTRY

    def test_registry_functions_callable(self, patched_settings):
        """Test that all registered functions are callable."""
        from src.agents.conditions import CONDITION_REGISTRY

        for name, func in CONDITION_REGISTRY.items():
            assert callable(func), f"{name} is not callable"
