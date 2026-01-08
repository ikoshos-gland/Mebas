# Faz 1: Proje Altyapısı ve Azure Kurulumu

## 🎯 Amaç
MEB Eğitim RAG sisteminin temelini oluşturmak.

---

## 📁 Proje Yapısı

```
meba/
├── .env                          # Ortam değişkenleri
├── .env.example
├── requirements.txt
├── config/
│   ├── __init__.py              # ÖNEMLİ: Boş olsa bile gerekli!
│   ├── settings.py              # Konfigürasyon yönetimi
│   └── azure_config.py          # Azure bağlantı ayarları
├── src/
│   ├── __init__.py              # ÖNEMLİ: Import hatası almamak için!
│   ├── document_processing/
│   │   └── __init__.py
│   ├── database/
│   │   └── __init__.py
│   ├── vector_store/
│   │   └── __init__.py
│   ├── vision/
│   │   └── __init__.py
│   ├── agents/
│   │   └── __init__.py
│   └── rag/
│       └── __init__.py
├── api/
│   └── __init__.py
├── data/
│   ├── pdfs/kazanimlar/
│   ├── pdfs/ders_kitaplari/
│   └── processed/
└── tests/
    └── __init__.py
```

---

## 🔧 Uygulama Adımları

### 1.1 Bağımlılıklar (requirements.txt)

```txt
# Azure AI Services
azure-ai-documentintelligence>=1.0.2
azure-search-documents>=11.4.0
azure-identity>=1.15.0
azure-core>=1.30.0

# OpenAI & LangChain - KRİTİK!
openai>=1.12.0
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.20
langgraph>=0.0.10               # FAZ 6 İÇİN GEREKLİ!

# Database
sqlalchemy>=2.0.0
alembic>=1.13.0
psycopg2-binary>=2.9.9          # PostgresCheckpointer için

# Vision & API
pillow>=10.0.0
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
slowapi>=0.1.9                  # Rate limiting için

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
aiohttp>=3.9.0
tqdm>=4.66.0

# Development
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

### 1.2 Azure Kaynakları

```powershell
# Resource Group
az group create --name meb-rag-rg --location westeurope

# Document Intelligence
az cognitiveservices account create `
    --name meb-doc-intelligence `
    --resource-group meb-rag-rg `
    --kind FormRecognizer `
    --sku S0 `
    --location westeurope

# AI Search (NOT: Semantic Ranker için Standard önerilir, test için Basic yeterli)
az search service create `
    --name meb-ai-search `
    --resource-group meb-rag-rg `
    --sku basic `
    --location westeurope

# Azure OpenAI - KRİTİK!
az cognitiveservices account create `
    --name meb-openai `
    --resource-group meb-rag-rg `
    --kind OpenAI `
    --sku S0 `
    --location swedencentral  # GPT-4o availability

# GPT-4o deployment (Azure Portal'dan yapılması önerilir)
# text-embedding-ada-002 deployment
```

### 1.3 Ortam Değişkenleri (.env) - TAM LİSTE

```env
# ===== Azure Document Intelligence =====
DOCUMENTINTELLIGENCE_ENDPOINT=https://meb-doc-intelligence.cognitiveservices.azure.com/
DOCUMENTINTELLIGENCE_API_KEY=your_doc_intel_key

# ===== Azure AI Search =====
AZURE_SEARCH_ENDPOINT=https://meb-ai-search.search.windows.net
AZURE_SEARCH_API_KEY=your_search_key
AZURE_SEARCH_INDEX_KAZANIM=meb-kazanimlar-index
AZURE_SEARCH_INDEX_KITAP=meb-kitaplar-index
AZURE_SEARCH_INDEX_IMAGES=meb-images-index
AZURE_SEARCH_INDEX_QUESTIONS=meb-sentetik-sorular-index

# ===== Azure OpenAI - KRİTİK! =====
AZURE_OPENAI_ENDPOINT=https://meb-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your_openai_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# ===== Database =====
DATABASE_URL=sqlite:///data/meb_rag.db
# Production için:
# DATABASE_URL=postgresql://user:pass@localhost:5432/meb_rag

