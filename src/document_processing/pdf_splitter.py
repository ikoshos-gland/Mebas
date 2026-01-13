"""
PDF Splitter for Large Files

Splits large PDF files into smaller chunks to avoid Azure Document Intelligence timeouts.
Each chunk is processed separately and results are merged.
"""
import io
from pathlib import Path
from typing import List, Tuple
import logging

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

logger = logging.getLogger(__name__)


class PDFSplitter:
    """Split large PDFs into smaller chunks for processing."""

    # Split PDFs larger than this size (in MB)
    MAX_CHUNK_SIZE_MB = 40

    # Target pages per chunk (roughly 20-30 pages = ~20-30MB for typical textbooks)
    PAGES_PER_CHUNK = 25

    def __init__(self, max_chunk_size_mb: int = MAX_CHUNK_SIZE_MB, pages_per_chunk: int = PAGES_PER_CHUNK):
        """
        Initialize PDF splitter.

        Args:
            max_chunk_size_mb: Maximum chunk size in MB before splitting
            pages_per_chunk: Target number of pages per chunk
        """
        if not HAS_PYPDF2:
            raise ImportError("PyPDF2 is required for PDF splitting. Install with: pip install PyPDF2")

        self.max_chunk_size_mb = max_chunk_size_mb
        self.pages_per_chunk = pages_per_chunk

    def should_split(self, pdf_bytes: bytes) -> bool:
        """
        Check if PDF should be split based on size.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            True if PDF should be split, False otherwise
        """
        size_mb = len(pdf_bytes) / (1024 * 1024)
        return size_mb > self.max_chunk_size_mb

    def split_pdf(self, pdf_bytes: bytes) -> List[Tuple[bytes, int, int]]:
        """
        Split PDF into smaller chunks.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            List of tuples: (chunk_bytes, start_page, end_page)
            Page numbers are 1-indexed (e.g., first page = 1)
        """
        size_mb = len(pdf_bytes) / (1024 * 1024)

        if not self.should_split(pdf_bytes):
            logger.info(f"PDF size ({size_mb:.1f}MB) is below threshold, no splitting needed")
            return [(pdf_bytes, 1, self._get_page_count(pdf_bytes))]

        logger.info(f"Splitting large PDF ({size_mb:.1f}MB) into chunks...")

        try:
            # Read PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = len(pdf_reader.pages)

            logger.info(f"Total pages: {total_pages}, target pages per chunk: {self.pages_per_chunk}")

            chunks = []
            current_page = 0

            while current_page < total_pages:
                # Create a new PDF for this chunk
                pdf_writer = PyPDF2.PdfWriter()

                # Add pages to chunk
                start_page = current_page
                end_page = min(current_page + self.pages_per_chunk, total_pages)

                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])

                # Write chunk to bytes
                chunk_buffer = io.BytesIO()
                pdf_writer.write(chunk_buffer)
                chunk_bytes = chunk_buffer.getvalue()
                chunk_size_mb = len(chunk_bytes) / (1024 * 1024)

                # Convert to 1-indexed page numbers for user display
                chunks.append((chunk_bytes, start_page + 1, end_page))

                logger.info(f"  Chunk {len(chunks)}: pages {start_page + 1}-{end_page} ({chunk_size_mb:.1f}MB)")

                current_page = end_page

            logger.info(f"Split into {len(chunks)} chunks")
            return chunks

        except Exception as e:
            logger.error(f"Failed to split PDF: {e}")
            # If splitting fails, return original PDF as single chunk
            return [(pdf_bytes, 1, self._get_page_count(pdf_bytes))]

    def _get_page_count(self, pdf_bytes: bytes) -> int:
        """Get total page count from PDF bytes."""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            return len(pdf_reader.pages)
        except Exception:
            return 0

    @staticmethod
    def merge_analyze_results(chunk_results: List, page_offsets: List[int]):
        """
        Merge analysis results from multiple chunks.

        This adjusts page numbers in the results to account for chunk offsets.

        Args:
            chunk_results: List of AnalyzeResult objects from each chunk
            page_offsets: List of starting page numbers for each chunk (1-indexed)

        Returns:
            Merged AnalyzeResult with adjusted page numbers
        """
        if not chunk_results:
            return None

        if len(chunk_results) == 1:
            return chunk_results[0]

        # Use first result as base and merge others into it
        merged_result = chunk_results[0]

        # Merge content
        merged_content = []
        for i, result in enumerate(chunk_results):
            if result.content:
                merged_content.append(result.content)
        merged_result.content = "\n\n".join(merged_content)

        # Merge pages with adjusted page numbers
        all_pages = []
        for i, result in enumerate(chunk_results):
            offset = page_offsets[i] - 1  # Convert to 0-indexed offset
            if result.pages:
                for page in result.pages:
                    # Adjust page number
                    page.page_number += offset
                    all_pages.append(page)
        merged_result.pages = all_pages

        # Merge paragraphs with adjusted page numbers
        all_paragraphs = []
        for i, result in enumerate(chunk_results):
            offset = page_offsets[i] - 1
            if result.paragraphs:
                for para in result.paragraphs:
                    # Adjust bounding region page numbers
                    if para.bounding_regions:
                        for region in para.bounding_regions:
                            region.page_number += offset
                    all_paragraphs.append(para)
        merged_result.paragraphs = all_paragraphs

        # Merge figures with adjusted page numbers
        all_figures = []
        for i, result in enumerate(chunk_results):
            offset = page_offsets[i] - 1
            if result.figures:
                for figure in result.figures:
                    if figure.bounding_regions:
                        for region in figure.bounding_regions:
                            region.page_number += offset
                    all_figures.append(figure)
        merged_result.figures = all_figures

        # Merge tables with adjusted page numbers
        all_tables = []
        for i, result in enumerate(chunk_results):
            offset = page_offsets[i] - 1
            if result.tables:
                for table in result.tables:
                    if table.bounding_regions:
                        for region in table.bounding_regions:
                            region.page_number += offset
                    all_tables.append(table)
        merged_result.tables = all_tables

        return merged_result
