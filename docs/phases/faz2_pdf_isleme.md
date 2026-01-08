# Faz 2: PDF İşleme ve Semantic Chunking

## 🎯 Amaç
MEB ders kitaplarının karmaşık yapısını (yan kutular, görseller, hiyerarşi) koruyarak akıllı parçalama yapmak.

---

## ⚠️ KRİTİK: Bu Faz RAG Başarısının %80'ini Belirler!

**Veri kalitesi = RAG kalitesi**

---

## 🔧 Uygulama Adımları

### 2.1 Ek Bağımlılıklar (requirements.txt'e ekle)

```txt
# PDF Görsel Çıkarma için KRİTİK!
pymupdf>=1.23.0  # fitz olarak import edilir
```

### 2.2 Layout Analizi - Markdown Modu ile (KRİTİK!)

```python
# src/document_processing/layout_analyzer.py
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from dataclasses import dataclass
from enum import Enum
from typing import List
import re

class ElementType(Enum):
    CHAPTER_TITLE = "chapter_title"
    SECTION_TITLE = "section_title"
    SUBSECTION_TITLE = "subsection_title"
    BODY_TEXT = "body_text"
    INFO_BOX = "info_box"
    EXAMPLE_BOX = "example_box"
    FIGURE = "figure"
    FIGURE_CAPTION = "figure_caption"
    TABLE = "table"
    SIDEBAR = "sidebar"      # Yan sütun - AYRI TUTULMALI!
    EXERCISE = "exercise"

@dataclass
class LayoutElement:
    element_type: ElementType
    content: str
    page_number: int
    bounding_box: list
    confidence: float
    is_sidebar: bool = False  # Yan sütun kontrolü için

class LayoutAnalyzer:
    INFO_BOX_KEYWORDS = ["Biliyor musunuz", "Dikkat", "Hatırlatma", "Not", "Uyarı"]
    
    # Sayfa genişliğinin %20'si kenarlarda sidebar olarak kabul edilir
    SIDEBAR_MARGIN_RATIO = 0.20
    
    async def analyze_document(self, client: DocumentIntelligenceClient, 
                                pdf_bytes: bytes) -> AnalyzeResult:
        """
        KRİTİK: output_content_format="markdown" kullanılmalı!
        Bu sayede matematik formülleri LaTeX formatında gelir.
        """
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
            output_content_format="markdown"  # FORMÜLLER İÇİN KRİTİK!
        )
        return poller.result()
    
    def classify_elements(self, result: AnalyzeResult) -> List[LayoutElement]:
        """Elementleri tipine göre sınıflandır ve yan sütunları işaretle"""
        elements = []
        
        for page in result.pages:
            page_width = page.width
            
            for paragraph in result.paragraphs:
                if not self._is_on_page(paragraph, page.page_number):
                    continue
                
                bbox = paragraph.bounding_regions[0].polygon if paragraph.bounding_regions else []
                
                # Yan sütun kontrolü
                is_sidebar = self._is_in_sidebar_region(bbox, page_width)
                
                # Element tipini belirle
                element_type = self._detect_element_type(paragraph, is_sidebar)
                
                elements.append(LayoutElement(
                    element_type=element_type,
                    content=paragraph.content,
                    page_number=page.page_number,
                    bounding_box=bbox,
                    confidence=0.9,
                    is_sidebar=is_sidebar
                ))
        
        return elements
    
    def _is_in_sidebar_region(self, bbox: list, page_width: float) -> bool:
        """Koordinatlara göre yan sütun kontrolü"""
        if not bbox or len(bbox) < 4:
            return False
        
        # x koordinatlarını al
        x_coords = [bbox[i] for i in range(0, len(bbox), 2)]
        min_x = min(x_coords)
        max_x = max(x_coords)
        
        # Sağ veya sol kenarda mı?
        left_margin = page_width * self.SIDEBAR_MARGIN_RATIO
        right_margin = page_width * (1 - self.SIDEBAR_MARGIN_RATIO)
        
        # Element tamamen kenarda ise sidebar
        return max_x < left_margin or min_x > right_margin
    
    def _detect_element_type(self, paragraph, is_sidebar: bool) -> ElementType:
        """Paragraf tipini tespit et"""
        if is_sidebar:
            return ElementType.SIDEBAR
        
        text = paragraph.content
        
        if paragraph.role == "title":
            return ElementType.CHAPTER_TITLE
        if paragraph.role == "sectionHeading":
            return ElementType.SECTION_TITLE
        
        for keyword in self.INFO_BOX_KEYWORDS:
            if keyword.lower() in text.lower():
                return ElementType.INFO_BOX
        
        return ElementType.BODY_TEXT
```

### 2.3 Görsel Çıkarma - PyMuPDF ile (KRİTİK!)

