"""
MEB RAG Sistemi - Chat Memory
Loads conversation history from database for LLM context
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session


def load_chat_history(
    db: Session,
    conversation_id: str,
    max_messages: int = 10,
    max_chars_per_message: int = 1000
) -> List[Dict[str, str]]:
    """
    Load recent chat history from database for a conversation.

    Args:
        db: Database session
        conversation_id: Conversation UUID
        max_messages: Maximum number of messages to load (default: 10)
        max_chars_per_message: Truncate message content (default: 1000 chars)

    Returns:
        List of messages in format [{"role": "user"|"assistant", "content": "..."}]
    """
    from src.database.models import Message

    if not conversation_id:
        return []

    try:
        # Get recent messages ordered by creation time
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(
            Message.created_at.desc()
        ).limit(max_messages).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        # Format for LLM
        chat_history = []
        for msg in messages:
            content = msg.content or ""
            # Truncate if too long
            if len(content) > max_chars_per_message:
                content = content[:max_chars_per_message] + "..."

            chat_history.append({
                "role": msg.role,
                "content": content
            })

        return chat_history

    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []


def format_chat_history_for_prompt(
    chat_history: List[Dict[str, str]],
    max_history_chars: int = 4000
) -> str:
    """
    Format chat history as a string for inclusion in LLM prompts.

    Args:
        chat_history: List of messages from load_chat_history()
        max_history_chars: Maximum total characters for history section

    Returns:
        Formatted string with conversation history
    """
    if not chat_history:
        return ""

    # Skip the last message if it's the current user question
    # (it will be included separately in the prompt)
    history_to_format = chat_history[:-1] if chat_history else []

    if not history_to_format:
        return ""

    formatted_parts = []
    total_chars = 0

    for msg in history_to_format:
        role_label = "Ogrenci" if msg["role"] == "user" else "Asistan"
        content = msg["content"]

        entry = f"**{role_label}:** {content}"
        entry_chars = len(entry)

        if total_chars + entry_chars > max_history_chars:
            # Truncate this entry to fit
            remaining = max_history_chars - total_chars - 50  # Leave room for "..."
            if remaining > 100:
                entry = f"**{role_label}:** {content[:remaining]}..."
                formatted_parts.append(entry)
            break

        formatted_parts.append(entry)
        total_chars += entry_chars

    if not formatted_parts:
        return ""

    return "## ONCEKI SOHBET\n" + "\n\n".join(formatted_parts) + "\n\n---\n"


def format_chat_history_as_messages(
    chat_history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Format chat history as OpenAI-compatible message list.

    This is useful for including history as actual message turns
    rather than as part of the prompt.

    Args:
        chat_history: List of messages from load_chat_history()

    Returns:
        List of messages ready for OpenAI API
    """
    if not chat_history:
        return []

    # Skip the last message (current question)
    history_to_format = chat_history[:-1] if chat_history else []

    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_to_format
    ]
