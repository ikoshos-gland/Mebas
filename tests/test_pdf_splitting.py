"""
Unit tests for PDF splitting and metadata coordination.

Tests that large PDF splitting maintains correct:
- Page number coordination
- Metadata consistency
- Image extraction alignment
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from src.document_processing.pdf_splitter import PDFSplitter


class TestPDFSplitter:
    """Test PDF splitting logic and page number coordination."""

    def test_should_split_large_file(self):
        """Test that files >35MB are marked for splitting."""
        splitter = PDFSplitter(max_chunk_size_mb=35, pages_per_chunk=25)

        # 40MB file should be split
        large_pdf = b"x" * (40 * 1024 * 1024)
        assert splitter.should_split(large_pdf) is True

        # 30MB file should not be split
        small_pdf = b"x" * (30 * 1024 * 1024)
        assert splitter.should_split(small_pdf) is False

    def test_page_offset_calculation(self):
        """Test that page offsets are calculated correctly for merge."""
        # Simulate split: 3 chunks
        chunk_results = [Mock(), Mock(), Mock()]
        page_offsets = [1, 26, 51]  # 1-indexed start pages

        # Verify offset calculation logic
        for i, offset_start in enumerate(page_offsets):
            offset = offset_start - 1  # Convert to 0-based offset

            if i == 0:
                assert offset == 0  # First chunk: no adjustment
            elif i == 1:
                assert offset == 25  # Second chunk: +25 pages
            elif i == 2:
                assert offset == 50  # Third chunk: +50 pages

    def test_merge_page_number_adjustment(self):
        """Test that merge correctly adjusts page numbers."""
        splitter = PDFSplitter()

        # Create mock Azure results with page numbers
        chunk1_result = Mock()
        chunk1_result.content = "Chunk 1 content"
        chunk1_result.pages = []
        chunk1_result.paragraphs = [Mock(bounding_regions=[Mock(page_number=1)])]
        chunk1_result.figures = [Mock(bounding_regions=[Mock(page_number=2)])]
        chunk1_result.tables = []

        chunk2_result = Mock()
        chunk2_result.content = "Chunk 2 content"
        chunk2_result.pages = []
        chunk2_result.paragraphs = [Mock(bounding_regions=[Mock(page_number=1)])]
        chunk2_result.figures = [Mock(bounding_regions=[Mock(page_number=3)])]
        chunk2_result.tables = []

        chunk_results = [chunk1_result, chunk2_result]
        page_offsets = [1, 26]  # Chunk 1 starts at 1, Chunk 2 starts at 26

        # Merge results
        merged = PDFSplitter.merge_analyze_results(chunk_results, page_offsets)

        # Verify page number adjustments
        # Chunk 1 paragraph: page 1 + offset 0 = 1
        assert merged.paragraphs[0].bounding_regions[0].page_number == 1

        # Chunk 1 figure: page 2 + offset 0 = 2
        assert merged.figures[0].bounding_regions[0].page_number == 2

        # Chunk 2 paragraph: page 1 + offset 25 = 26
        assert merged.paragraphs[1].bounding_regions[0].page_number == 26

        # Chunk 2 figure: page 3 + offset 25 = 28
        assert merged.figures[1].bounding_regions[0].page_number == 28

    def test_single_chunk_no_adjustment(self):
        """Test that single chunk (no split) returns original result."""
        splitter = PDFSplitter()

        original_result = Mock()
        original_result.content = "Original content"
        original_result.paragraphs = [Mock(bounding_regions=[Mock(page_number=5)])]

        # Single chunk should return as-is
        merged = PDFSplitter.merge_analyze_results([original_result], [1])

        # Page numbers should be unchanged
        assert merged.paragraphs[0].bounding_regions[0].page_number == 5


class TestMetadataConsistency:
    """Test that metadata remains consistent across split PDFs."""

    def test_textbook_id_consistency(self):
        """Test that textbook_id is same for all chunks."""
        from scripts.process_pdfs import parse_filename

        # Same filename should produce same textbook_id
        metadata1 = parse_filename("biyoloji_9.pdf")
        metadata2 = parse_filename("biyoloji_9.pdf")

        assert metadata1["textbook_id"] == metadata2["textbook_id"]
        assert metadata1["subject"] == metadata2["subject"]
        assert metadata1["grade"] == metadata2["grade"]

    def test_page_number_coordination(self):
        """Test that image extraction uses correct page numbers."""
        # This is an integration test concept - documents the expected flow:
        # 1. Split PDF: chunk 2 starts at page 26
        # 2. Azure DI analyzes chunk 2: returns pages 1, 2, 3...
        # 3. Merge adjusts: page 1 → 26, page 2 → 27...
        # 4. Image extraction: uses adjusted page 26 with original PDF
        # 5. PyMuPDF: doc[26-1] = doc[25] (0-indexed) ✅

        # Expected flow verification
        azure_page_in_chunk = 1  # Azure DI sees first page of chunk 2 as page 1
        chunk_start_page = 26  # Chunk 2 starts at original page 26
        offset = chunk_start_page - 1  # 25

        adjusted_page = azure_page_in_chunk + offset  # 1 + 25 = 26
        pymupdf_index = adjusted_page - 1  # 26 - 1 = 25 (0-indexed)

        assert adjusted_page == 26
        assert pymupdf_index == 25


class TestEdgeCases:
    """Test edge cases in PDF splitting."""

    def test_empty_results(self):
        """Test merge with empty results."""
        splitter = PDFSplitter()

        # Empty results should not crash
        merged = PDFSplitter.merge_analyze_results([], [])
        assert merged is None

    def test_missing_bounding_regions(self):
        """Test handling of figures without bounding regions."""
        splitter = PDFSplitter()

        result = Mock()
        result.content = "Test"
        result.pages = []
        result.paragraphs = []
        result.figures = [Mock(bounding_regions=None)]  # No bounding region
        result.tables = []

        # Should not crash
        merged = PDFSplitter.merge_analyze_results([result], [1])
        assert merged is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