```python
# src/document_processing/image_extractor.py
import fitz  # PyMuPDF
import base64
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ExtractedImage:
    image_id: str
    image_bytes: bytes
    image_path: Optional[Path]
    page_number: int
    bounding_box: list
    width: int
    height: int
    caption: Optional[str] = None
    image_type: Optional[str] = None
    related_text: str = ""
    hierarchy_path: str = ""

class ImageExtractor:
    """
    Azure koordinatlarını kullanarak PDF'ten görselleri keser.
    PyMuPDF (fitz) kullanır.
    """
    
    # Maliyet kontrolü için minimum boyutlar
    MIN_WIDTH = 100   # piksel
    MIN_HEIGHT = 100  # piksel
    MAX_ASPECT_RATIO = 10  # Çok ince şeritleri atla (kenar süsleri)
    
    def __init__(self, vision_client, output_dir: Path):
        self.vision_client = vision_client
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_images_from_pdf(self, pdf_path: Path, 
                                 azure_figures: list) -> List[ExtractedImage]:
        """PDF'den görselleri çıkar ve filtrele"""
        images = []
        doc = fitz.open(str(pdf_path))
        
        for figure in azure_figures:
            if not figure.bounding_regions:
                continue
            
            page_num = figure.bounding_regions[0].page_number
            bbox = figure.bounding_regions[0].polygon
            
            # Görseli kes
            image_bytes, width, height = self._crop_image(doc, page_num, bbox)
            
            if image_bytes is None:
                continue  # Filtre geçemedi
            
            # Boyut kontrolü - MALİYET KONTROLÜ İÇİN KRİTİK!
            if not self._passes_size_filter(width, height):
                continue
            
            image_id = str(uuid.uuid4())[:8]
            image_path = self._save_image(image_bytes, image_id)
            
            images.append(ExtractedImage(
                image_id=image_id,
                image_bytes=image_bytes,
                image_path=image_path,
                page_number=page_num,
                bounding_box=bbox,
                width=width,
                height=height
            ))
        
        doc.close()
        return images
    
    def _crop_image(self, doc: fitz.Document, page_num: int, 
                    bbox: list) -> tuple:
        """
        Azure polygon koordinatlarını kullanarak görseli kes.
        Azure bbox: [x1,y1, x2,y1, x2,y2, x1,y2] (polygon)
        PyMuPDF rect: [x0, y0, x1, y1]
        """
        try:
            page = doc[page_num - 1]  # PyMuPDF 0-indexed
            
            # Polygon'u Rectangle'a çevir
            x_coords = [bbox[i] for i in range(0, len(bbox), 2)]
            y_coords = [bbox[i] for i in range(1, len(bbox), 2)]
            
            rect = fitz.Rect(
                min(x_coords), min(y_coords),
                max(x_coords), max(y_coords)
            )
            
            # Görseli kes
            pix = page.get_pixmap(clip=rect, dpi=150)
            
            return pix.tobytes("png"), pix.width, pix.height
        except Exception as e:
            print(f"Görsel kesme hatası: {e}")
            return None, 0, 0
    
    def _passes_size_filter(self, width: int, height: int) -> bool:
        """
        MALİYET KONTROLÜ: Çok küçük veya çok ince görselleri atla.
        Bunlar genellikle süsleme, ikon veya kenar çizgileridir.
        """
        # Minimum boyut kontrolü
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            return False
        
        # Aspect ratio kontrolü (çok ince şeritleri atla)
        aspect_ratio = max(width, height) / max(min(width, height), 1)
        if aspect_ratio > self.MAX_ASPECT_RATIO:
            return False
        
        return True
    
    def _save_image(self, image_bytes: bytes, image_id: str) -> Path:
        """Görseli diske kaydet"""
        path = self.output_dir / f"{image_id}.png"
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    
    async def generate_captions(self, images: List[ExtractedImage]) -> List[ExtractedImage]:
        """
        Sadece filtreyi geçen görseller için GPT-4o caption üret.
        MALİYET OPTİMİZASYONU: Gereksiz görsel işlenmez.
        """
        for image in images:
            image_b64 = base64.b64encode(image.image_bytes).decode()
            
            response = await self.vision_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high"
                        }},
                        {"type": "text", "text": self._get_caption_prompt()}
                    ]
                }],
                max_tokens=500
            )
            
            image.caption = response.choices[0].message.content
            image.image_type = await self._classify_image_type(image_b64)
        
        return images
    
    def _get_caption_prompt(self) -> str:
        return """Bu ders kitabı görselini analiz et:
1. Görselin detaylı açıklaması
2. Hangi matematik/fen konusuyla ilgili
3. Tüm sayısal değerler ve etiketler
4. Öğrencinin bu görselden ne öğrenmesi gerektiği"""
```

### 2.4 Semantic Chunker - Yan Sütun Ayrımı ile

