"""
MEB RAG Sistemi - Supervisor
Routes between image analysis (full RAG) and follow-up chat
"""
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RouteDecision(str, Enum):
    """Routing decisions"""
    NEW_IMAGE_ANALYSIS = "new_image_analysis"  # Full RAG pipeline
    FOLLOW_UP_CHAT = "follow_up_chat"  # Use existing context


class SupervisorOutput(BaseModel):
    """Structured output from supervisor"""
    decision: RouteDecision = Field(description="Routing decision")
    reasoning: str = Field(description="Why this decision was made")


class Supervisor:
    """
    Routes user input to the appropriate handler.
    
    Decision logic:
    - If image is present → NEW_IMAGE_ANALYSIS
    - If text only and no prior context → NEW_IMAGE_ANALYSIS (will fail gracefully)
    - If text only and has prior context → FOLLOW_UP_CHAT
    """
    
    def decide(
        self,
        has_image: bool,
        has_context: bool,
        user_message: Optional[str] = None
    ) -> SupervisorOutput:
        """
        Decide routing based on input.
        
        Args:
            has_image: Whether the user sent an image
            has_context: Whether there's existing context from prior analysis
            user_message: Optional text message
            
        Returns:
            SupervisorOutput with decision and reasoning
        """
        # Rule 1: Image always triggers full analysis
        if has_image:
            return SupervisorOutput(
                decision=RouteDecision.NEW_IMAGE_ANALYSIS,
                reasoning="Yeni görüntü algılandı - tam analiz başlatılıyor"
            )
        
        # Rule 2: Text with context → follow-up chat
        if has_context and user_message:
            return SupervisorOutput(
                decision=RouteDecision.FOLLOW_UP_CHAT,
                reasoning="Metin sorusu + önceki analiz mevcut - takip sohbeti"
            )
        
        # Rule 3: Text without context → try analysis anyway
        return SupervisorOutput(
            decision=RouteDecision.NEW_IMAGE_ANALYSIS,
            reasoning="Bağlam yok - metin bazlı analiz deneniyor"
        )


class FollowUpChatbot:
    """
    Handles follow-up questions using stored context.
    
    Uses the previous analysis (question solution, kazanımlar, textbook)
    to answer related questions.
    """
    
    SYSTEM_PROMPT = """Sen öğrenci sorularını yanıtlayan bir eğitim asistanısın.
Sana önceki bir soru analizi ve RAG sonuçları veriliyor. 
Bu bağlamı kullanarak öğrencinin takip sorusunu yanıtla.

KURALLAR:
1. Sadece verilen bağlam içinde kal
2. Bilmiyorsan "Bu konuda önceki analizde bilgi yok" de
3. Önceki cevapla tutarlı ol
4. Türkçe, öğrenci dostu yanıt ver
5. Kısa ve öz ol"""

    USER_PROMPT_TEMPLATE = """## Önceki Analiz Bağlamı
{context_summary}

## Sohbet Geçmişi
{chat_history}

## Öğrencinin Sorusu
{user_question}

---
Yukarıdaki bağlamı kullanarak öğrencinin sorusunu yanıtla."""

    def __init__(self):
        """Initialize chatbot with Azure OpenAI"""
        from openai import AzureOpenAI
        from config.settings import get_settings
        
        settings = get_settings()
        self.client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self.deployment = settings.azure_openai_chat_deployment  # Use gpt-4o for chat
    
    async def chat(
        self,
        user_question: str,
        context_summary: str,
        chat_history: list[Dict[str, str]] = None
    ) -> str:
        """
        Generate response using context.
        
        Args:
            user_question: The follow-up question
            context_summary: Summary of previous analysis
            chat_history: Previous chat messages
            
        Returns:
            Response text
        """
        import asyncio
        
        # Format chat history
        history_text = ""
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages
                role = "Öğrenci" if msg.get("role") == "user" else "Asistan"
                history_text += f"{role}: {msg.get('content', '')}\n"
        
        if not history_text:
            history_text = "(Henüz sohbet yok)"
        
        prompt = self.USER_PROMPT_TEMPLATE.format(
            context_summary=context_summary,
            chat_history=history_text,
            user_question=user_question
        )
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1024,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Yanıt üretilemedi: {str(e)}"
    
    def chat_sync(
        self,
        user_question: str,
        context_summary: str,
        chat_history: list[Dict[str, str]] = None
    ) -> str:
        """Synchronous version of chat"""
        import asyncio
        return asyncio.run(self.chat(user_question, context_summary, chat_history))
