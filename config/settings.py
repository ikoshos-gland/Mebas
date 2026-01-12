"""
MEB RAG Sistemi - Merkezi Konfigürasyon Modülü
Pydantic V2 uyumlu
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ===== Document Intelligence =====
    documentintelligence_endpoint: str = ""
    documentintelligence_api_key: str = ""

    # ===== Azure AI Search =====
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_kazanim: str = "meb-kazanimlar-index"
    azure_search_index_kitap: str = "meb-kitaplar-index"
    azure_search_index_images: str = "meb-images-index"
    azure_search_index_questions: str = "meb-sentetik-sorular-index"

    # ===== Azure OpenAI - CRITICAL! =====
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_teacher_deployment: str = "gpt-5.2-chat"  # Advanced model for teacher synthesis
    azure_openai_embedding_deployment: str = "text-embedding-3-large-957047"

    # ===== RAG Retrieval Settings =====
    rag_confidence_threshold: float = 0.50  # Lowered - blended scores tend to be low
    rag_kazanim_top_k: int = 5  # Max kazanımlar to retrieve
    rag_textbook_top_k: int = 5  # Max textbook chunks (multiple grades)

    # ===== Hybrid Query Expansion Settings =====
    rag_hybrid_kazanim_weight: float = 0.6   # Weight for direct kazanım search (PRIMARY)
    rag_hybrid_question_weight: float = 0.4  # Weight for synthetic question discovery
    rag_hybrid_synergy_bonus: float = 0.1    # Bonus when found in both indexes

    # ===== Database =====
    database_url: str = "sqlite:///data/meb_rag.db"

    # ===== Firebase Authentication =====
    firebase_credentials_path: str = "firebase-service-account.json"

    # ===== Frontend URL (for CORS) =====
    frontend_url: str = "http://localhost:3000"

    # ===== Application =====
    debug: bool = False
    log_level: str = "INFO"

    # ===== Timeout Settings (seconds) =====
    timeout_analyze_input: float = 60.0
    timeout_retrieve: float = 30.0
    timeout_rerank: float = 30.0
    timeout_synthesize: float = 45.0
    timeout_generate_response: float = 60.0
    timeout_vision: float = 30.0
    timeout_question_analyzer: float = 45.0
    timeout_gap_finder: float = 15.0

    # ===== Retrieval Settings =====
    retrieval_min_description_length: int = 10
    retrieval_max_description_length: int = 2500
    retrieval_weak_signal_threshold: float = 0.5
    retrieval_max_retries: int = 3
    retrieval_min_kazanimlar: int = 1  # Reduced - don't force bad results

    # ===== Reranker Settings =====
    reranker_max_items: int = 10
    reranker_truncate_length: int = 300
    reranker_score_blend_ratio: float = 0.7  # Increased - trust LLM judgment more
    reranker_hard_cutoff: float = 0.25  # Filter out if LLM score below this

    # ===== Response Generator Settings =====
    response_max_kazanimlar: int = 5
    response_max_textbook_sections: int = 5
    response_content_truncate: int = 800

    # ===== Token Management =====
    token_model: str = "cl100k_base"
    token_max_context: int = 128000
    token_reserve_output: int = 4096
    token_warn_threshold: float = 0.8

    # ===== Circuit Breaker Settings =====
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 60.0
    circuit_breaker_half_open_requests: int = 3

    # ===== Retry Settings =====
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    retry_exponential_base: float = 2.0

    # ===== LLM Temperature Settings =====
    llm_temperature_deterministic: float = 0.0
    llm_temperature_creative: float = 0.3
    llm_temperature_chat: float = 0.7

    # Pydantic V2 Modern Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Don't error on extra env vars
    )


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance"""
    return Settings()