```python
# src/document_processing/semantic_chunker.py
from dataclasses import dataclass, field
from typing import List, Dict
import uuid

@dataclass
class SemanticChunk:
    chunk_id: str
    content: str
    chunk_type: str  # "concept", "example", "info", "visual", "sidebar"
    hierarchy_path: str
    page_range: tuple
    related_figures: List[str] = field(default_factory=list)
    related_tables: List[dict] = field(default_factory=list)
    is_sidebar_content: bool = False
    metadata: Dict = field(default_factory=dict)

class SemanticChunker:
    MAX_CHUNK_SIZE = 1500  # Token
    MIN_CHUNK_SIZE = 200
    
    def chunk_document(self, elements: List) -> List[SemanticChunk]:
        """
        Hiyerarşik yapıyı koruyarak akıllı chunking.
        Yan sütunlar ayrı tutulur!
        """
        # Ana içerik ve yan sütunları ayır
        main_elements = [e for e in elements if not e.is_sidebar]
        sidebar_elements = [e for e in elements if e.is_sidebar]
        
        chunks = []
        
        # Ana içeriği chunk'la
        main_chunks = self._chunk_main_content(main_elements)
        chunks.extend(main_chunks)
        
        # Yan sütunları ayrı chunk'lar olarak ekle
        sidebar_chunks = self._chunk_sidebars(sidebar_elements)
        chunks.extend(sidebar_chunks)
        
        return chunks
    
    def _chunk_main_content(self, elements: List) -> List[SemanticChunk]:
        """Ana içeriği semantik gruplara ayır"""
        chunks = []
        current_hierarchy = {"chapter": "", "section": "", "subsection": ""}
        current_group = []
        
        for elem in elements:
            # Yeni bölüm başlangıcı mı?
            if elem.element_type.value in ["section_title", "chapter_title"]:
                if current_group:
                    chunk = self._create_chunk(current_group, current_hierarchy, "concept")
                    chunks.append(chunk)
                current_group = [elem]
                current_hierarchy = self._update_hierarchy(elem, current_hierarchy)
            else:
                current_group.append(elem)
        
        # Son grubu ekle
        if current_group:
            chunks.append(self._create_chunk(current_group, current_hierarchy, "concept"))
        
        return chunks
    
    def _chunk_sidebars(self, elements: List) -> List[SemanticChunk]:
        """Yan sütunları ayrı chunk'lar olarak oluştur"""
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
    
    def _create_chunk(self, group: List, hierarchy: Dict, 
                      chunk_type: str) -> SemanticChunk:
        """Gruptan chunk oluştur - etiketli içerik"""
        content_parts = []
        figures = []
        
        for elem in group:
            if elem.element_type.value == "info_box":
                content_parts.append(f"\n[BİLGİ KUTUSU]\n{elem.content}\n[/BİLGİ KUTUSU]\n")
            elif elem.element_type.value == "example_box":
                content_parts.append(f"\n[ÖRNEK]\n{elem.content}\n[/ÖRNEK]\n")
            elif elem.element_type.value == "figure":
                figures.append(elem.content)
                content_parts.append(f"[ŞEKİL: {elem.content}]")
            else:
                content_parts.append(elem.content)
        
        return SemanticChunk(
            chunk_id=self._generate_id(),
            content="\n".join(content_parts),
            chunk_type=chunk_type,
            hierarchy_path=f"{hierarchy['chapter']}/{hierarchy['section']}/{hierarchy['subsection']}",
            page_range=(group[0].page_number, group[-1].page_number),
            related_figures=figures,
            metadata={"element_count": len(group)}
        )
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())[:8]
    
    def _update_hierarchy(self, elem, current: Dict) -> Dict:
        """Hiyerarşiyi güncelle"""
        new = current.copy()
        if elem.element_type.value == "chapter_title":
            new["chapter"] = elem.content[:50]
            new["section"] = ""
            new["subsection"] = ""
        elif elem.element_type.value == "section_title":
            new["section"] = elem.content[:50]
            new["subsection"] = ""
        elif elem.element_type.value == "subsection_title":
            new["subsection"] = elem.content[:50]
        return new
```

---

## 📊 Maliyet Optimizasyonu Özeti

| Kontrol | Açıklama | Tasarruf |
|---------|----------|----------|
| Min boyut (100x100) | Küçük ikonları atla | ~%40 |
| Aspect ratio (<10) | Kenar süslerini atla | ~%20 |
| Sidebar ayrımı | Gereksiz karışıklığı önle | Kalite ↑ |
| Markdown modu | LaTeX formül desteği | Doğruluk ↑ |

---

## ✅ Doğrulama

```python
def test_image_extraction():
    extractor = ImageExtractor(vision_client, Path("data/processed/images"))
    doc = fitz.open("data/pdfs/ders_kitaplari/mat_5.pdf")
    
    # Manuel test: ilk sayfa, koordinat [100, 100, 300, 100, 300, 300, 100, 300]
    image_bytes, w, h = extractor._crop_image(doc, 1, [100,100,300,100,300,300,100,300])
    assert image_bytes is not None
    assert w == 200 and h == 200
    print("✅ Görsel çıkarma çalışıyor!")
```

---

## ⏭️ Sonraki: Faz 3 - Veritabanı Şeması
