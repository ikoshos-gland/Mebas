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
    
    # ===== Database =====
    database_url: str = "sqlite:///data/meb_rag.db"
    
    # ===== Application =====
    debug: bool = False
    log_level: str = "INFO"
    
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
