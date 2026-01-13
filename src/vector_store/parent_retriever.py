"""
MEB RAG Sistemi - Parent Document Retriever
Hybrid Search ile kazanım eşleştirme

PRIMARY: Kazanımlar index'i (meb-kazanimlar-index) - MEB müfredat hedefleri
SECONDARY: Sentetik sorular index'i - örnek soru formatları için
"""
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from typing import List, Optional, Dict, Any

from src.vector_store.embeddings import embed_text, embed_text_async


class ParentDocumentRetriever:
    """
    Hybrid Search: Vector + Keyword + Semantic Reranker

    NEW Flow (Fixed):
    Student Question → Kazanımlar Index (PRIMARY) → Related Content

    OLD (Broken) Flow:
    Student Question → Synthetic Questions → Parent Kazanım

    Key features:
    - Direct kazanım search as PRIMARY source
    - Grade and subject filters for pedagogical correctness
    - Semantic reranking for improved accuracy
    """

    def __init__(self, search_client: SearchClient, kazanim_client: SearchClient = None):
        """
        Args:
            search_client: Azure Search client (for questions or default index)
            kazanim_client: Azure Search client for kazanımlar index (PRIMARY)
        """
        self.search_client = search_client
        self.kazanim_client = kazanim_client

    async def search_kazanimlar_direct(
        self,
        student_question: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        is_exam_mode: bool = False,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        PRIMARY: Search kazanımlar index directly.

        This searches the actual MEB learning objectives, NOT synthetic questions.
        This should be the primary source for curriculum alignment.

        Args:
            student_question: The question to analyze
            grade: Student's grade level (9-12)
            subject: Subject code (BİY, M, F, etc.)
            is_exam_mode: If True, includes lower grades (YKS mode)
            top_k: Number of top kazanımlar to return

        Returns:
            List of kazanım matches with scores
        """
        import asyncio

        if not self.kazanim_client:
            # Fallback to old behavior if kazanim_client not provided
            return await self.search_async(
                student_question, grade, subject, is_exam_mode, top_k
            )

        # 1. Create embedding
        query_embedding = await embed_text_async(student_question)

        # 2. Build filter
        filter_str = self._build_grade_filter(grade, subject, is_exam_mode)

        # 3. Hybrid Search directly on kazanımlar index
        results = await asyncio.to_thread(
            self.kazanim_client.search,
            search_text=student_question,  # Keyword search on description
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
            top=top_k * 2,  # Get extra for deduplication
            select=[
                "id",
                "code",
                "parent_code",
                "description",
                "title",
                "grade",
                "subject",
                "semester"
            ]
        )

        # 4. Format results
        kazanimlar = []
        seen_codes = set()

        for result in results:
            code = result.get("code", "")
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)

            kazanimlar.append({
                "kazanim_id": result.get("id", ""),
                "kazanim_code": code,
                "kazanim_description": result.get("title", ""),  # Use ORIGINAL description (title field), NOT enriched
                "kazanim_title": result.get("title", ""),
                "parent_code": result.get("parent_code", ""),
                "subject": result.get("subject", ""),
                "semester": result.get("semester", 0),
                "grade": result.get("grade", 0),
                "score": result.get("@search.score", 0),
                "matched_questions": []  # Will be populated from synthetic questions if needed
            })

            if len(kazanimlar) >= top_k:
                break

        return kazanimlar

    async def search_hybrid_expansion(
        self,
        student_question: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        is_exam_mode: bool = False,
        top_k: int = 5,
        kazanim_weight: float = 0.6,
        question_weight: float = 0.4,
        synergy_bonus: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Query Expansion: Search BOTH indexes in parallel.

        Flow:
        1. Search kazanimlar index (direct semantic match) - PRIMARY
        2. Search sentetik-sorular index (similar questions) - SECONDARY
        3. Extract kazanim codes from question matches
        4. Merge results by kazanim_code
        5. Apply weighted scoring with synergy bonus

        Args:
            student_question: The question to analyze
            grade: Student's grade level
            subject: Subject code
            is_exam_mode: YKS mode flag
            top_k: Number of results to return
            kazanim_weight: Weight for direct kazanim search (0-1)
            question_weight: Weight for question-based discovery (0-1)
            synergy_bonus: Bonus when found in both indexes

        Returns:
            Merged, deduplicated, scored kazanimlar
        """
        import asyncio

        # Check if we have both clients
        if not self.kazanim_client:
            # Fallback to questions-only search
            return await self.search_async(
                student_question, grade, subject, is_exam_mode, top_k
            )

        # 1. Run BOTH searches in parallel
        kazanim_task = self.search_kazanimlar_direct(
            student_question=student_question,
            grade=grade,
            subject=subject,
            is_exam_mode=is_exam_mode,
            top_k=top_k * 2  # Get more to merge
        )

        question_task = self.search_async(
            student_question=student_question,
            grade=grade,
            subject=subject,
            is_exam_mode=is_exam_mode,
            top_k=top_k * 2
        )

        try:
            # Wait for both with timeout
            kazanim_results, question_results = await asyncio.wait_for(
                asyncio.gather(kazanim_task, question_task, return_exceptions=True),
                timeout=25.0
            )
        except asyncio.TimeoutError:
            print("[HybridSearch] Timeout - falling back to kazanim-only")
            return await self.search_kazanimlar_direct(
                student_question, grade, subject, is_exam_mode, top_k
            )

        # Handle exceptions from individual searches
        if isinstance(kazanim_results, Exception):
            print(f"[HybridSearch] Kazanim search error: {kazanim_results}")
            kazanim_results = []
        if isinstance(question_results, Exception):
            print(f"[HybridSearch] Question search error: {question_results}")
            question_results = []

        # If both failed, return empty for retry logic
        if not kazanim_results and not question_results:
            return []

        # 2. Merge results by kazanim_code
        merged = self._merge_hybrid_results(
            kazanim_results=kazanim_results,
            question_results=question_results,
            kazanim_weight=kazanim_weight,
            question_weight=question_weight,
            synergy_bonus=synergy_bonus
        )

        # 3. Sort by merged score and return top_k
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.get("merged_score", 0),
            reverse=True
        )

        # 4. Assign match_type based on relative score
        # Primary: Top result(s) with significantly higher scores
        # Alternative: Lower scoring results (contextual/related)
        #
        # Logic: First result is always primary. Subsequent results are primary
        # only if their score is within 10% of the top score.
        final_results = []
        top_score = sorted_results[0].get("score", 0) if sorted_results else 0

        for i, result in enumerate(sorted_results[:top_k]):
            score = result.get("score", result.get("merged_score", 0))

            # First result is always primary
            # Others are primary only if score >= 90% of top score
            if i == 0 or (top_score > 0 and score >= top_score * 0.9):
                result["match_type"] = "primary"
            else:
                result["match_type"] = "alternative"

            final_results.append(result)

        return final_results

    def _merge_hybrid_results(
        self,
        kazanim_results: List[Dict[str, Any]],
        question_results: List[Dict[str, Any]],
        kazanim_weight: float,
        question_weight: float,
        synergy_bonus: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Merge results from both indexes by kazanim_code.

        Score Merging Strategy:
        - If found in BOTH: weighted average + synergy bonus
        - If found in kazanim only: kazanim score * weight
        - If found in questions only: question score * weight (discovery)
        """
        merged: Dict[str, Dict[str, Any]] = {}

        # Normalize scores to 0-1 range
        max_kazanim_score = max(
            [r.get("score", 0) for r in kazanim_results] or [1]
        )
        max_question_score = max(
            [r.get("score", 0) for r in question_results] or [1]
        )

        # Process kazanim results first (PRIMARY)
        for k in kazanim_results:
            code = k.get("kazanim_code")
            if not code:
                continue

            normalized_score = k.get("score", 0) / max(max_kazanim_score, 0.001)

            merged[code] = {
                **k,
                "kazanim_score": normalized_score,
                "question_score": 0.0,
                "found_via": ["kazanim"],
                "merged_score": normalized_score * kazanim_weight,
                "score": normalized_score * kazanim_weight  # Override original score
            }

        # Process question results (SECONDARY - can discover or boost)
        for q in question_results:
            code = q.get("kazanim_code")
            if not code:
                continue

            normalized_score = q.get("score", 0) / max(max_question_score, 0.001)

            if code in merged:
                # BOOST: Found in both indexes - strong signal!
                existing = merged[code]
                existing["question_score"] = normalized_score
                existing["found_via"].append("question")
                existing["matched_questions"] = q.get("matched_questions", [])

                # Boosted score: weighted average + synergy bonus
                base_score = (
                    existing["kazanim_score"] * kazanim_weight +
                    normalized_score * question_weight
                )
                existing["merged_score"] = min(1.0, base_score + synergy_bonus)
                existing["score"] = existing["merged_score"]
            else:
                # DISCOVERY: Found via questions but not in direct search
                merged[code] = {
                    "kazanim_id": q.get("kazanim_id"),
                    "kazanim_code": code,
                    "kazanim_description": q.get("kazanim_description"),
                    "kazanim_title": q.get("kazanim_title", ""),
                    "parent_code": q.get("parent_code", ""),
                    "subject": q.get("subject"),
                    "semester": q.get("semester"),
                    "grade": q.get("grade"),
                    "kazanim_score": 0.0,
                    "question_score": normalized_score,
                    "found_via": ["question"],
                    "matched_questions": q.get("matched_questions", []),
                    "merged_score": normalized_score * question_weight,
                    "score": normalized_score * question_weight
                }

        return merged

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
            top=100,  # Get more for grouping
            select=[
                "parent_kazanim_id",
                "parent_kazanim_code",
                "parent_kazanim_desc",
                "kazanim_title",
                "subject",
                "semester",
                "grade",
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
                    "title": result.get("kazanim_title", ""),
                    "subject": result.get("subject", ""),
                    "semester": result.get("semester", 0),
                    "grade": result.get("grade", 0),
                    "matches": []
                }

            # Accumulate score from search - USE MAX instead of SUM to avoid quantity bias
            score = result.get("@search.score", 0)
            kazanim_scores[kid]["score"] = max(kazanim_scores[kid]["score"], score)
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
                "kazanim_description": data["title"] or data["desc"],  # Prefer original (title), fallback to enriched
                "kazanim_title": data["title"],
                "subject": data["subject"],
                "semester": data["semester"],
                "grade": data["grade"],
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
            top=100,  # Get more for grouping
            select=[
                "parent_kazanim_id",
                "parent_kazanim_code",
                "parent_kazanim_desc",
                "kazanim_title",
                "subject",
                "semester",
                "grade",
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
                    "title": result.get("kazanim_title", ""),
                    "subject": result.get("subject", ""),
                    "semester": result.get("semester", 0),
                    "grade": result.get("grade", 0),
                    "matches": []
                }

            score = result.get("@search.score", 0)
            kazanim_scores[kid]["score"] = max(kazanim_scores[kid]["score"], score)
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
                "kazanim_description": data["title"] or data["desc"],  # Prefer original (title), fallback to enriched
                "kazanim_title": data["title"],
                "subject": data["subject"],
                "semester": data["semester"],
                "grade": data["grade"],
                "score": data["score"],
                "matched_questions": data["matches"][:3]
            }
            for kid, data in sorted_kazanimlar
        ]

    async def search_siblings_async(
        self,
        target_code: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for sibling kazanımlar (e.g., 12.1.1 and 12.1.2).
        
        Args:
            target_code: The code to find siblings for (e.g., "12.1.1")
            grade: Optional grade filter
            subject: Optional subject filter
            
        Returns:
            List of sibling kazanımlar with MatchType.ALTERNATIVE logic ready
        """
        import asyncio
        
        # Determine prefix (e.g., "12.1.1" -> "12.1.")
        # If code is shorter (e.g. "12.1"), just use it as is?
        parts = target_code.split(".")
        if len(parts) >= 3:
            prefix = ".".join(parts[:2]) + "."  # "12.1."
        else:
            return []  # Too short to have siblings
            
        # Build filter string
        # We want: (parent_kazanim_code startswith prefix) AND (parent_kazanim_code ne target_code)
        # Azure Search syntax for startswith is not standard in filter
        # But we can use search.ismatch against the code field if searchable
        
        # Better approach: Filter by prefix exact match logic is hard in Azure Search OData
        # But we can SEARCH for the prefix in the code field
        
        # Build filter manually
        filter_parts = []
        if grade:
             filter_parts.append(f"grade eq {grade}")
        if subject:
             filter_parts.append(f"subject eq '{subject}'")
             
        # Exclude the exact target code (we already have it)
        filter_parts.append(f"parent_kazanim_code ne '{target_code}'")
        
        filter_str = " and ".join(filter_parts) if filter_parts else None
        
        results = await asyncio.to_thread(
            self.search_client.search,
            search_text=prefix,  # Search for the prefix
            search_fields=["parent_kazanim_code"], # Limit search to code field
            filter=filter_str,
            top=5,  # Just get 5 closest neighbors
            select=[
                "parent_kazanim_id",
                "parent_kazanim_code",
                "parent_kazanim_desc"
            ]
        )
        
        siblings = []
        seen_codes = set()
        
        for r in results:
            code = r.get("parent_kazanim_code")
            if not code or code in seen_codes:
                continue
                
            # Verify prefix locally to be safe (search text might be fuzzy)
            if not code.startswith(prefix):
                continue
                
            seen_codes.add(code)
            siblings.append({
                "kazanim_id": r.get("parent_kazanim_id"),
                "kazanim_code": code,
                "kazanim_description": r.get("kazanim_title") or r.get("parent_kazanim_desc"),  # Prefer original
                "score": 0.8,  # Artificial high score for relevance
                "matched_questions": [],
                "match_type": "alternative"
            })
            
        return siblings
    
    async def search_textbook_by_kazanimlar(
        self,
        kazanim_codes: List[str],
        question_text: str,
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        is_exam_mode: bool = False,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search textbook chunks related to given kazanımlar.

        Uses Hybrid Search (Vector + Text) on textbook index with
        CRITICAL grade/subject filtering for pedagogical correctness.

        Args:
            kazanim_codes: List of kazanım codes (used for context enrichment)
            question_text: The question/topic to search for
            grade: Student's grade level - CRITICAL for filtering content
            subject: Subject code for filtering
            is_exam_mode: If True, includes content from lower grades (YKS mode)
            top_k: Number of results to return
        """
        import asyncio
        from config.settings import get_settings
        from config.azure_config import get_search_client

        settings = get_settings()
        client = get_search_client(settings.azure_search_index_kitap)

        # 1. Build search text enriched with kazanım codes for better semantic matching
        # This helps find content that covers the specific learning outcomes
        search_text = question_text
        if kazanim_codes:
            # Add kazanım codes to search - helps match curriculum-aligned content
            codes_str = " ".join(kazanim_codes[:3])  # Limit to top 3 to avoid noise
            search_text = f"{question_text} {codes_str}"

        # 2. Embed the enriched search text
        query_embedding = await embed_text_async(search_text)

        # 3. Build filter - CRITICAL for pedagogical correctness
        # A 3rd grader should NOT see 12th grade content
        filter_parts = []

        if subject:
            filter_parts.append(f"subject eq '{subject}'")

        if grade:
            if is_exam_mode:
                # YKS Mode: Include content from student's grade and below
                # e.g., 12th grader sees grades 9, 10, 11, 12
                filter_parts.append(f"grade le {grade}")
            else:
                # School Mode: ONLY student's exact grade level
                filter_parts.append(f"grade eq {grade}")

        filter_str = " and ".join(filter_parts) if filter_parts else None

        # 4. Hybrid Search with semantic reranking
        results = await asyncio.to_thread(
            client.search,
            search_text=question_text,  # Use original question for keyword matching
            vector_queries=[
                VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=20,
                    fields="embedding"
                )
            ],
            filter=filter_str,  # CRITICAL: Apply grade/subject filter
            query_type="semantic",  # Enable semantic reranking
            semantic_configuration_name="semantic-config",
            top=top_k,
            select=[
                "id",
                "content",
                "hierarchy_path",
                "page_range",
                "subject",
                "grade",
                "semester",
                "chunk_type",
                "textbook_id",
                "textbook_name"
            ]
        )

        return [
            {
                "id": r.get("id"),
                "content": r.get("content"),
                "hierarchy_path": r.get("hierarchy_path"),
                "page_range": r.get("page_range"),
                "subject": r.get("subject", ""),
                "grade": r.get("grade", 0),
                "semester": r.get("semester", 0),
                "chunk_type": r.get("chunk_type", ""),
                "textbook_id": r.get("textbook_id"),
                "textbook_name": r.get("textbook_name", "Ders Kitabı"),
                "score": r.get("@search.score", 0)
            }
            for r in results
        ]
