"""
MEB RAG Sistemi - Embedding Fonksiyonları
Azure OpenAI text-embedding-3-large ile vektör üretimi (3072 dim)
"""
from openai import AzureOpenAI
from typing import List
import asyncio

from config.settings import get_settings

# Singleton client
_client = None


def get_embedding_client() -> AzureOpenAI:
    """Get or create singleton Azure OpenAI client"""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
    return _client


def embed_text(text: str) -> List[float]:
    """
    Convert text to embedding vector using text-embedding-ada-002.
    
    Args:
        text: Text to embed
        
    Returns:
        List of 3072 floats (embedding vector for text-embedding-3-large)
        
    Raises:
        ValueError: If text is too short
    """
    settings = get_settings()
    client = get_embedding_client()
    
    # Clean text (newlines hurt embedding quality)
    text = text.replace("\n", " ").strip()
    
    # Validation
    if len(text) < 3:
        raise ValueError("Metin çok kısa, embedding oluşturulamaz")
    
    print(f"DEBUG: Using embedding model: '{settings.azure_openai_embedding_deployment}'")
    response = client.embeddings.create(
        input=[text],
        model=settings.azure_openai_embedding_deployment
    )
    return response.data[0].embedding


async def embed_text_async(text: str) -> List[float]:
    """Async version of embed_text"""
    return await asyncio.to_thread(embed_text, text)


def embed_batch(texts: List[str], batch_size: int = 16) -> List[List[float]]:
    """
    Batch embedding for multiple texts.
    
    Azure OpenAI has limits on batch size, so we process in chunks.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts per API call (default 16)
        
    Returns:
        List of embedding vectors
    """
    settings = get_settings()
    client = get_embedding_client()
    
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        # Clean texts
        cleaned = [t.replace("\n", " ").strip() for t in batch]
        
        # Filter out empty texts
        valid_texts = [t for t in cleaned if len(t) >= 3]
        
        if not valid_texts:
            # Return zero vectors for empty batch
            all_embeddings.extend([[0.0] * 3072 for _ in batch])
            continue
        
        if i == 0:
            print(f"DEBUG: Batch embedding model: '{settings.azure_openai_embedding_deployment}'")
            print(f"DEBUG: Using Endpoint: '{settings.azure_openai_endpoint}'")
        
        response = client.embeddings.create(
            input=valid_texts,
            model=settings.azure_openai_embedding_deployment
        )
        
        # Extract embeddings
        batch_embeddings = [d.embedding for d in response.data]
        
        # Handle filtered texts - insert zero vectors
        if len(valid_texts) != len(batch):
            result = []
            valid_idx = 0
            for t in cleaned:
                if len(t) >= 3:
                    result.append(batch_embeddings[valid_idx])
                    valid_idx += 1
                else:
                    result.append([0.0] * 3072)
            all_embeddings.extend(result)
        else:
            all_embeddings.extend(batch_embeddings)
    
    return all_embeddings


async def embed_batch_async(
    texts: List[str], 
    batch_size: int = 16,
    delay_between_batches: float = 0.5
) -> List[List[float]]:
    """
    Async batch embedding with rate limiting.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts per API call
        delay_between_batches: Seconds to wait between batches
        
    Returns:
        List of embedding vectors
    """
    settings = get_settings()
    client = get_embedding_client()
    
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        cleaned = [t.replace("\n", " ").strip() for t in batch]
        valid_texts = [t for t in cleaned if len(t) >= 3]
        
        if not valid_texts:
            all_embeddings.extend([[0.0] * 3072 for _ in batch])
            continue
        
        # Run embedding in thread pool
        response = await asyncio.to_thread(
            client.embeddings.create,
            input=valid_texts,
            model=settings.azure_openai_embedding_deployment
        )
        
        batch_embeddings = [d.embedding for d in response.data]
        
        # Handle filtered texts
        if len(valid_texts) != len(batch):
            result = []
            valid_idx = 0
            for t in cleaned:
                if len(t) >= 3:
                    result.append(batch_embeddings[valid_idx])
                    valid_idx += 1
                else:
                    result.append([0.0] * 3072)
            all_embeddings.extend(result)
        else:
            all_embeddings.extend(batch_embeddings)
        
        # Rate limiting
        if i + batch_size < len(texts):
            await asyncio.sleep(delay_between_batches)
    
    return all_embeddings
