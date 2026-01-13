"""
Layout Analyzer for MEB Textbook PDFs

Uses Azure Document Intelligence to analyze document layout
and classify elements (titles, paragraphs, sidebars, figures).
"""
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


class ElementType(Enum):
    """Document element types for MEB textbooks"""
    CHAPTER_TITLE = "chapter_title"
    SECTION_TITLE = "section_title"
    SUBSECTION_TITLE = "subsection_title"
    BODY_TEXT = "body_text"
    INFO_BOX = "info_box"
    EXAMPLE_BOX = "example_box"
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    SIDEBAR = "sidebar"      # Side column - MUST be separated!
    EXERCISE = "exercise"


@dataclass
class LayoutElement:
    """A single layout element from document analysis"""
    element_type: ElementType
    content: str
    page_number: int
    bounding_box: list
    confidence: float
    is_sidebar: bool = False  # Sidebar detection flag


class LayoutAnalyzer:
    """
    Analyzes document layout using Azure Document Intelligence.
    
    Key features:
    - Markdown output format for LaTeX math support
    - Sidebar detection based on page position
    - Element type classification
    """
    
    # Keywords that indicate info boxes
    INFO_BOX_KEYWORDS = [
        "Biliyor musunuz", "Dikkat", "Hatırlatma", "Not", "Uyarı",
        "Bilgi", "İpucu", "Örnek", "Etkinlik"
    ]
    
    # Page margin ratio for sidebar detection (20% on each side)
    SIDEBAR_MARGIN_RATIO = 0.20
    
    async def analyze_document(
        self,
        client: DocumentIntelligenceClient,
        pdf_bytes: bytes,
        max_retries: int = 5,
        initial_delay: float = 60.0
    ) -> AnalyzeResult:
        """
        Analyze document layout with Azure Document Intelligence.

        CRITICAL: Uses output_content_format="markdown" for LaTeX formula support!

        Implements retry with exponential backoff for transient failures (timeouts).
        Large files (>30MB) get MUCH longer timeouts to prevent Azure DI timeouts.

        Args:
            client: DocumentIntelligenceClient instance
            pdf_bytes: PDF file content as bytes
            max_retries: Maximum number of retry attempts (default: 5)
            initial_delay: Initial delay between retries in seconds (default: 60)
        """
        last_error = None
        file_size_mb = len(pdf_bytes) / (1024 * 1024)

        # Aggressive timeout settings based on file size
        # Azure Document Intelligence can take VERY long for large PDFs
        if file_size_mb > 30:
            # For files >30MB, use much longer timeouts
            max_retries = 8  # More retries
            initial_delay = 180.0  # Start with 3 minutes between retries
            poller_timeout = 5400  # 90 minutes for polling
            logger.info(f"⚠️ Large file detected ({file_size_mb:.0f}MB) - using EXTENDED timeouts:")
            logger.info(f"   • {max_retries} retry attempts")
            logger.info(f"   • {initial_delay}s initial delay between retries")
            logger.info(f"   • {poller_timeout}s ({poller_timeout/60:.0f}min) poller timeout")
            print(f"      ⚠️ Büyük dosya ({file_size_mb:.0f}MB) - uzatılmış timeout kullanılıyor")
        else:
            poller_timeout = 2700  # 45 minutes for smaller files

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # Exponential backoff with higher cap for large files
                    max_delay = 900 if file_size_mb > 30 else 600  # 15 min vs 10 min
                    delay = min(initial_delay * (1.5 ** (attempt - 1)), max_delay)
                    logger.info(f"⏳ Retry attempt {attempt}/{max_retries} after {delay:.0f}s delay...")
                    print(f"      ⏳ Tekrar deneme {attempt}/{max_retries} - {delay:.0f}s bekleniyor...")
                    await asyncio.sleep(delay)

                # Run the synchronous SDK call in a thread pool to avoid blocking
                loop = asyncio.get_event_loop()

                logger.info(f"Starting Azure Document Intelligence analysis (attempt {attempt + 1})...")
                poller = await loop.run_in_executor(
                    None,
                    lambda: client.begin_analyze_document(
                        "prebuilt-layout",
                        AnalyzeDocumentRequest(bytes_source=pdf_bytes),
                        output_content_format="markdown"  # CRITICAL for math formulas!
                    )
                )

                # Wait for result with appropriate timeout
                logger.info(f"Waiting for analysis result (timeout: {poller_timeout}s = {poller_timeout/60:.1f}min)...")
                result = await loop.run_in_executor(
                    None,
                    lambda: poller.result(timeout=poller_timeout)
                )

                logger.info(f"✅ Analysis completed successfully!")
                return result

            except HttpResponseError as e:
                last_error = e
                error_code = getattr(e, 'error', {})
                if hasattr(error_code, 'code'):
                    error_code = error_code.code
                else:
                    error_code = str(e)

                # Retry on timeout or transient errors
                if "Timeout" in str(error_code) or "timeout" in str(e).lower() or "429" in str(e) or "503" in str(e):
                    logger.warning(f"⚠️ Timeout/Throttle on attempt {attempt + 1}/{max_retries + 1}: {e}")
                    print(f"      ⚠️ Timeout/Throttle deneme {attempt + 1}/{max_retries + 1}")
                    if attempt < max_retries:
                        # For very large files, suggest splitting
                        if file_size_mb > 40 and attempt == max_retries - 1:
                            print(f"      💡 İPUCU: Bu dosya çok büyük ({file_size_mb:.0f}MB). PDF'i bölmek gerekebilir.")
                            logger.warning(f"File might be too large for Azure DI. Consider splitting.")
                        continue
                # Don't retry on non-transient errors
                logger.error(f"Non-retryable error: {e}")
                raise

            except (ServiceRequestError, ConnectionError, TimeoutError) as e:
                last_error = e
                logger.warning(f"⚠️ Connection error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                print(f"      ⚠️ Bağlantı hatası deneme {attempt + 1}/{max_retries + 1}")
                if attempt < max_retries:
                    continue
                raise

        # If we exhausted all retries
        logger.error(f"❌ Failed to analyze document after {max_retries + 1} attempts")
        raise last_error or Exception("Failed to analyze document after all retries")
    
    def classify_elements(self, result: AnalyzeResult) -> List[LayoutElement]:
        """
        Classify document elements by type and detect sidebars.
        
        Returns:
            List of LayoutElement with detected types and sidebar flags
        """
        elements = []
        
        if not result.pages:
            return elements
        
        for page in result.pages:
            page_width = page.width or 612  # Default A4 width in points
            
            # Process paragraphs
            if result.paragraphs:
                for paragraph in result.paragraphs:
                    if not self._is_on_page(paragraph, page.page_number):
                        continue
                    
                    bbox = []
                    if paragraph.bounding_regions:
                        regions = paragraph.bounding_regions
                        if regions and regions[0].polygon:
                            bbox = regions[0].polygon
                    
                    # Detect sidebar based on position
                    is_sidebar = self._is_in_sidebar_region(bbox, page_width)
                    
                    # Classify element type
                    element_type = self._detect_element_type(paragraph, is_sidebar)
                    
                    elements.append(LayoutElement(
                        element_type=element_type,
                        content=paragraph.content or "",
                        page_number=page.page_number,
                        bounding_box=bbox,
                        confidence=0.9,
                        is_sidebar=is_sidebar
                    ))
            
            # Process figures
            if result.figures:
                for figure in result.figures:
                    if not figure.bounding_regions:
                        continue
                    
                    region = figure.bounding_regions[0]
                    if region.page_number != page.page_number:
                        continue
                    
                    elements.append(LayoutElement(
                        element_type=ElementType.FIGURE,
                        content=figure.caption.content if figure.caption else "",
                        page_number=page.page_number,
                        bounding_box=region.polygon or [],
                        confidence=0.9,
                        is_sidebar=False
                    ))
            
            # Process tables
            if result.tables:
                for table in result.tables:
                    if not table.bounding_regions:
                        continue
                    
                    region = table.bounding_regions[0]
                    if region.page_number != page.page_number:
                        continue
                    
                    # Extract table content as text
                    table_content = self._extract_table_content(table)
                    
                    elements.append(LayoutElement(
                        element_type=ElementType.TABLE,
                        content=table_content,
                        page_number=page.page_number,
                        bounding_box=region.polygon or [],
                        confidence=0.9,
                        is_sidebar=False
                    ))
        
        return elements
    
    def _is_on_page(self, paragraph, page_number: int) -> bool:
        """Check if paragraph is on the specified page"""
        if not paragraph.bounding_regions:
            return False
        return any(r.page_number == page_number for r in paragraph.bounding_regions)
    
    def _is_in_sidebar_region(self, bbox: list, page_width: float) -> bool:
        """
        Detect if element is in sidebar region based on x-coordinates.
        
        Sidebar = element completely within left or right 20% margin.
        """
        if not bbox or len(bbox) < 4:
            return False
        
        # Extract x coordinates (polygon format: [x1,y1, x2,y2, ...])
        x_coords = [bbox[i] for i in range(0, len(bbox), 2)]
        min_x = min(x_coords)
        max_x = max(x_coords)
        
        # Calculate margin thresholds
        left_margin = page_width * self.SIDEBAR_MARGIN_RATIO
        right_margin = page_width * (1 - self.SIDEBAR_MARGIN_RATIO)
        
        # Element is sidebar if entirely in margin area
        return max_x < left_margin or min_x > right_margin
    
    def _detect_element_type(self, paragraph, is_sidebar: bool) -> ElementType:
        """
        Detect element type based on role and content.
        """
        if is_sidebar:
            return ElementType.SIDEBAR
        
        text = paragraph.content or ""
        role = getattr(paragraph, 'role', None)
        
        # Check paragraph role
        if role == "title":
            return ElementType.CHAPTER_TITLE
        if role == "sectionHeading":
            return ElementType.SECTION_TITLE
        
        # Check for info box keywords
        for keyword in self.INFO_BOX_KEYWORDS:
            if keyword.lower() in text.lower():
                return ElementType.INFO_BOX
        
        # Check for exercise patterns
        if self._is_exercise(text):
            return ElementType.EXERCISE
        
        # Check for example patterns
        if self._is_example(text):
            return ElementType.EXAMPLE_BOX
        
        return ElementType.BODY_TEXT
    
    def _is_exercise(self, text: str) -> bool:
        """Detect if text is an exercise"""
        patterns = [
            r'^Soru\s*\d+',
            r'^Alıştırma\s*\d+',
            r'^\d+\.\s*Soru',
            r'^Etkinlik\s*\d+'
        ]
        return any(re.match(p, text, re.IGNORECASE) for p in patterns)
    
    def _is_example(self, text: str) -> bool:
        """Detect if text is an example"""
        patterns = [
            r'^Örnek\s*\d*',
            r'^ÖRNEK',
            r'^Çözümlü\s*Örnek'
        ]
        return any(re.match(p, text, re.IGNORECASE) for p in patterns)
    
    def _extract_table_content(self, table) -> str:
        """Extract table content as formatted text"""
        if not table.cells:
            return ""
        
        rows = {}
        for cell in table.cells:
            row_idx = cell.row_index
            if row_idx not in rows:
                rows[row_idx] = []
            rows[row_idx].append((cell.column_index, cell.content or ""))
        
        # Build table text
        lines = []
        for row_idx in sorted(rows.keys()):
            cells = sorted(rows[row_idx], key=lambda x: x[0])
            line = " | ".join(c[1] for c in cells)
            lines.append(line)
        
        return "\n".join(lines)
