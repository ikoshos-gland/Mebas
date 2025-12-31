"""
Hierarchy Builder for MEB Textbook PDFs

Constructs document hierarchy from layout elements
and provides navigation utilities.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class HierarchyNode:
    """A node in the document hierarchy tree"""
    id: str
    title: str
    level: str  # "chapter", "section", "subsection"
    page_start: int
    page_end: Optional[int] = None
    children: List["HierarchyNode"] = field(default_factory=list)
    content_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class HierarchyBuilder:
    """
    Builds document hierarchy from layout elements.
    
    Creates a tree structure:
    - Chapter (Ünite)
      - Section (Konu)
        - Subsection (Alt Başlık)
    """
    
    def __init__(self):
        self.root = HierarchyNode(
            id="root",
            title="Document",
            level="root",
            page_start=1
        )
        self._current_chapter: Optional[HierarchyNode] = None
        self._current_section: Optional[HierarchyNode] = None
        self._node_counter = 0
    
    def build_from_elements(self, elements: list) -> HierarchyNode:
        """
        Build hierarchy tree from layout elements.
        
        Args:
            elements: List of LayoutElement objects
            
        Returns:
            Root HierarchyNode containing the full document tree
        """
        for elem in elements:
            elem_type = elem.element_type.value
            
            if elem_type == "chapter_title":
                self._add_chapter(elem.content, elem.page_number)
            elif elem_type == "section_title":
                self._add_section(elem.content, elem.page_number)
            elif elem_type == "subsection_title":
                self._add_subsection(elem.content, elem.page_number)
        
        # Update page_end for all nodes
        self._finalize_page_ranges()
        
        return self.root
    
    def _add_chapter(self, title: str, page: int) -> None:
        """Add a new chapter node"""
        self._node_counter += 1
        chapter = HierarchyNode(
            id=f"chapter_{self._node_counter}",
            title=title[:100],  # Truncate long titles
            level="chapter",
            page_start=page
        )
        self.root.children.append(chapter)
        self._current_chapter = chapter
        self._current_section = None
    
    def _add_section(self, title: str, page: int) -> None:
        """Add a new section node under current chapter"""
        self._node_counter += 1
        section = HierarchyNode(
            id=f"section_{self._node_counter}",
            title=title[:100],
            level="section",
            page_start=page
        )
        
        # Add to current chapter or root if no chapter
        if self._current_chapter:
            self._current_chapter.children.append(section)
        else:
            self.root.children.append(section)
        
        self._current_section = section
    
    def _add_subsection(self, title: str, page: int) -> None:
        """Add a new subsection node under current section"""
        self._node_counter += 1
        subsection = HierarchyNode(
            id=f"subsection_{self._node_counter}",
            title=title[:100],
            level="subsection",
            page_start=page
        )
        
        # Add to current section, chapter, or root
        if self._current_section:
            self._current_section.children.append(subsection)
        elif self._current_chapter:
            self._current_chapter.children.append(subsection)
        else:
            self.root.children.append(subsection)
    
    def _finalize_page_ranges(self) -> None:
        """Calculate page_end for all nodes based on next sibling's page_start"""
        self._finalize_children(self.root.children)
    
    def _finalize_children(self, children: List[HierarchyNode]) -> None:
        """Recursively finalize page ranges for children"""
        for i, node in enumerate(children):
            # Set page_end based on next sibling
            if i + 1 < len(children):
                node.page_end = children[i + 1].page_start - 1
            else:
                node.page_end = node.page_start  # Last node
            
            # Recurse to children
            if node.children:
                self._finalize_children(node.children)
    
    def get_path(self, page_number: int) -> str:
        """
        Get hierarchy path for a given page number.
        
        Args:
            page_number: Page number to find path for
            
        Returns:
            Path string like "Ünite 1/Konu 2/Alt Başlık 3"
        """
        path_parts = []
        self._find_path(self.root.children, page_number, path_parts)
        return "/".join(path_parts) or "root"
    
    def _find_path(
        self, 
        children: List[HierarchyNode], 
        page: int, 
        path: List[str]
    ) -> bool:
        """Recursively find path to page"""
        for node in children:
            start = node.page_start
            end = node.page_end or node.page_start
            
            if start <= page <= end:
                path.append(node.title)
                if node.children:
                    self._find_path(node.children, page, path)
                return True
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert hierarchy to dictionary for JSON serialization"""
        return self._node_to_dict(self.root)
    
    def _node_to_dict(self, node: HierarchyNode) -> Dict:
        """Convert single node to dictionary"""
        return {
            "id": node.id,
            "title": node.title,
            "level": node.level,
            "page_start": node.page_start,
            "page_end": node.page_end,
            "children": [self._node_to_dict(c) for c in node.children]
        }
    
    def get_flat_list(self) -> List[Dict]:
        """
        Get flat list of all nodes with their paths.
        
        Useful for database import.
        """
        nodes = []
        self._flatten_node(self.root, [], nodes)
        return nodes
    
    def _flatten_node(
        self, 
        node: HierarchyNode, 
        path: List[str], 
        output: List[Dict]
    ) -> None:
        """Recursively flatten nodes"""
        if node.level != "root":
            current_path = path + [node.title]
            output.append({
                "id": node.id,
                "title": node.title,
                "level": node.level,
                "path": "/".join(current_path),
                "page_start": node.page_start,
                "page_end": node.page_end
            })
        else:
            current_path = []
        
        for child in node.children:
            self._flatten_node(child, current_path, output)
    
    def find_node_by_title(self, title: str) -> Optional[HierarchyNode]:
        """Find node by title (case-insensitive partial match)"""
        return self._search_node(self.root, title.lower())
    
    def _search_node(
        self, 
        node: HierarchyNode, 
        search_term: str
    ) -> Optional[HierarchyNode]:
        """Recursively search for node by title"""
        if search_term in node.title.lower():
            return node
        
        for child in node.children:
            result = self._search_node(child, search_term)
            if result:
                return result
        
        return None
