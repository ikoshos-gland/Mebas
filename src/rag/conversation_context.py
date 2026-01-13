"""
MEB RAG Sistemi - Conversation Context Manager
Stores analysis results per session for follow-up chat
"""
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ConversationContext:
    """Stores context from analysis for follow-up questions"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    
    # Original question data
    question_text: str = ""
    question_image_base64: Optional[str] = None
    
    # QuestionAnalyzer results
    question_analysis: Optional[Dict[str, Any]] = None
    
    # RAG results  
    matched_kazanimlar: List[Dict[str, Any]] = field(default_factory=list)
    textbook_chunks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Synthesizer output
    teacher_explanation: Optional[str] = None
    
    # Chat history
    messages: List[Dict[str, str]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        """Add a message to chat history"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_context_summary(self) -> str:
        """Get a summary of the context for the chatbot"""
        summary_parts = []
        
        if self.question_text:
            summary_parts.append(f"## Analiz Edilen Soru\n{self.question_text[:500]}")
        
        if self.question_analysis:
            qa = self.question_analysis
            summary_parts.append(f"""
## Soru Çözümü
**Doğru Cevap:** {qa.get('correct_answer', 'Belirsiz')}
**Açıklama:** {qa.get('explanation', '')}
""")
        
        if self.matched_kazanimlar:
            kazanim_list = "\n".join([
                f"- {k.get('kazanim_code', '')}: {k.get('kazanim_description', '')[:100]}..."
                for k in self.matched_kazanimlar[:3]
            ])
            summary_parts.append(f"## Eşleşen Kazanımlar\n{kazanim_list}")
        
        if self.teacher_explanation:
            summary_parts.append(f"## Önceki Açıklama\n{self.teacher_explanation[:1000]}...")
        
        return "\n\n".join(summary_parts)


class ConversationManager:
    """
    Manages conversation contexts across sessions.
    
    In production, this should use Redis or a database.
    For now, uses in-memory storage.
    """
    
    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}
    
    def create_context(self, session_id: Optional[str] = None) -> ConversationContext:
        """Create a new conversation context"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        context = ConversationContext(session_id=session_id)
        self._contexts[session_id] = context
        return context
    
    def get_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get an existing context by session ID"""
        return self._contexts.get(session_id)
    
    def update_context(
        self,
        session_id: str,
        question_text: Optional[str] = None,
        question_image_base64: Optional[str] = None,
        question_analysis: Optional[Dict[str, Any]] = None,
        matched_kazanimlar: Optional[List[Dict[str, Any]]] = None,
        textbook_chunks: Optional[List[Dict[str, Any]]] = None,
        teacher_explanation: Optional[str] = None
    ) -> ConversationContext:
        """Update an existing context with new analysis results"""
        context = self.get_context(session_id)
        if not context:
            context = self.create_context(session_id)
        
        if question_text is not None:
            context.question_text = question_text
        if question_image_base64 is not None:
            context.question_image_base64 = question_image_base64
        if question_analysis is not None:
            context.question_analysis = question_analysis
        if matched_kazanimlar is not None:
            context.matched_kazanimlar = matched_kazanimlar
        if textbook_chunks is not None:
            context.textbook_chunks = textbook_chunks
        if teacher_explanation is not None:
            context.teacher_explanation = teacher_explanation
        
        return context
    
    def delete_context(self, session_id: str) -> bool:
        """Delete a context"""
        if session_id in self._contexts:
            del self._contexts[session_id]
            return True
        return False
    
    def cleanup_old_contexts(self, max_age_hours: int = 24):
        """Remove contexts older than max_age_hours"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        old_sessions = [
            sid for sid, ctx in self._contexts.items()
            if ctx.created_at < cutoff
        ]
        
        for sid in old_sessions:
            del self._contexts[sid]


# Global conversation manager instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager (singleton)"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
