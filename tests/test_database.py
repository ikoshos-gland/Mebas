"""
Tests for Database Module (Phase 3)
"""
import pytest


class TestDatabaseModels:
    """Tests for SQLAlchemy models"""
    
    def test_subject_model(self):
        """Test Subject model structure"""
        from src.database.models import Subject
        
        subject = Subject(id=1, code="M", name="Matematik")
        assert subject.code == "M"
        assert subject.name == "Matematik"
        print("✅ Subject model test passed!")
    
    def test_kazanim_model(self):
        """Test Kazanim model structure"""
        from src.database.models import Kazanim
        
        kazanim = Kazanim(
            id=1,
            code="M.5.1.2.3",
            description="Doğal sayılarla toplama işlemi yapar.",
            grade=5,
            learning_area="Sayılar ve İşlemler",
            sub_learning_area="Doğal Sayılar",
            bloom_level="Uygulama"
        )
        assert kazanim.code == "M.5.1.2.3"
        assert kazanim.grade == 5
        print("✅ Kazanim model test passed!")
    
    def test_book_chunk_model(self):
        """Test BookChunk model structure"""
        from src.database.models import BookChunk
        
        chunk = BookChunk(
            id="test-001",
            content="Test content",
            chunk_type="concept",
            hierarchy_path="Ünite1/Konu1",
            page_range="1-2",
            is_sidebar=False
        )
        assert chunk.id == "test-001"
        assert chunk.chunk_type == "concept"
        print("✅ BookChunk model test passed!")
    
    def test_textbook_image_model(self):
        """Test TextbookImage model structure"""
        from src.database.models import TextbookImage
        
        image = TextbookImage(
            id="img-001",
            image_path="/path/to/image.png",
            width=200,
            height=200,
            image_type="diagram",
            page_number=5
        )
        assert image.id == "img-001"
        assert image.image_type == "diagram"
        print("✅ TextbookImage model test passed!")


class TestDatabaseOperations:
    """Tests for database operations"""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup and teardown test database"""
        from src.database.db import init_db, drop_db, reinitialize_engine

        # Reinitialize with in-memory database for tests
        reinitialize_engine("sqlite:///:memory:")
        init_db()
        yield
        drop_db()
    
    def test_init_db(self):
        """Test database initialization"""
        from src.database.db import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "subjects", "kazanimlar", "textbooks", "chapters",
            "book_chunks", "textbook_images", "feedbacks"
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found!"
        
        print("✅ Database initialization test passed!")
    
    def test_create_subject(self):
        """Test creating a subject"""
        from src.database.db import get_db_context
        from src.database.models import Subject
        
        with get_db_context() as db:
            subject = Subject(code="M", name="Matematik")
            db.add(subject)
            db.flush()
            
            # Query back
            result = db.query(Subject).filter_by(code="M").first()
            assert result is not None
            assert result.name == "Matematik"
        
        print("✅ Create subject test passed!")
    
    def test_chunk_with_images(self):
        """Test chunk-image relationship"""
        from src.database.db import get_db_context
        from src.database.models import BookChunk, TextbookImage
        
        with get_db_context() as db:
            # Create chunk
            chunk = BookChunk(
                id="chunk-001",
                content="Test",
                chunk_type="concept",
                hierarchy_path="test",
                page_range="1-1"
            )
            db.add(chunk)
            db.flush()
            
            # Create image linked to chunk
            image = TextbookImage(
                id="img-001",
                chunk_id="chunk-001",
                width=100,
                height=100,
                page_number=1
            )
            db.add(image)
            db.flush()
            
            # Query relationship
            result = db.query(BookChunk).filter_by(id="chunk-001").first()
            assert len(result.images) == 1
            assert result.images[0].id == "img-001"
        
        print("✅ Chunk-image relationship test passed!")


class TestImportFunctions:
    """Tests for import functions"""
    
    def test_import_chunks_function_exists(self):
        """Test import function exists"""
        from src.database.import_chunks import import_semantic_chunks
        assert callable(import_semantic_chunks)
        print("✅ Import function exists test passed!")
    
    def test_import_images_function_exists(self):
        """Test import images function exists"""
        from src.database.import_chunks import import_extracted_images
        assert callable(import_extracted_images)
        print("✅ Import images function exists test passed!")


if __name__ == "__main__":
    # Run model tests (no DB needed)
    test_models = TestDatabaseModels()
    test_models.test_subject_model()
    test_models.test_kazanim_model()
    test_models.test_book_chunk_model()
    test_models.test_textbook_image_model()
    
    # Run import function tests
    test_imports = TestImportFunctions()
    test_imports.test_import_chunks_function_exists()
    test_imports.test_import_images_function_exists()
    
    print("\n✅ All Phase 3 basic tests passed!")
    print("Run 'pytest tests/test_database.py -v' for full database tests")
