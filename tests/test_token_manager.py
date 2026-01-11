"""
MEB RAG Sistemi - Token Manager Tests
Tests for token counting and context management
"""
import pytest
from unittest.mock import patch, MagicMock

from src.utils.token_manager import (
    TokenManager,
    TokenCheckResult,
    get_token_manager
)


class TestTokenManager:
    """Tests for TokenManager class."""

    @pytest.fixture
    def manager(self, patched_settings):
        """Create a token manager instance with mocked settings."""
        return TokenManager()

    @pytest.mark.unit
    def test_count_tokens_empty(self, manager):
        """Empty string should have 0 tokens."""
        assert manager.count_tokens("") == 0

    @pytest.mark.unit
    def test_count_tokens_simple(self, manager):
        """Simple text should count correctly."""
        # "hello world" is typically 2 tokens
        count = manager.count_tokens("hello world")
        assert count > 0
        assert count < 10  # Sanity check

    @pytest.mark.unit
    def test_count_tokens_turkish(self, manager):
        """Turkish text should count correctly."""
        count = manager.count_tokens("DNA'nın yapısını açıklayınız")
        assert count > 0
        # Turkish with special chars usually has more tokens

    @pytest.mark.unit
    def test_count_messages(self, manager):
        """Should count tokens in chat messages with overhead."""
        messages = [
            {"role": "system", "content": "Sen bir asistansın."},
            {"role": "user", "content": "Merhaba!"}
        ]
        count = manager.count_messages(messages)
        # Should include message overhead
        assert count > manager.count_tokens("Sen bir asistansın.Merhaba!")

    @pytest.mark.unit
    def test_truncate_to_tokens_no_truncation(self, manager):
        """Short text should not be truncated."""
        text = "short text"
        result = manager.truncate_to_tokens(text, max_tokens=100)
        assert result == text
        assert "..." not in result

    @pytest.mark.unit
    def test_truncate_to_tokens_with_truncation(self, manager):
        """Long text should be truncated with ellipsis."""
        text = "This is a very long text that should be truncated " * 10
        result = manager.truncate_to_tokens(text, max_tokens=10)
        assert len(result) < len(text)
        assert result.endswith("...")

    @pytest.mark.unit
    def test_truncate_to_chars_approx_no_truncation(self, manager):
        """Short text should not be truncated."""
        text = "short"
        result = manager.truncate_to_chars_approx(text, max_chars=100)
        assert result == text

    @pytest.mark.unit
    def test_truncate_to_chars_approx_with_truncation(self, manager):
        """Long text should be truncated."""
        text = "a" * 500
        result = manager.truncate_to_chars_approx(text, max_chars=100)
        assert len(result) == 103  # 100 chars + "..."

    @pytest.mark.unit
    def test_check_context_fit_fits(self, manager):
        """Should return fits=True when content fits."""
        messages = [{"role": "user", "content": "Hello"}]
        result = manager.check_context_fit(messages, "short content")

        assert result.fits is True
        assert result.utilization < 1.0
        assert result.warning_message is None

    @pytest.mark.unit
    def test_check_context_fit_warning(self, manager):
        """Should return warning when near threshold."""
        # Create large content to trigger warning
        large_content = "word " * 20000  # ~20000 tokens

        messages = [{"role": "user", "content": large_content}]
        result = manager.check_context_fit(messages, large_content)

        if result.over_threshold:
            assert result.warning_message is not None

    @pytest.mark.unit
    def test_prepare_kazanimlar_context_empty(self, manager):
        """Empty list should return empty."""
        kazanimlar, tokens = manager.prepare_kazanimlar_context([])
        assert kazanimlar == []
        assert tokens == 0

    @pytest.mark.unit
    def test_prepare_kazanimlar_context_truncates(self, manager):
        """Should truncate kazanimlar to fit token budget."""
        kazanimlar = [
            {
                "kazanim_code": f"B.9.1.{i}",
                "kazanim_description": "X" * 500  # Long description
            }
            for i in range(10)
        ]

        result, tokens = manager.prepare_kazanimlar_context(kazanimlar, max_tokens=500)

        # Should have fewer items due to truncation
        assert len(result) <= len(kazanimlar)
        assert tokens <= 500

    @pytest.mark.unit
    def test_prepare_textbook_context_empty(self, manager):
        """Empty list should return empty."""
        chunks, tokens = manager.prepare_textbook_context([])
        assert chunks == []
        assert tokens == 0

    @pytest.mark.unit
    def test_prepare_textbook_context_truncates(self, manager):
        """Should truncate chunks to fit token budget."""
        chunks = [
            {"content": "X" * 1000}  # Long content
            for _ in range(10)
        ]

        result, tokens = manager.prepare_textbook_context(chunks, max_tokens=500)

        assert len(result) <= len(chunks)
        assert tokens <= 500

    @pytest.mark.unit
    def test_estimate_response_tokens(self, manager):
        """Should estimate reasonable token counts."""
        estimate = manager.estimate_response_tokens(
            kazanimlar_count=3,
            chunks_count=2
        )

        # Base + (3 * 150) + (2 * 50) = 350 + 450 + 100 = 900
        assert estimate > 0
        assert estimate < 2000  # Sanity check


class TestTokenCheckResult:
    """Tests for TokenCheckResult dataclass."""

    @pytest.mark.unit
    def test_result_creation(self):
        """Should create result with all fields."""
        result = TokenCheckResult(
            fits=True,
            total_tokens=100,
            available_tokens=1000,
            utilization=0.1,
            over_threshold=False,
            warning_message=None
        )

        assert result.fits is True
        assert result.total_tokens == 100
        assert result.utilization == 0.1

    @pytest.mark.unit
    def test_result_with_warning(self):
        """Should include warning message."""
        result = TokenCheckResult(
            fits=True,
            total_tokens=8500,
            available_tokens=10000,
            utilization=0.85,
            over_threshold=True,
            warning_message="Token utilization high"
        )

        assert result.over_threshold is True
        assert result.warning_message is not None


class TestGetTokenManager:
    """Tests for get_token_manager singleton."""

    @pytest.mark.unit
    def test_returns_same_instance(self, patched_settings):
        """Should return same instance (singleton)."""
        # Reset singleton
        import src.utils.token_manager as tm
        tm._token_manager = None

        manager1 = get_token_manager()
        manager2 = get_token_manager()

        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
