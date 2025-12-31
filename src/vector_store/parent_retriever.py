"""
MEB RAG Sistemi - Parent Document Retriever
Hybrid Search ile kazanım eşleştirme
"""
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from typing import List, Optional, Dict, Any

from src.vector_store.embeddings import embed_text, embed_text_async


class ParentDocumentRetriever:
    """
    Hybrid Search: Vector + Keyword + Semantic Reranker
    
    Flow:
    Student Question → Matching Synthetic Questions → Parent Kazanım
    
    Key features:
    - Grade and subject filters for pedagogical correctness
    - Semantic reranking for improved accuracy
    - Parent kazanım grouping and scoring
    """
    
    def __init__(self, search_client: SearchClient, kazanim_db=None):
        """
        Args:
            search_client: Azure Search client for questions index
            kazanim_db: Optional database session for kazanım lookup
        """
        self.search_client = search_client
        self.kazanim_db = kazanim_db
    
    def _build_grade_filter(
        self,
        grade: Optional[int],
        subject: Optional[str],
        is_exam_mode: bool = False
    ) -> Optional[str]:
        """
        Dynamic filter based on search mode.
        
        CRITICAL for pedagogical correctness:
        - Okul Modu (is_exam_mode=False): grade eq X
          Öğrenci sadece kendi sınıf seviyesini görür.
        - YKS Modu (is_exam_mode=True): grade le X
          YKS hazırlık için 9-12 arası tüm içerik.
        """
        filters = []
        
        if subject:
            filters.append(f"subject eq '{subject}'")
        
        if grade:
            if is_exam_mode:
                # YKS Modu: Öğrencinin sınıfına KADAR olan tüm içerik
                # 12. sınıf öğrencisi 9, 10, 11, 12 sınıfları görür
                filters.append(f"grade le {grade}")
            else:
                # Okul Modu: SADECE öğrencinin sınıfı
                filters.append(f"grade eq {grade}")
        
        return " and ".join(filters) if filters else None
    
    def search(
        self,
        student_question: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        is_exam_mode: bool = False,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search to find matching kazanımlar (sync version).
        
        CRITICAL: Grade and subject filters ensure pedagogical correctness!
        A 3rd grader shouldn't get 6th grade content.
        
        Args:
            student_question: The question to analyze
            grade: Student's grade level (1-12)
            subject: Subject code (M, F, T, etc.)
            top_k: Number of top kazanımlar to return
            
        Returns:
            List of kazanım matches with scores
        """
        # 1. Create embedding
        query_embedding = embed_text(student_question)
        
        # 2. Build filter with YKS mode support
        filter_str = self._build_grade_filter(grade, subject, is_exam_mode)
        
        # 3. Hybrid Search (Vector + Keyword + Semantic)
        results = self.search_client.search(
            search_text=student_question,  # Keyword search
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=50,  # Get wide pool
                    fields="embedding"
                )
            ],
            filter=filter_str,
            query_type="semantic",  # Enable semantic reranker
            semantic_configuration_name="semantic-config",
            top=50,  # Get more for grouping
            select=[
                "parent_kazanim_id",
                "parent_kazanim_code",
                "parent_kazanim_desc",
                "question_text",
                "difficulty"
            ]
        )
        
        # 4. Group by parent kazanım and score
        kazanim_scores: Dict[str, Dict] = {}
        
        for result in results:
            kid = result.get("parent_kazanim_id", "")
            if not kid:
                continue
                
            if kid not in kazanim_scores:
                kazanim_scores[kid] = {
                    "score": 0,
                    "code": result.get("parent_kazanim_code", ""),
                    "desc": result.get("parent_kazanim_desc", ""),
                    "matches": []
                }
            
            # Accumulate score from search
            score = result.get("@search.score", 0)
            kazanim_scores[kid]["score"] += score
            kazanim_scores[kid]["matches"].append({
                "question": result.get("question_text", ""),
                "difficulty": result.get("difficulty", "")
            })
        
        # 5. Sort by score and return top kazanımlar
        sorted_kazanimlar = sorted(
            kazanim_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )[:top_k]
        
        return [
            {
                "kazanim_id": kid,
                "kazanim_code": data["code"],
                "kazanim_description": data["desc"],
                "score": data["score"],
                "matched_questions": data["matches"][:3]  # Top 3 matches
            }
            for kid, data in sorted_kazanimlar
        ]
    
    async def search_async(
        self,
        student_question: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        is_exam_mode: bool = False,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Async version of search"""
        import asyncio
        
        # Get embedding async
        query_embedding = await embed_text_async(student_question)
        
        # Build filter with YKS mode support
        filter_str = self._build_grade_filter(grade, subject, is_exam_mode)
        
        # Run search in thread pool (Azure SDK is sync)
        results = await asyncio.to_thread(
            self.search_client.search,
            search_text=student_question,
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=50,
                    fields="embedding"
                )
            ],
            filter=filter_str,
            query_type="semantic",
            semantic_configuration_name="semantic-config",
            top=50,
            select=[
                "parent_kazanim_id",
                "parent_kazanim_code",
                "parent_kazanim_desc",
                "question_text",
                "difficulty"
            ]
        )
        
        # Group and score
        kazanim_scores: Dict[str, Dict] = {}
        
        for result in results:
            kid = result.get("parent_kazanim_id", "")
            if not kid:
                continue
                
            if kid not in kazanim_scores:
                kazanim_scores[kid] = {
                    "score": 0,
                    "code": result.get("parent_kazanim_code", ""),
                    "desc": result.get("parent_kazanim_desc", ""),
                    "matches": []
                }
            
            score = result.get("@search.score", 0)
            kazanim_scores[kid]["score"] += score
            kazanim_scores[kid]["matches"].append({
                "question": result.get("question_text", ""),
                "difficulty": result.get("difficulty", "")
            })
        
        sorted_kazanimlar = sorted(
            kazanim_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )[:top_k]
        
        return [
            {
                "kazanim_id": kid,
                "kazanim_code": data["code"],
                "kazanim_description": data["desc"],
                "score": data["score"],
                "matched_questions": data["matches"][:3]
            }
            for kid, data in sorted_kazanimlar
        ]
    
    async def search_textbook_by_kazanimlar(
        self,
        kazanim_codes: List[str],
        question_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search textbook chunks related to given kazanımlar.
        
        Called after initial kazanım retrieval to get relevant
        textbook sections for the response.
        """
        # This would use a separate textbook chunks index
        # For now, return empty - will be implemented with textbook index
        return []
