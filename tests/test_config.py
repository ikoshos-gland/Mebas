"""
Configuration tests for MEB RAG System
"""
import pytest
from config.settings import get_settings, Settings


def test_settings_instance():
    """Test that settings can be instantiated"""
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_settings_singleton():
    """Test that get_settings returns the same instance (cached)"""
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2


def test_default_values():
    """Test that default values are set correctly"""
    settings = get_settings()
    
    # Check default index names
    assert settings.azure_search_index_kazanim == "meb-kazanimlar-index"
    assert settings.azure_search_index_kitap == "meb-kitaplar-index"
    assert settings.azure_search_index_images == "meb-images-index"
    assert settings.azure_search_index_questions == "meb-sentetik-sorular-index"
    
    # Check default OpenAI settings
    assert settings.azure_openai_api_version == "2024-02-15-preview"
    assert settings.azure_openai_chat_deployment == "gpt-4o"
    assert settings.azure_openai_embedding_deployment == "text-embedding-ada-002"
    
    # Check database default
    assert settings.database_url == "sqlite:///data/meb_rag.db"


def test_all_settings_loaded():
    """Verify all critical settings are available (may be empty strings without .env)"""
    settings = get_settings()
    
    # These will be empty strings without .env, but should exist
    assert hasattr(settings, 'doc_intelligence_endpoint')
    assert hasattr(settings, 'doc_intelligence_api_key')
    assert hasattr(settings, 'azure_search_endpoint')
    assert hasattr(settings, 'azure_search_api_key')
    assert hasattr(settings, 'azure_openai_endpoint')
    assert hasattr(settings, 'azure_openai_api_key')
    
    print("✅ All settings attributes exist!")


# Optional: Test Azure OpenAI connection (requires valid .env)
# Uncomment when you have valid Azure credentials
# def test_azure_openai_connection():
#     """Test Azure OpenAI connection"""
#     from config.azure_config import get_chat_model
#     
#     llm = get_chat_model()
#     response = llm.invoke("Merhaba!")
#     assert response.content, "LLM did not respond!"
#     print("✅ Azure OpenAI connection successful!")
