"""
MEB RAG Sistemi - LLM Reranker
Uses LLM to rerank kazanım results for better relevance
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_openai import AzureChatOpenAI

from config.settings import get_settings
from src.utils.resilience import with_resilience, CircuitOpenError


class RerankedItem(BaseModel):
    """Single reranked kazanım with relevance score."""
    kazanim_code: str = Field(description="Kazanım kodu")
    relevance_score: float = Field(
        ge=0.0, le=1.0, 
        description="0-1 arası alakalılık skoru"
    )
    reasoning: str = Field(
        description="Skorun kısa gerekçesi",
        max_length=200
    )


class RerankerOutput(BaseModel):
    """Structured output for reranking."""
    ranked_items: List[RerankedItem] = Field(
        description="Alakalılık skoruna göre sıralanmış kazanımlar"
    )


class LLMReranker:
    """
    LLM-based reranker for kazanım retrieval results.
    
    Uses structured output to score each kazanım's relevance
    to the student's question, then reorders by combined score.
    """
    
    SYSTEM_PROMPT = """Sen bir MEB müfredat uzmanısın. Öğrenci sorusuna göre kazanımların alakalılığını değerlendir.

SKORLAMA KRİTERLERİ:
- 0.9-1.0: Kazanım soruyu doğrudan kapsar, tam eşleşme
- 0.7-0.8: Güçlü ilişki, kazanım soruyla yakından alakalı
- 0.5-0.6: Orta düzey ilişki, kısmen alakalı
- 0.3-0.4: Zayıf ilişki, dolaylı bağlantı
- 0.0-0.2: Alakasız veya çok uzak bağlantı

HER KAZANIM İÇİN:
1. Soruyla semantik benzerliği değerlendir
2. Konusal örtüşmeyi kontrol et
3. Sınıf seviyesi uyumluluğunu göz önünde bulundur
4. 0-1 arası skor ve kısa gerekçe ver"""

    USER_PROMPT_TEMPLATE = """## Öğrenci Sorusu
{question}

## Değerlendirilecek Kazanımlar
{kazanimlar}

Her kazanımı soruyla alakalılığına göre skorla (0.0-1.0)."""

    def __init__(self, llm: Optional[AzureChatOpenAI] = None):
        """
        Initialize reranker.
        
        Args:
            llm: Optional pre-configured LLM. Creates default if not provided.
        """
        self.settings = get_settings()
        if llm:
            self.llm = llm
        else:
            self.llm = AzureChatOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
                azure_deployment=self.settings.azure_openai_chat_deployment,
                temperature=self.settings.llm_temperature_deterministic
            )
        
        # Create structured output chain
        self.structured_llm = self.llm.with_structured_output(RerankerOutput)
    
    async def rerank(
        self,
        question: str,
        kazanimlar: List[Dict[str, Any]],
        top_k: Optional[int] = None,
        score_blend_ratio: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank kazanımlar using LLM relevance scoring.
        
        Args:
            question: Student's question text
            kazanimlar: List of kazanım dicts from retrieval
            top_k: Number of top results to return
            score_blend_ratio: How much to weight LLM score vs original
                               0.5 = equal blend, 1.0 = LLM only
        
        Returns:
            Reranked list of kazanımlar with updated scores
        """
        # Use settings defaults if not provided
        if top_k is None:
            top_k = self.settings.rag_kazanim_top_k
        if score_blend_ratio is None:
            score_blend_ratio = self.settings.reranker_score_blend_ratio

        if not kazanimlar:
            return []

        if len(kazanimlar) == 1:
            return kazanimlar

        # Limit input to avoid token limits
        kazanimlar_to_rank = kazanimlar[:self.settings.reranker_max_items]
        
        # Format kazanımlar for prompt
        kazanim_text = self._format_kazanimlar(kazanimlar_to_rank)
        
        prompt = self.USER_PROMPT_TEMPLATE.format(
            question=question,
            kazanimlar=kazanim_text
        )
        
        try:
            # Get structured reranking result with resilience
            result = await self._invoke_llm_with_resilience(prompt)
            
            # Build score map
            score_map = {
                item.kazanim_code: {
                    "score": item.relevance_score,
                    "reasoning": item.reasoning
                }
                for item in result.ranked_items
            }
            
            # Blend scores and add reranking info
            for k in kazanimlar_to_rank:
                code = k.get("kazanim_code", "")
                original_score = k.get("score", 0)
                
                if code in score_map:
                    llm_score = score_map[code]["score"]
                    # Normalize original score to 0-1 range
                    # If already <= 1.0, it's pre-normalized (from hybrid search)
                    # Otherwise, assume max ~10 from Azure Search
                    if original_score <= 1.0:
                        original_normalized = original_score
                    else:
                        original_normalized = min(1.0, original_score / 10.0)
                    # Blend scores
                    blended = (
                        (1 - score_blend_ratio) * original_normalized +
                        score_blend_ratio * llm_score
                    )
                    k["rerank_score"] = llm_score
                    k["rerank_reasoning"] = score_map[code]["reasoning"]
                    k["blended_score"] = blended
                else:
                    # Not scored by LLM, keep original normalized
                    if original_score <= 1.0:
                        k["blended_score"] = original_score
                    else:
                        k["blended_score"] = min(1.0, original_score / 10.0)
            
            # Sort by blended score
            reranked = sorted(
                kazanimlar_to_rank, 
                key=lambda x: x.get("blended_score", 0), 
                reverse=True
            )
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"[LLMReranker] Error during reranking: {e}")
            # Fallback: return original order
            return kazanimlar[:top_k]
    
    def rerank_sync(
        self, 
        question: str, 
        kazanimlar: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Synchronous version of rerank."""
        import asyncio
        return asyncio.run(self.rerank(question, kazanimlar, top_k))
    
    async def _invoke_llm_with_resilience(self, prompt: str) -> RerankerOutput:
        """
        Invoke LLM with circuit breaker and retry protection.

        Uses the resilience module for:
        - Circuit breaker to fast-fail if Azure OpenAI is down
        - Exponential backoff retry for transient failures
        - Timeout protection
        """
        @with_resilience(
            circuit_name="azure_openai_reranker",
            timeout=self.settings.timeout_rerank,
            use_circuit_breaker=True,
            use_retry=True
        )
        async def _invoke():
            return await self.structured_llm.ainvoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ])

        return await _invoke()

    def _format_kazanimlar(self, kazanimlar: List[Dict[str, Any]]) -> str:
        """Format kazanımlar for LLM prompt."""
        lines = []
        truncate_len = self.settings.reranker_truncate_length
        for i, k in enumerate(kazanimlar, 1):
            code = k.get("kazanim_code", "?")
            desc = k.get("kazanim_description", "")[:truncate_len]
            grade = k.get("grade", "?")
            lines.append(f"{i}. [{code}] (Sınıf: {grade})\n   {desc}")
        return "\n\n".join(lines)


# Convenience function
async def rerank_kazanimlar(
    question: str,
    kazanimlar: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Convenience function for reranking kazanımlar.
    
    Args:
        question: Student's question
        kazanimlar: Retrieved kazanımlar
        top_k: Number of results to return
        
    Returns:
        Reranked kazanımlar
    """
    reranker = LLMReranker()
    return await reranker.rerank(question, kazanimlar, top_k)
