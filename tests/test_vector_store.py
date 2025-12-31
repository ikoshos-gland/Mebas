"""
Tests for Vector Store Module (Phase 4)
"""
import pytest


class TestEmbeddings:
    """Tests for embedding functions"""
    
    def test_embed_text_function_exists(self):
        """Test embed_text function exists"""
        from src.vector_store.embeddings import embed_text
        assert callable(embed_text)
        print("✅ embed_text function exists!")
    
    def test_embed_batch_function_exists(self):
        """Test embed_batch function exists"""
        from src.vector_store.embeddings import embed_batch
        assert callable(embed_batch)
        print("✅ embed_batch function exists!")
    
    def test_embed_text_async_exists(self):
        """Test async embedding function exists"""
        from src.vector_store.embeddings import embed_text_async
        assert callable(embed_text_async)
        print("✅ embed_text_async function exists!")


class TestQuestionGenerator:
    """Tests for synthetic question generator"""
    
    def test_synthetic_question_dataclass(self):
        """Test SyntheticQuestion dataclass"""
        from src.vector_store.question_generator import SyntheticQuestion
        
        q = SyntheticQuestion(
            question_text="Test soru",
            difficulty="kolay",
            question_type="çoktan_seçmeli",
            parent_kazanim_id="1",
            parent_kazanim_code="M.5.1.2.3"
        )
        assert q.question_text == "Test soru"
        assert q.difficulty == "kolay"
        print("✅ SyntheticQuestion dataclass test passed!")
    
    def test_generator_class_exists(self):
        """Test generator class exists"""
        from src.vector_store.question_generator import SyntheticQuestionGenerator
        assert SyntheticQuestionGenerator is not None
        print("✅ SyntheticQuestionGenerator class exists!")


class TestIndexSchema:
    """Tests for index schemas"""
    
    def test_question_index_schema(self):
        """Test question index schema creation"""
        from src.vector_store.index_schema import create_question_index_schema
        
        schema = create_question_index_schema("test-index")
        assert schema.name == "test-index"
        
        # Check required fields exist
        field_names = [f.name for f in schema.fields]
        assert "id" in field_names
        assert "question_text" in field_names
        assert "embedding" in field_names
        assert "grade" in field_names
        assert "subject" in field_names
        
        print("✅ Question index schema test passed!")
    
    def test_image_index_schema(self):
        """Test image index schema creation"""
        from src.vector_store.index_schema import create_image_index_schema
        
        schema = create_image_index_schema("test-images")
        assert schema.name == "test-images"
        
        field_names = [f.name for f in schema.fields]
        assert "caption" in field_names
        assert "image_type" in field_names
        assert "embedding" in field_names
        
        print("✅ Image index schema test passed!")
    
    def test_chunk_index_schema(self):
        """Test textbook chunk index schema creation"""
        from src.vector_store.index_schema import create_textbook_chunk_index_schema
        
        schema = create_textbook_chunk_index_schema("test-chunks")
        assert schema.name == "test-chunks"
        
        field_names = [f.name for f in schema.fields]
        assert "content" in field_names
        assert "chunk_type" in field_names
        
        print("✅ Chunk index schema test passed!")


class TestRetrievers:
    """Tests for retriever classes"""
    
    def test_parent_retriever_exists(self):
        """Test ParentDocumentRetriever class exists"""
        from src.vector_store.parent_retriever import ParentDocumentRetriever
        assert ParentDocumentRetriever is not None
        print("✅ ParentDocumentRetriever class exists!")
    
    def test_image_retriever_exists(self):
        """Test ImageRetriever class exists"""
        from src.vector_store.image_retriever import ImageRetriever
        assert ImageRetriever is not None
        print("✅ ImageRetriever class exists!")


class TestIndexingPipeline:
    """Tests for indexing pipeline"""
    
    def test_pipeline_class_exists(self):
        """Test IndexingPipeline class exists"""
        from src.vector_store.indexing_pipeline import IndexingPipeline
        assert IndexingPipeline is not None
        print("✅ IndexingPipeline class exists!")


if __name__ == "__main__":
    # Run tests manually
    test_emb = TestEmbeddings()
    test_emb.test_embed_text_function_exists()
    test_emb.test_embed_batch_function_exists()
    test_emb.test_embed_text_async_exists()
    
    test_qg = TestQuestionGenerator()
    test_qg.test_synthetic_question_dataclass()
    test_qg.test_generator_class_exists()
    
    test_schema = TestIndexSchema()
    test_schema.test_question_index_schema()
    test_schema.test_image_index_schema()
    test_schema.test_chunk_index_schema()
    
    test_ret = TestRetrievers()
    test_ret.test_parent_retriever_exists()
    test_ret.test_image_retriever_exists()
    
    test_pipe = TestIndexingPipeline()
    test_pipe.test_pipeline_class_exists()
    
    print("\n✅ All Phase 4 tests passed!")
