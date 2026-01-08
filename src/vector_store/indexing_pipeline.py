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
    create_textbook_chunk_index_schema
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
            create_question_index_schema(self.settings.azure_search_index_questions),
            create_image_index_schema(self.settings.azure_search_index_images),
            create_textbook_chunk_index_schema(self.settings.azure_search_index_kitap)
        ]
        
        for index in indexes:
            try:
                self.index_client.create_or_update_index(index)
                print(f"✅ Index oluşturuldu/güncellendi: {index.name}")
            except Exception as e:
                print(f"❌ Index hatası {index.name}: {e}")
    
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
            print(f"Processing kazanım {i+1}/{len(kazanimlar)}: {code}")
            
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
                safe_code = raw_code.replace('.', '_').replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C')
                # Add UUID prefix to ensure uniqueness across different PDFs
                doc_id = f"{safe_code}-{uuid.uuid4().hex[:8]}-{j:03d}"
                documents.append({
                    "id": doc_id,
                    "question_text": q.question_text,
                    "difficulty": q.difficulty,
                    "question_type": q.question_type,
                    "parent_kazanim_id": q.parent_kazanim_id,
                    "parent_kazanim_code": q.parent_kazanim_code,
                    "parent_kazanim_desc": kazanim.get("description", ""),
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
            print(f"Processing kazanım {i+1}/{len(kazanimlar)}: {kazanim.get('code')}")
            
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
                safe_code = raw_code.replace('.', '_').replace('İ', 'I').replace('Ş', 'S').replace('Ğ', 'G').replace('Ü', 'U').replace('Ö', 'O').replace('Ç', 'C')
                # Add UUID prefix to ensure uniqueness across different PDFs
                doc_id = f"{safe_code}-{uuid.uuid4().hex[:8]}-{j:03d}"
                documents.append({
                    "id": doc_id,
                    "question_text": q.question_text,
                    "difficulty": q.difficulty,
                    "question_type": q.question_type,
                    "parent_kazanim_id": q.parent_kazanim_id,
                    "parent_kazanim_code": q.parent_kazanim_code,
                    "parent_kazanim_desc": kazanim.get("description", ""),
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
        contents = [c.get("content", "")[:2000] for c in chunks]  # Truncate for embedding
        embeddings = embed_batch(contents)
        
        documents = []
        for chunk, emb in zip(chunks, embeddings):
            documents.append({
                "id": chunk.get("id"),
                "content": chunk.get("content", ""),
                "chunk_type": chunk.get("chunk_type", ""),
                "hierarchy_path": chunk.get("hierarchy_path", ""),
                "page_range": chunk.get("page_range", ""),
                "is_sidebar": chunk.get("is_sidebar", False),
                "textbook_id": chunk.get("textbook_id", 0),
                "chapter_id": chunk.get("chapter_id", 0),
                "grade": chunk.get("grade", 0),
                "subject": chunk.get("subject", ""),
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
