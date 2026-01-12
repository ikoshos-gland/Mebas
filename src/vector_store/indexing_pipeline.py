"""
MEB RAG Sistemi - Indexing Pipeline
Sentetik soru ve görsel indexleme
"""
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential
from typing import List, Optional
import asyncio
import time
import uuid

from config.settings import get_settings
from src.vector_store.embeddings import embed_text, embed_batch, embed_batch_async
from src.vector_store.question_generator import (
    SyntheticQuestionGenerator, 
    SyntheticQuestion
)
from src.vector_store.index_schema import (
    create_question_index_schema,
    create_image_index_schema,
    create_textbook_chunk_index_schema,
    create_kazanim_index_schema
)


class IndexingPipeline:
    """
    Batch indexing pipeline for Azure AI Search.
    
    Features:
    - Creates indexes if they don't exist
    - Rate limited batch processing
    - Progress tracking
    """
    
    BATCH_SIZE = 100  # Documents per upload batch
    RATE_LIMIT_DELAY = 1.0  # Seconds between batches
    
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        
        # Index client for creating indexes
        self.index_client = SearchIndexClient(
            endpoint=settings.azure_search_endpoint,
            credential=AzureKeyCredential(settings.azure_search_api_key)
        )
        
        # Question generator
        self.question_generator = SyntheticQuestionGenerator()
    
    def _get_search_client(self, index_name: str) -> SearchClient:
        """Get search client for a specific index"""
        return SearchClient(
            endpoint=self.settings.azure_search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(self.settings.azure_search_api_key)
        )
    
    def create_all_indexes(self) -> None:
        """Create all required indexes"""
        indexes = [
            # PRIMARY: Kazanımlar - MEB müfredat hedefleri
            create_kazanim_index_schema(self.settings.azure_search_index_kazanim),
            # Ders kitabı içerikleri
            create_textbook_chunk_index_schema(self.settings.azure_search_index_kitap),
            # Görseller
            create_image_index_schema(self.settings.azure_search_index_images),
            # Sentetik sorular (örnek soru üretimi için)
            create_question_index_schema(self.settings.azure_search_index_questions),
        ]

        for index in indexes:
            try:
                self.index_client.create_or_update_index(index)
                print(f"✅ Index oluşturuldu/güncellendi: {index.name}")
            except Exception as e:
                print(f"❌ Index hatası {index.name}: {e}")

    def delete_indexes(self, target_mode: str = "all") -> None:
        """
        Delete indexes based on target mode.

        Args:
            target_mode: "all", "kazanim", or "kitap"
        """
        indexes_to_delete = []

        if target_mode == "kazanim":
            indexes_to_delete = [
                self.settings.azure_search_index_kazanim,  # Raw kazanımlar
                self.settings.azure_search_index_questions  # Sentetik sorular
            ]
            print(f"\n⚠️  RESET MODE: Deleting Kazanım + Sentetik Soru indexes...")

        elif target_mode == "kitap":
            indexes_to_delete = [
                self.settings.azure_search_index_images,
                self.settings.azure_search_index_kitap
            ]
            print(f"\n⚠️  RESET MODE: Deleting Textbook (Chunks & Images) indexes...")

        else:
            # ALL
            indexes_to_delete = [
                self.settings.azure_search_index_kazanim,
                self.settings.azure_search_index_questions,
                self.settings.azure_search_index_images,
                self.settings.azure_search_index_kitap
            ]
            print("\n⚠️  RESET MODE: DELETING ALL INDEXES...")

        for index_name in indexes_to_delete:
            try:
                self.index_client.delete_index(index_name)
                print(f"🗑️  Deleted index: {index_name}")
            except Exception as e:
                # 404 is fine (index doesn't exist)
                print(f"ℹ️  Index {index_name} not found or error: {e}")
        print("✅ Selected indexes deleted.\n")

    def index_kazanimlar_raw(self, kazanimlar: List[dict]) -> int:
        """
        Index raw kazanımlar (MEB learning objectives) directly.

        This is the PRIMARY index for curriculum alignment.
        These are the actual learning objectives from MEB curriculum,
        NOT synthetic questions.

        Args:
            kazanimlar: List of kazanim dicts with:
                - id: unique identifier
                - code: kazanım code (e.g., "BİY.9.1.1.a")
                - parent_code: parent kazanım code
                - description: the learning objective text
                - title: parent kazanım title
                - grade: grade level (9, 10, 11, 12)
                - subject: subject code (BİY, M, F, etc.)
                - semester: semester (1 or 2)

        Returns:
            Number of documents indexed
        """
        client = self._get_search_client(self.settings.azure_search_index_kazanim)
        total_indexed = 0

        print(f"\n📚 Indexing {len(kazanimlar)} kazanımlar to PRIMARY index...")

        # Create embeddings for all kazanımlar
        # Combine title + description for better semantic matching
        texts_to_embed = []
        for k in kazanimlar:
            title = k.get("title", "")
            desc = k.get("description", "")
            code = k.get("code", "")
            # Format: "BİY.9.1.1.a: Title - Description"
            embed_text = f"{code}: {title} - {desc}" if title else f"{code}: {desc}"
            texts_to_embed.append(embed_text[:2000])  # Limit for embedding

        embeddings = embed_batch(texts_to_embed)

        # Prepare documents
        documents = []
        for kazanim, emb in zip(kazanimlar, embeddings):
            documents.append({
                "id": kazanim.get("id"),
                "code": kazanim.get("code", ""),
                "parent_code": kazanim.get("parent_code", ""),
                "description": kazanim.get("description", ""),
                "title": kazanim.get("title", ""),
                "grade": kazanim.get("grade", 0),
                "subject": kazanim.get("subject", ""),
                "semester": kazanim.get("semester", 0),
                "embedding": emb
            })

        # Upload in batches
        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i:i + self.BATCH_SIZE]
            try:
                result = client.upload_documents(batch)
                success = sum(1 for r in result if r.succeeded)
                total_indexed += success
                print(f"  ✅ Indexed batch {i//self.BATCH_SIZE + 1}: {success}/{len(batch)} kazanımlar")
            except Exception as e:
                print(f"  ❌ Upload error: {e}")
            time.sleep(self.RATE_LIMIT_DELAY)

        print(f"✅ Total kazanımlar indexed: {total_indexed}")
        return total_indexed
    
    def index_kazanimlar(
        self,
        kazanimlar: List[dict],
        generate_questions: bool = True,
        questions_per_kazanim: int = 20
    ) -> int:
        """
        Index kazanımlar with synthetic questions.
        
        Args:
            kazanimlar: List of kazanim dicts with code, description, grade, subject
            generate_questions: Whether to generate synthetic questions
            questions_per_kazanim: Questions per kazanım (cost consideration)
            
        Returns:
            Number of documents indexed
        """
        client = self._get_search_client(self.settings.azure_search_index_questions)
        total_indexed = 0
        
        for i, kazanim in enumerate(kazanimlar):
            code = kazanim.get('code') or kazanim.get('kazanim_code', 'Unknown')
            print(f"Processing sentetik soru {i+1}/{len(kazanimlar)}: {code}")
            
            if generate_questions:
                # Generate synthetic questions
                questions = self.question_generator.generate_for_kazanim(
                    kazanim,
                    count=questions_per_kazanim
                )
            else:
                # Use pre-generated question from the input dict
                # Check if question_text is provided (pre-generated question)
                if kazanim.get("question_text"):
                    questions = [SyntheticQuestion(
                        question_text=kazanim.get("question_text", ""),
                        difficulty=kazanim.get("difficulty", "orta"),
                        question_type=kazanim.get("question_type", "kavram"),
                        parent_kazanim_id=str(kazanim.get("id", "")),
                        parent_kazanim_code=kazanim.get("code", "")
                    )]
                else:
                    # Fallback: index kazanım description as a question
                    questions = [SyntheticQuestion(
                        question_text=kazanim.get("description", ""),
                        difficulty="orta",
                        question_type="kavram",
                        parent_kazanim_id=str(kazanim.get("id", "")),
                        parent_kazanim_code=kazanim.get("code", "")
                    )]
            
            if not questions:
                print(f"  ⚠️ No questions generated for {kazanim.get('code')}")
                continue
            
            # Create embeddings for questions
            question_texts = [q.question_text for q in questions]
            embeddings = embed_batch(question_texts)
            
            # Prepare documents for indexing
            documents = []
            for j, (q, emb) in enumerate(zip(questions, embeddings)):
                # Sanitize ID: Azure Search only allows letters, digits, _, -, =
                raw_code = kazanim.get('code', 'K') or 'K'
                # Replace both uppercase and lowercase Turkish characters
                safe_code = (raw_code
                    .replace('.', '_')
                    .replace('İ', 'I').replace('ı', 'i')
                    .replace('Ş', 'S').replace('ş', 's')
                    .replace('Ğ', 'G').replace('ğ', 'g')
                    .replace('Ü', 'U').replace('ü', 'u')
                    .replace('Ö', 'O').replace('ö', 'o')
                    .replace('Ç', 'C').replace('ç', 'c')
                )
                # Add UUID prefix to ensure uniqueness across different PDFs
                doc_id = f"{safe_code}-{uuid.uuid4().hex[:8]}-{j:03d}"
                documents.append({
                    "id": doc_id,
                    "question_text": q.question_text,
                    "difficulty": q.difficulty,
                    "question_type": q.question_type,
                    "parent_kazanim_id": q.parent_kazanim_id,
                    "parent_kazanim_code": kazanim.get("parent_code", q.parent_kazanim_code),
                    "parent_kazanim_desc": kazanim.get("description", ""),
                    "kazanim_title": kazanim.get("title", ""),  # Parent title for context
                    "grade": kazanim.get("grade", 0),
                    "subject": kazanim.get("subject", ""),
                    "semester": kazanim.get("semester", 0),
                    "embedding": emb
                })

            # Upload batch
            try:
                # DEBUG: Show document details
                if documents:
                    print(f"  DEBUG: Doc ID: {documents[0]['id']}")
                    print(f"  DEBUG: Semester: {documents[0].get('semester', 'N/A')}, Grade: {documents[0].get('grade', 'N/A')}")
                    print(f"  DEBUG: Question preview: {documents[0]['question_text'][:80]}...")
                
                result = client.upload_documents(documents)
                success = sum(1 for r in result if r.succeeded)
                total_indexed += success
                print(f"  ✅ Indexed {success}/{len(documents)} documents")
            except Exception as e:
                print(f"  ❌ Upload error: {e}")
            
            # Rate limiting
            time.sleep(self.RATE_LIMIT_DELAY)
        
        print(f"\n✅ Total indexed: {total_indexed} documents")
        return total_indexed
    
    async def index_kazanimlar_async(
        self,
        kazanimlar: List[dict],
        generate_questions: bool = True,
        questions_per_kazanim: int = 20
    ) -> int:
        """Async version of index_kazanimlar"""
        client = self._get_search_client(self.settings.azure_search_index_questions)
        total_indexed = 0
        
        for i, kazanim in enumerate(kazanimlar):
            print(f"Processing sentetik soru {i+1}/{len(kazanimlar)}: {kazanim.get('code')}")
            
            if generate_questions:
                questions = await self.question_generator.generate_for_kazanim_async(
                    kazanim,
                    count=questions_per_kazanim
                )
            else:
                questions = [SyntheticQuestion(
                    question_text=kazanim.get("description", ""),
                    difficulty="orta",
                    question_type="kavram",
                    parent_kazanim_id=str(kazanim.get("id", "")),
                    parent_kazanim_code=kazanim.get("code", "")
                )]
            
            if not questions:
                continue
            
            question_texts = [q.question_text for q in questions]
            embeddings = await embed_batch_async(question_texts)

            documents = []
            for j, (q, emb) in enumerate(zip(questions, embeddings)):
                # Sanitize ID: Azure Search only allows letters, digits, _, -, =
                raw_code = kazanim.get('code', 'K') or 'K'
                # Replace both uppercase and lowercase Turkish characters
                safe_code = (raw_code
                    .replace('.', '_')
                    .replace('İ', 'I').replace('ı', 'i')
                    .replace('Ş', 'S').replace('ş', 's')
                    .replace('Ğ', 'G').replace('ğ', 'g')
                    .replace('Ü', 'U').replace('ü', 'u')
                    .replace('Ö', 'O').replace('ö', 'o')
                    .replace('Ç', 'C').replace('ç', 'c')
                )
                # Add UUID prefix to ensure uniqueness across different PDFs
                doc_id = f"{safe_code}-{uuid.uuid4().hex[:8]}-{j:03d}"
                documents.append({
                    "id": doc_id,
                    "question_text": q.question_text,
                    "difficulty": q.difficulty,
                    "question_type": q.question_type,
                    "parent_kazanim_id": q.parent_kazanim_id,
                    "parent_kazanim_code": kazanim.get("parent_code", q.parent_kazanim_code),
                    "parent_kazanim_desc": kazanim.get("description", ""),
                    "kazanim_title": kazanim.get("title", ""),  # Parent title for context
                    "grade": kazanim.get("grade", 0),
                    "subject": kazanim.get("subject", ""),
                    "semester": kazanim.get("semester", 0),
                    "embedding": emb
                })

            try:
                result = await asyncio.to_thread(client.upload_documents, documents)
                success = sum(1 for r in result if r.succeeded)
                total_indexed += success
            except Exception as e:
                print(f"Upload error: {e}")
            
            await asyncio.sleep(self.RATE_LIMIT_DELAY)
        
        return total_indexed
    
    def index_images(self, images: List[dict]) -> int:
        """
        Index textbook images.
        
        Args:
            images: List of image dicts with caption, type, path, etc.
            
        Returns:
            Number indexed
        """
        client = self._get_search_client(self.settings.azure_search_index_images)
        
        # Create embeddings from captions
        captions = [img.get("caption", "") for img in images]
        embeddings = embed_batch(captions)
        
        documents = []
        for img, emb in zip(images, embeddings):
            documents.append({
                "id": img.get("id"),
                "caption": img.get("caption", ""),
                "image_type": img.get("image_type", "unknown"),
                "page_number": img.get("page_number", 0),
                "chunk_id": img.get("chunk_id", ""),
                "related_text": img.get("related_text", ""),
                "hierarchy_path": img.get("hierarchy_path", ""),
                "image_path": img.get("image_path", ""),
                "width": img.get("width", 0),
                "height": img.get("height", 0),
                # Grade/Subject for filtering - CRITICAL for pedagogical correctness
                "grade": img.get("grade", 0),
                "subject": img.get("subject", ""),
                "textbook_id": img.get("textbook_id", 0),
                "embedding": emb
            })
        
        # Upload in batches
        total_indexed = 0
        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i:i + self.BATCH_SIZE]
            try:
                result = client.upload_documents(batch)
                success = sum(1 for r in result if r.succeeded)
                total_indexed += success
            except Exception as e:
                print(f"Image upload error: {e}")
            time.sleep(self.RATE_LIMIT_DELAY)
        
        print(f"✅ Indexed {total_indexed} images")
        return total_indexed
    
    def index_textbook_chunks(self, chunks: List[dict]) -> int:
        """
        Index textbook chunks directly.

        Args:
            chunks: List of chunk dicts with content, type, etc.

        Returns:
            Number indexed
        """
        client = self._get_search_client(self.settings.azure_search_index_kitap)

        # Create embeddings from content
        # Use smart truncation: hierarchy_path + content for better semantic representation
        # text-embedding-3-large supports ~8191 tokens, so 6000 chars (~1500 tokens) is safe
        # Include hierarchy_path for context
        contents = []
        for c in chunks:
            hierarchy = c.get("hierarchy_path", "")
            content = c.get("content", "")
            # Combine hierarchy (context) with content for better embeddings
            # If content is very long, sample from beginning, middle, and end
            # to preserve semantic meaning from all parts
            if len(content) > 5500:
                # Improved truncation: beginning (definitions) + middle (core content) + end (conclusions)
                # 3000 from start + 1000 from middle + 1500 from end = 5500 chars
                mid_start = len(content) // 2 - 500
                content = (
                    content[:3000] +
                    "\n[...]\n" +
                    content[mid_start:mid_start + 1000] +
                    "\n[...]\n" +
                    content[-1500:]
                )
                print(f"   ⚠️ Truncated long chunk ({len(c.get('content', ''))} chars): {c.get('id', '')[:8]}...")
            embed_text = f"{hierarchy}\n\n{content}" if hierarchy else content
            contents.append(embed_text[:6000])  # Hard limit for safety

        embeddings = embed_batch(contents)

        documents = []
        for chunk, emb in zip(chunks, embeddings):
            documents.append({
                "id": chunk.get("id"),
                "content": chunk.get("content", ""),  # Store full content
                "chunk_type": chunk.get("chunk_type", ""),
                "hierarchy_path": chunk.get("hierarchy_path", ""),
                "page_range": chunk.get("page_range", ""),
                "is_sidebar": chunk.get("is_sidebar", False),
                "textbook_id": chunk.get("textbook_id", 0),
                "textbook_name": chunk.get("textbook_name", ""),
                "chapter_id": chunk.get("chapter_id", 0),
                "grade": chunk.get("grade", 0),
                "subject": chunk.get("subject", ""),
                "semester": chunk.get("semester", 0),  # Added semester for curriculum alignment
                "embedding": emb
            })
        
        total_indexed = 0
        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i:i + self.BATCH_SIZE]
            try:
                result = client.upload_documents(batch)
                success = sum(1 for r in result if r.succeeded)
                total_indexed += success
            except Exception as e:
                print(f"Chunk upload error: {e}")
            time.sleep(self.RATE_LIMIT_DELAY)
        
        print(f"✅ Indexed {total_indexed} chunks")
        return total_indexed
