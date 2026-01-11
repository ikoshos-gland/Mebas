"""
MEB RAG Sistemi - Token Manager
Token counting and context window management for LLM calls
"""
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import tiktoken

from config.settings import get_settings


@dataclass
class TokenCheckResult:
    """Result of a token check operation."""
    fits: bool
    total_tokens: int
    available_tokens: int
    utilization: float
    over_threshold: bool
    warning_message: Optional[str] = None


class TokenManager:
    """
    Manages token counting and content truncation for LLM calls.

    Uses tiktoken for accurate token counting with the cl100k_base encoding
    (used by GPT-4, GPT-4o, and text-embedding-3 models).

    Key features:
    - Count tokens in text and chat messages
    - Truncate content to fit within token limits
    - Check if content fits in context window
    - Prepare context with token-aware truncation
    """

    # Overhead tokens per message in chat format
    MESSAGE_OVERHEAD = 4  # <|im_start|>role\ncontent<|im_end|>
    REPLY_PRIMING = 2     # Tokens for reply priming

    def __init__(self):
        """Initialize token manager with settings."""
        self.settings = get_settings()
        try:
            self.encoding = tiktoken.get_encoding(self.settings.token_model)
        except Exception:
            # Fallback to cl100k_base if specified encoding not found
            self.encoding = tiktoken.get_encoding("cl100k_base")

        self.max_context = self.settings.token_max_context
        self.reserve_output = self.settings.token_reserve_output
        self.warn_threshold = self.settings.token_warn_threshold

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in a list of chat messages.

        Includes overhead for message formatting.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Total token count including overhead
        """
        total = 0
        for msg in messages:
            total += self.MESSAGE_OVERHEAD
            total += self.count_tokens(msg.get("content", ""))
            total += self.count_tokens(msg.get("role", ""))
        total += self.REPLY_PRIMING
        return total

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within a token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated text with "..." suffix if truncated
        """
        if not text:
            return ""

        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text

        # Leave room for "..." suffix
        truncated_tokens = tokens[:max_tokens - 1]
        truncated_text = self.encoding.decode(truncated_tokens)
        return truncated_text + "..."

    def truncate_to_chars_approx(self, text: str, max_chars: int) -> str:
        """
        Truncate text to approximate character limit.

        Uses ~4 chars per token as approximation for Turkish text.

        Args:
            text: Text to truncate
            max_chars: Maximum characters (approximate)

        Returns:
            Truncated text
        """
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."

    def check_context_fit(
        self,
        messages: List[Dict[str, str]],
        additional_content: str = ""
    ) -> TokenCheckResult:
        """
        Check if content fits in context window.

        Args:
            messages: Chat messages to send
            additional_content: Additional content to include

        Returns:
            TokenCheckResult with fit information
        """
        message_tokens = self.count_messages(messages)
        content_tokens = self.count_tokens(additional_content)
        total = message_tokens + content_tokens
        available = self.max_context - self.reserve_output
        utilization = total / available if available > 0 else 1.0

        warning = None
        if utilization > self.warn_threshold:
            warning = (
                f"Token kullanımı yüksek: {total}/{available} "
                f"({utilization:.1%}). Bağlam kısıtlanabilir."
            )

        return TokenCheckResult(
            fits=total <= available,
            total_tokens=total,
            available_tokens=available,
            utilization=utilization,
            over_threshold=utilization > self.warn_threshold,
            warning_message=warning
        )

    def prepare_kazanimlar_context(
        self,
        kazanimlar: List[Dict[str, Any]],
        max_tokens: int = 2000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Prepare kazanımlar list with token-aware truncation.

        Truncates individual descriptions and limits list size
        to fit within token budget.

        Args:
            kazanimlar: List of kazanım dicts
            max_tokens: Maximum tokens for all kazanımlar

        Returns:
            Tuple of (truncated kazanımlar list, total tokens used)
        """
        if not kazanimlar:
            return [], 0

        truncated = []
        current_tokens = 0
        max_desc_tokens = self.settings.retrieval_max_description_length // 4

        for k in kazanimlar:
            desc = k.get("kazanim_description", "")
            code = k.get("kazanim_code", "")

            # Truncate description
            desc_truncated = self.truncate_to_tokens(desc, max_desc_tokens)

            # Build entry text to count tokens
            entry = f"[{code}] {desc_truncated}"
            entry_tokens = self.count_tokens(entry)

            # Check if we have room
            if current_tokens + entry_tokens > max_tokens:
                break

            truncated.append({
                **k,
                "kazanim_description": desc_truncated
            })
            current_tokens += entry_tokens

        return truncated, current_tokens

    def prepare_textbook_context(
        self,
        chunks: List[Dict[str, Any]],
        max_tokens: int = 3000
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Prepare textbook chunks with token-aware truncation.

        Args:
            chunks: List of textbook chunk dicts
            max_tokens: Maximum tokens for all chunks

        Returns:
            Tuple of (truncated chunks list, total tokens used)
        """
        if not chunks:
            return [], 0

        truncated = []
        current_tokens = 0
        content_limit = self.settings.response_content_truncate

        for chunk in chunks:
            content = chunk.get("content", "")

            # Truncate content
            content_truncated = self.truncate_to_chars_approx(content, content_limit)

            # Build entry to count tokens
            entry_tokens = self.count_tokens(content_truncated)

            # Check if we have room
            if current_tokens + entry_tokens > max_tokens:
                break

            truncated.append({
                **chunk,
                "content": content_truncated
            })
            current_tokens += entry_tokens

        return truncated, current_tokens

    def estimate_response_tokens(
        self,
        kazanimlar_count: int,
        chunks_count: int
    ) -> int:
        """
        Estimate tokens needed for response generation.

        Based on typical response structure:
        - Summary: ~100 tokens
        - Per kazanım: ~150 tokens (match reason, etc.)
        - Per chunk reference: ~50 tokens
        - Solution steps: ~200 tokens
        - Final answer: ~50 tokens

        Args:
            kazanimlar_count: Number of kazanımlar
            chunks_count: Number of textbook chunks

        Returns:
            Estimated output tokens
        """
        base = 350  # summary + steps + answer
        per_kazanim = 150
        per_chunk = 50

        return base + (kazanimlar_count * per_kazanim) + (chunks_count * per_chunk)


# Singleton instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get or create singleton TokenManager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
