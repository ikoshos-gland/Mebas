"""
Azure Servis Client'ları için Factory Modülü
"""
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from openai import AzureOpenAI, AsyncAzureOpenAI
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
    """Search Index management client"""
    settings = get_settings()
    return SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )


def get_search_client(index_name: str) -> SearchClient:
    """Search client for a specific index"""
    settings = get_settings()
    return SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=index_name,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )


def get_azure_openai_client() -> AzureOpenAI:
    """Azure OpenAI client (sync API)"""
    settings = get_settings()
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )


def get_async_azure_openai_client() -> AsyncAzureOpenAI:
    """Azure OpenAI client (async API)"""
    settings = get_settings()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version
    )


def get_chat_model() -> AzureChatOpenAI:
    """LangChain ChatOpenAI model (for LangGraph)"""
    settings = get_settings()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_chat_deployment,
        temperature=0
    )


def get_embedding_model() -> AzureOpenAIEmbeddings:
    """Embedding model (for vector generation)"""
    settings = get_settings()
    return AzureOpenAIEmbeddings(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_openai_embedding_deployment
    )
