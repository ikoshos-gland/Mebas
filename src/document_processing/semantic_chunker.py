"""
Semantic Chunker for MEB Textbook PDFs

Creates semantic chunks from layout elements while
preserving document hierarchy and separating sidebars.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid

from src.document_processing.layout_analyzer import LayoutElement, ElementType


@dataclass
class SemanticChunk:
    """A semantic chunk of textbook content"""
    chunk_id: str
    content: str
    chunk_type: str  # "concept", "example", "info", "visual", "sidebar"
    hierarchy_path: str  # "Chapter1/Section2/Subsection3"
    page_range: tuple  # (start_page, end_page)
    related_figures: List[str] = field(default_factory=list)
    related_tables: List[dict] = field(default_factory=list)
    is_sidebar_content: bool = False
    metadata: Dict = field(default_factory=dict)


class SemanticChunker:
    """
    Creates semantic chunks from layout elements.
    
    Key features:
    - Preserves document hierarchy (Chapter > Section > Subsection)
    - Separates sidebar content into dedicated chunks
    - Tags content with semantic labels [BİLGİ KUTUSU], [ÖRNEK], etc.
    """
    
    MAX_CHUNK_SIZE = 1500  # Approximate token limit
    MIN_CHUNK_SIZE = 200
    
    def chunk_document(self, elements: List[LayoutElement]) -> List[SemanticChunk]:
        """
        Create semantic chunks from layout elements.
        
        Separates:
        - Main content (preserves hierarchy)
        - Sidebar content (separate chunks)
        
        Args:
            elements: List of LayoutElement from LayoutAnalyzer
            
        Returns:
            List of SemanticChunk objects
        """
        # Separate main content and sidebars
        main_elements = [e for e in elements if not e.is_sidebar]
        sidebar_elements = [e for e in elements if e.is_sidebar]
        
        chunks = []
        
        # Chunk main content
        main_chunks = self._chunk_main_content(main_elements)
        chunks.extend(main_chunks)
        
        # Create separate chunks for sidebars
        sidebar_chunks = self._chunk_sidebars(sidebar_elements)
        chunks.extend(sidebar_chunks)
        
        return chunks
    
    def _chunk_main_content(self, elements: List[LayoutElement]) -> List[SemanticChunk]:
        """
        Chunk main content preserving hierarchy.
        
        Breaks on section changes and respects max chunk size.
        """
        chunks = []
        current_hierarchy = {"chapter": "", "section": "", "subsection": ""}
        current_group = []
        
        for elem in elements:
            # New section starts a new chunk
            if elem.element_type.value in ["section_title", "chapter_title"]:
                if current_group:
                    chunk = self._create_chunk(current_group, current_hierarchy, "concept")
                    chunks.append(chunk)
                current_group = [elem]
                current_hierarchy = self._update_hierarchy(elem, current_hierarchy)
            else:
                current_group.append(elem)
                
                # Check if group is getting too large
                content_length = sum(len(e.content) for e in current_group)
                if content_length > self.MAX_CHUNK_SIZE:
                    chunk = self._create_chunk(current_group[:-1], current_hierarchy, "concept")
                    chunks.append(chunk)
                    current_group = [elem]
        
        # Don't forget the last group
        if current_group:
            chunks.append(self._create_chunk(current_group, current_hierarchy, "concept"))
        
        return chunks
    
    def _chunk_sidebars(self, elements: List[LayoutElement]) -> List[SemanticChunk]:
        """
        Create separate chunks for sidebar content.
        
        Each sidebar element becomes its own chunk tagged as [EK BİLGİ].
        """
        chunks = []
        
        for elem in elements:
            chunk = SemanticChunk(
                chunk_id=self._generate_id(),
                content=f"[EK BİLGİ]\n{elem.content}\n[/EK BİLGİ]",
                chunk_type="sidebar",
                hierarchy_path=f"page_{elem.page_number}/sidebar",
                page_range=(elem.page_number, elem.page_number),
                is_sidebar_content=True,
                metadata={"source": "sidebar", "page": elem.page_number}
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(
        self, 
        group: List[LayoutElement], 
        hierarchy: Dict, 
        chunk_type: str
    ) -> SemanticChunk:
        """
        Create a chunk from a group of elements.
        
        Applies semantic tags:
        - [BİLGİ KUTUSU] for info boxes
        - [ÖRNEK] for examples
        - [ŞEKİL: ...] for figures
        """
        content_parts = []
        figures = []
        tables = []
        
        for elem in group:
            elem_type = elem.element_type.value
            
            if elem_type == "info_box":
                content_parts.append(f"\n[BİLGİ KUTUSU]\n{elem.content}\n[/BİLGİ KUTUSU]\n")
            elif elem_type == "example_box":
                content_parts.append(f"\n[ÖRNEK]\n{elem.content}\n[/ÖRNEK]\n")
            elif elem_type == "figure":
                figures.append(elem.content)
                content_parts.append(f"[ŞEKİL: {elem.content}]")
            elif elem_type == "table":
                tables.append({"content": elem.content, "page": elem.page_number})
                content_parts.append(f"\n[TABLO]\n{elem.content}\n[/TABLO]\n")
            elif elem_type == "exercise":
                content_parts.append(f"\n[ALIŞTIRMA]\n{elem.content}\n[/ALIŞTIRMA]\n")
            elif elem_type in ["chapter_title", "section_title", "subsection_title"]:
                content_parts.append(f"\n## {elem.content}\n")
            else:
                content_parts.append(elem.content)
        
        # Build hierarchy path
        hierarchy_path = "/".join(filter(None, [
            hierarchy.get("chapter", ""),
            hierarchy.get("section", ""),
            hierarchy.get("subsection", "")
        ]))
        
        if not hierarchy_path:
            hierarchy_path = "root"
        
        # Get page range
        page_range = (
            group[0].page_number if group else 0,
            group[-1].page_number if group else 0
        )
        
        return SemanticChunk(
            chunk_id=self._generate_id(),
            content="\n".join(content_parts),
            chunk_type=chunk_type,
            hierarchy_path=hierarchy_path,
            page_range=page_range,
            related_figures=figures,
            related_tables=tables,
            metadata={"element_count": len(group)}
        )
    
    def _generate_id(self) -> str:
        """Generate unique chunk ID"""
        return str(uuid.uuid4())[:8]
    
    def _update_hierarchy(self, elem: LayoutElement, current: Dict) -> Dict:
        """Update hierarchy based on title element"""
        new = current.copy()
        elem_type = elem.element_type.value
        
        if elem_type == "chapter_title":
            new["chapter"] = elem.content[:50]  # Truncate long titles
            new["section"] = ""
            new["subsection"] = ""
        elif elem_type == "section_title":
            new["section"] = elem.content[:50]
            new["subsection"] = ""
        elif elem_type == "subsection_title":
            new["subsection"] = elem.content[:50]
        
        return new
    
    def merge_small_chunks(self, chunks: List[SemanticChunk]) -> List[SemanticChunk]:
        """
        Merge chunks that are too small.
        
        Combines consecutive chunks if their combined size is under MAX_CHUNK_SIZE.
        """
        if not chunks:
            return chunks
        
        merged = []
        current = chunks[0]
        
        for next_chunk in chunks[1:]:
            combined_length = len(current.content) + len(next_chunk.content)
            
            # Merge if same type and small enough
            if (current.chunk_type == next_chunk.chunk_type 
                and combined_length < self.MAX_CHUNK_SIZE
                and len(current.content) < self.MIN_CHUNK_SIZE):
                
                # Merge chunks
                current = SemanticChunk(
                    chunk_id=current.chunk_id,
                    content=current.content + "\n\n" + next_chunk.content,
                    chunk_type=current.chunk_type,
                    hierarchy_path=current.hierarchy_path,
                    page_range=(current.page_range[0], next_chunk.page_range[1]),
                    related_figures=current.related_figures + next_chunk.related_figures,
                    related_tables=current.related_tables + next_chunk.related_tables,
                    is_sidebar_content=current.is_sidebar_content,
                    metadata={
                        "element_count": (
                            current.metadata.get("element_count", 0) + 
                            next_chunk.metadata.get("element_count", 0)
                        ),
                        "merged": True
                    }
                )
            else:
                merged.append(current)
                current = next_chunk
        
        merged.append(current)
        return merged
