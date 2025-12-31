"""
Tests for PDF Processing Module (Phase 2)
"""
import pytest
from pathlib import Path


class TestLayoutAnalyzer:
    """Tests for LayoutAnalyzer class"""
    
    def test_element_type_enum(self):
        """Test ElementType enum values exist"""
        from src.document_processing.layout_analyzer import ElementType
        
        assert ElementType.CHAPTER_TITLE.value == "chapter_title"
        assert ElementType.SECTION_TITLE.value == "section_title"
        assert ElementType.BODY_TEXT.value == "body_text"
        assert ElementType.SIDEBAR.value == "sidebar"
        assert ElementType.INFO_BOX.value == "info_box"
        assert ElementType.FIGURE.value == "figure"
        assert ElementType.TABLE.value == "table"
        
        print("✅ ElementType enum test passed!")
    
    def test_layout_element_dataclass(self):
        """Test LayoutElement dataclass"""
        from src.document_processing.layout_analyzer import LayoutElement, ElementType
        
        element = LayoutElement(
            element_type=ElementType.BODY_TEXT,
            content="Test content",
            page_number=1,
            bounding_box=[0, 0, 100, 0, 100, 100, 0, 100],
            confidence=0.9,
            is_sidebar=False
        )
        
        assert element.content == "Test content"
        assert element.page_number == 1
        assert element.is_sidebar is False
        
        print("✅ LayoutElement dataclass test passed!")
    
    def test_sidebar_detection(self):
        """Test sidebar region detection"""
        from src.document_processing.layout_analyzer import LayoutAnalyzer
        
        analyzer = LayoutAnalyzer()
        page_width = 612  # Standard A4 width in points
        
        # Left sidebar (10% of page)
        left_sidebar_bbox = [0, 0, 50, 0, 50, 100, 0, 100]
        assert analyzer._is_in_sidebar_region(left_sidebar_bbox, page_width) is True
        
        # Right sidebar (90% of page)
        right_sidebar_bbox = [550, 0, 612, 0, 612, 100, 550, 100]
        assert analyzer._is_in_sidebar_region(right_sidebar_bbox, page_width) is True
        
        # Main content (center)
        center_bbox = [200, 0, 400, 0, 400, 100, 200, 100]
        assert analyzer._is_in_sidebar_region(center_bbox, page_width) is False
        
        print("✅ Sidebar detection test passed!")


class TestImageExtractor:
    """Tests for ImageExtractor class"""
    
    def test_size_filter(self):
        """Test image size filtering"""
        from src.document_processing.image_extractor import ImageExtractor
        
        extractor = ImageExtractor()
        
        # Too small - should fail
        assert extractor._passes_size_filter(50, 50) is False
        
        # Valid size - should pass
        assert extractor._passes_size_filter(200, 200) is True
        
        # Too thin (aspect ratio > 10) - should fail
        assert extractor._passes_size_filter(1000, 50) is False
        
        print("✅ Image size filter test passed!")
    
    def test_extracted_image_dataclass(self):
        """Test ExtractedImage dataclass"""
        from src.document_processing.image_extractor import ExtractedImage
        
        image = ExtractedImage(
            image_id="test123",
            image_bytes=b"fake_image_data",
            image_path=None,
            page_number=1,
            bounding_box=[0, 0, 100, 100],
            width=200,
            height=200
        )
        
        assert image.image_id == "test123"
        assert image.width == 200
        assert image.caption is None  # Optional field
        
        print("✅ ExtractedImage dataclass test passed!")


class TestSemanticChunker:
    """Tests for SemanticChunker class"""
    
    def test_chunk_creation(self):
        """Test basic chunk creation"""
        from src.document_processing.semantic_chunker import SemanticChunker, SemanticChunk
        from src.document_processing.layout_analyzer import LayoutElement, ElementType
        
        chunker = SemanticChunker()
        
        # Create test elements
        elements = [
            LayoutElement(
                element_type=ElementType.SECTION_TITLE,
                content="Test Section",
                page_number=1,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=False
            ),
            LayoutElement(
                element_type=ElementType.BODY_TEXT,
                content="This is test content for the section.",
                page_number=1,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=False
            ),
            LayoutElement(
                element_type=ElementType.SIDEBAR,
                content="Sidebar note",
                page_number=1,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=True
            )
        ]
        
        chunks = chunker.chunk_document(elements)
        
        # Should have at least 2 chunks (main + sidebar)
        assert len(chunks) >= 2
        
        # Check sidebar chunk exists
        sidebar_chunks = [c for c in chunks if c.is_sidebar_content]
        assert len(sidebar_chunks) == 1
        assert "[EK BİLGİ]" in sidebar_chunks[0].content
        
        print("✅ Semantic chunking test passed!")


class TestHierarchyBuilder:
    """Tests for HierarchyBuilder class"""
    
    def test_hierarchy_creation(self):
        """Test hierarchy tree creation"""
        from src.document_processing.hierarchy_builder import HierarchyBuilder
        from src.document_processing.layout_analyzer import LayoutElement, ElementType
        
        builder = HierarchyBuilder()
        
        elements = [
            LayoutElement(
                element_type=ElementType.CHAPTER_TITLE,
                content="Ünite 1: Sayılar",
                page_number=1,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=False
            ),
            LayoutElement(
                element_type=ElementType.SECTION_TITLE,
                content="Doğal Sayılar",
                page_number=2,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=False
            )
        ]
        
        root = builder.build_from_elements(elements)
        
        # Root should have one chapter
        assert len(root.children) == 1
        assert "Sayılar" in root.children[0].title
        
        # Chapter should have one section
        assert len(root.children[0].children) == 1
        assert "Doğal Sayılar" in root.children[0].children[0].title
        
        print("✅ Hierarchy builder test passed!")
    
    def test_path_lookup(self):
        """Test page to path lookup"""
        from src.document_processing.hierarchy_builder import HierarchyBuilder
        from src.document_processing.layout_analyzer import LayoutElement, ElementType
        
        builder = HierarchyBuilder()
        
        elements = [
            LayoutElement(
                element_type=ElementType.CHAPTER_TITLE,
                content="Chapter 1",
                page_number=1,
                bounding_box=[],
                confidence=0.9,
                is_sidebar=False
            )
        ]
        
        builder.build_from_elements(elements)
        path = builder.get_path(1)
        
        assert "Chapter 1" in path
        
        print("✅ Path lookup test passed!")


if __name__ == "__main__":
    # Run tests manually
    test_layout = TestLayoutAnalyzer()
    test_layout.test_element_type_enum()
    test_layout.test_layout_element_dataclass()
    test_layout.test_sidebar_detection()
    
    test_image = TestImageExtractor()
    test_image.test_size_filter()
    test_image.test_extracted_image_dataclass()
    
    test_chunker = TestSemanticChunker()
    test_chunker.test_chunk_creation()
    
    test_hierarchy = TestHierarchyBuilder()
    test_hierarchy.test_hierarchy_creation()
    test_hierarchy.test_path_lookup()
    
    print("\n✅ All Phase 2 tests passed!")
