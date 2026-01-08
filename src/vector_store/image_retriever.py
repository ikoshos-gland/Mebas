"""
MEB RAG Sistemi - Image Retriever
Görsel arama ve citation
"""
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from typing import List, Optional, Dict, Any

from src.vector_store.embeddings import embed_text, embed_text_async


class ImageRetriever:
    """
    Search textbook images by description or related content.
    
    Enables responses like "See Figure 3.1 on page 45"
    """
    
    def __init__(self, search_client: SearchClient):
        """
        Args:
            search_client: Azure Search client for images index
        """
        self.search_client = search_client
    
    def search_by_description(
        self,
        description: str,
        image_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search images by text description.
        
        Args:
            description: What to search for (e.g., "grafik çizimi", "üçgen")
            image_type: Filter by type (diagram, graph, photo, etc.)
            top_k: Number of results
            
        Returns:
            List of matching images with metadata
        """
        # Create embedding from description
        query_embedding = embed_text(description)
        
        # Build filter
        filter_str = f"image_type eq '{image_type}'" if image_type else None
        
        # Hybrid search
        results = self.search_client.search(
            search_text=description,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=20,
                    fields="embedding"
                )
            ],
            filter=filter_str,
            top=top_k,
            select=[
                "id",
                "caption",
                "image_type",
                "page_number",
                "chunk_id",
                "hierarchy_path",
                "image_path",
                "width",
                "height"
            ]
        )
        
        return [
            {
                "image_id": r.get("id"),
                "caption": r.get("caption"),
                "image_type": r.get("image_type"),
                "page_number": r.get("page_number"),
                "chunk_id": r.get("chunk_id"),
                "hierarchy_path": r.get("hierarchy_path"),
                "image_path": r.get("image_path"),
                "dimensions": f"{r.get('width', 0)}x{r.get('height', 0)}",
                "score": r.get("@search.score", 0)
            }
            for r in results
        ]
    
    async def search_by_description_async(
        self,
        description: str,
        image_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Async version of search_by_description"""
        import asyncio
        
        query_embedding = await embed_text_async(description)
        filter_str = f"image_type eq '{image_type}'" if image_type else None
        
        results = await asyncio.to_thread(
            self.search_client.search,
            search_text=description,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=20,
                    fields="embedding"
                )
            ],
            filter=filter_str,
            top=top_k,
            select=[
                "id",
                "caption",
                "image_type",
                "page_number",
                "chunk_id",
                "hierarchy_path",
                "image_path",
                "width",
                "height"
            ]
        )
        
        return [
            {
                "image_id": r.get("id"),
                "caption": r.get("caption"),
                "image_type": r.get("image_type"),
                "page_number": r.get("page_number"),
                "chunk_id": r.get("chunk_id"),
                "hierarchy_path": r.get("hierarchy_path"),
                "image_path": r.get("image_path"),
                "dimensions": f"{r.get('width', 0)}x{r.get('height', 0)}",
                "score": r.get("@search.score", 0)
            }
            for r in results
        ]
    
    def search_by_chunk(
        self,
        chunk_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all images related to a specific chunk.
        
        Args:
            chunk_id: The BookChunk ID
            top_k: Max images to return
            
        Returns:
            List of images in that chunk
        """
        results = self.search_client.search(
            search_text="*",
            filter=f"chunk_id eq '{chunk_id}'",
            top=top_k,
            select=[
                "id",
                "caption",
                "image_type",
                "page_number",
                "image_path",
                "width",
                "height"
            ]
        )
        
        return [
            {
                "image_id": r.get("id"),
                "caption": r.get("caption"),
                "image_type": r.get("image_type"),
                "page_number": r.get("page_number"),
                "image_path": r.get("image_path"),
                "dimensions": f"{r.get('width', 0)}x{r.get('height', 0)}"
            }
            for r in results
        ]
    
    def search_by_page(
        self,
        page_number: int,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all images on a specific page.
        
        Args:
            page_number: Page number
            top_k: Max images to return
            
        Returns:
            List of images on that page
        """
        results = self.search_client.search(
            search_text="*",
            filter=f"page_number eq {page_number}",
            top=top_k,
            select=[
                "id",
                "caption",
                "image_type",
                "chunk_id",
                "hierarchy_path",
                "image_path",
                "width",
                "height"
            ]
        )
        
        return [
            {
                "image_id": r.get("id"),
                "caption": r.get("caption"),
                "image_type": r.get("image_type"),
                "chunk_id": r.get("chunk_id"),
                "hierarchy_path": r.get("hierarchy_path"),
                "image_path": r.get("image_path"),
                "dimensions": f"{r.get('width', 0)}x{r.get('height', 0)}"
            }
            for r in results
        ]