# ===== Application =====
DEBUG=true
LOG_LEVEL=INFO
```

### 1.4 Konfigürasyon (config/settings.py) - DÜZELTILMIŞ

```python
"""
MEB RAG Sistemi - Merkezi Konfigürasyon Modülü
Pydantic V2 uyumlu
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ===== Document Intelligence =====
    doc_intelligence_endpoint: str
    doc_intelligence_api_key: str
    
    # ===== Azure AI Search =====
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_index_kazanim: str = "meb-kazanimlar-index"
    azure_search_index_kitap: str = "meb-kitaplar-index"
    azure_search_index_images: str = "meb-images-index"
    azure_search_index_questions: str = "meb-sentetik-sorular-index"
    
    # ===== Azure OpenAI - KRİTİK! =====
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-02-15-preview"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-ada-002"
    
    # ===== Database =====
    database_url: str = "sqlite:///data/meb_rag.db"
    
    # ===== Application =====
    debug: bool = False
    log_level: str = "INFO"
    
    # Pydantic V2 Modern Config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # .env'de fazladan değişken varsa hata verme
    )


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance döndürür"""
    return Settings()
```

### 1.5 Azure Client Factory (config/azure_config.py)

```python
"""
Azure Servis Client'ları için Factory Modülü
"""
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from config.settings import get_settings


def get_document_intelligence_client() -> DocumentIntelligenceClient:
    """Document Intelligence client instance"""
    settings = get_settings()
    return DocumentIntelligenceClient(
        endpoint=settings.doc_intelligence_endpoint,
        credential=AzureKeyCredential(settings.doc_intelligence_api_key)
    )


def get_search_index_client() -> SearchIndexClient:
    """Search Index yönetim client'ı"""
    settings = get_settings()
    return SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )


def get_search_client(index_name: str) -> SearchClient:
    """Belirli bir index için Search client"""
    settings = get_settings()
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )


def get_azure_openai_client() -> AzureOpenAI:
    """Azure OpenAI client (raw API)"""
    settings = get_settings()
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )


def get_chat_model() -> AzureChatOpenAI:
    """LangChain ChatOpenAI modeli (LangGraph için)"""
    settings = get_settings()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0
    )


def get_embedding_model() -> AzureOpenAIEmbeddings:
    """Embedding modeli (vektör üretimi için)"""
    settings = get_settings()
    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_embedding_deployment
    )
```

### 1.6 Init Dosyalarını Oluştur

```bash
# Windows PowerShell
New-Item -ItemType File -Path "config/__init__.py" -Force
New-Item -ItemType File -Path "src/__init__.py" -Force
New-Item -ItemType File -Path "src/document_processing/__init__.py" -Force
New-Item -ItemType File -Path "src/database/__init__.py" -Force
New-Item -ItemType File -Path "src/vector_store/__init__.py" -Force
New-Item -ItemType File -Path "src/vision/__init__.py" -Force
New-Item -ItemType File -Path "src/agents/__init__.py" -Force
New-Item -ItemType File -Path "src/rag/__init__.py" -Force
New-Item -ItemType File -Path "api/__init__.py" -Force
New-Item -ItemType File -Path "tests/__init__.py" -Force
```

---

## ✅ Doğrulama

```python
# tests/test_config.py
from config.settings import get_settings

def test_all_settings_loaded():
    """Tüm kritik ayarların yüklendiğini doğrula"""
    settings = get_settings()
    
    # Document Intelligence
    assert settings.doc_intelligence_endpoint, "Doc Intel endpoint eksik!"
    assert settings.doc_intelligence_api_key, "Doc Intel key eksik!"
    
    # Azure Search
    assert settings.azure_search_endpoint, "Search endpoint eksik!"
    assert settings.azure_search_api_key, "Search key eksik!"
    
    # Azure OpenAI - KRİTİK!
    assert settings.azure_openai_endpoint, "OpenAI endpoint eksik!"
    assert settings.azure_openai_api_key, "OpenAI key eksik!"
    assert settings.azure_openai_chat_deployment, "Chat deployment eksik!"
    assert settings.azure_openai_embedding_deployment, "Embedding deployment eksik!"
    
    print("✅ Tüm ayarlar yüklendi!")

def test_azure_openai_connection():
    """Azure OpenAI bağlantısını test et"""
    from config.azure_config import get_chat_model
    
    llm = get_chat_model()
    response = llm.invoke("Merhaba!")
    assert response.content, "LLM yanıt vermedi!"
    print("✅ Azure OpenAI bağlantısı başarılı!")
```

---

## ⚠️ SKU Uyarısı

| SKU | Semantic Ranker | Fiyat | Öneri |
|-----|-----------------|-------|-------|
| Basic | Sınırlı | $25/ay | Test |
| Standard (S1) | Tam | $250/ay | Prodüksiyon |

Semantic Ranker olmadan Hybrid Search düzgün çalışmaz!

---

## ⏭️ Sonraki: Faz 2 - PDF İşleme
