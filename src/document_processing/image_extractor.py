"""
Image Extractor for MEB Textbook PDFs

Uses PyMuPDF (fitz) to extract and crop images from PDFs
based on Azure Document Intelligence coordinates.
"""
import fitz  # PyMuPDF
import base64
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
from io import BytesIO


@dataclass
class ExtractedImage:
    """Extracted image from textbook"""
    image_id: str
    image_bytes: bytes
    image_path: Optional[Path]
    page_number: int
    bounding_box: list
    width: int
    height: int
    caption: Optional[str] = None
    image_type: Optional[str] = None  # graph, diagram, photo, table_image
    related_text: str = ""
    hierarchy_path: str = ""


class ImageExtractor:
    """
    Extract images from PDF using Azure coordinates.
    Uses PyMuPDF (fitz) for image cropping.
    
    Cost optimization:
    - Minimum size filter (100x100 pixels)
    - Aspect ratio filter (<10 to skip decorative lines)
    """
    
    # Cost control: minimum dimensions
    MIN_WIDTH = 100   # pixels
    MIN_HEIGHT = 100  # pixels
    MAX_ASPECT_RATIO = 10  # Skip thin strips (decorative borders)
    
    def __init__(self, vision_client=None, output_dir: Optional[Path] = None):
        """
        Args:
            vision_client: Azure OpenAI client for caption generation
            output_dir: Directory to save extracted images
        """
        self.vision_client = vision_client
        self.output_dir = output_dir
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_images_from_pdf(
        self, 
        pdf_path: Path, 
        azure_figures: list
    ) -> List[ExtractedImage]:
        """
        Extract images from PDF based on Azure figure coordinates.
        
        Args:
            pdf_path: Path to PDF file
            azure_figures: List of figure objects from Azure Document Intelligence
            
        Returns:
            List of ExtractedImage objects that pass size filters
        """
        images = []
        doc = fitz.open(str(pdf_path))
        
        try:
            for figure in azure_figures:
                if not figure.bounding_regions:
                    continue
                
                region = figure.bounding_regions[0]
                page_num = region.page_number
                bbox = region.polygon
                
                if not bbox:
                    continue
                
                # Crop image from PDF
                image_bytes, width, height = self._crop_image(doc, page_num, bbox)
                
                if image_bytes is None:
                    continue
                
                # Apply size filter - COST CONTROL!
                if not self._passes_size_filter(width, height):
                    continue
                
                image_id = str(uuid.uuid4())[:8]
                image_path = None
                
                if self.output_dir:
                    image_path = self._save_image(image_bytes, image_id)
                
                images.append(ExtractedImage(
                    image_id=image_id,
                    image_bytes=image_bytes,
                    image_path=image_path,
                    page_number=page_num,
                    bounding_box=bbox,
                    width=width,
                    height=height,
                    caption=figure.caption.content if figure.caption else None
                ))
        finally:
            doc.close()
        
        return images
    
    def extract_images_from_bytes(
        self, 
        pdf_bytes: bytes, 
        azure_figures: list
    ) -> List[ExtractedImage]:
        """
        Extract images from PDF bytes (for API use).
        
        Args:
            pdf_bytes: PDF content as bytes
            azure_figures: List of figure objects from Azure Document Intelligence
            
        Returns:
            List of ExtractedImage objects
        """
        images = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        try:
            for figure in azure_figures:
                if not figure.bounding_regions:
                    continue
                
                region = figure.bounding_regions[0]
                page_num = region.page_number
                bbox = region.polygon
                
                if not bbox:
                    continue
                
                image_bytes, width, height = self._crop_image(doc, page_num, bbox)
                
                if image_bytes is None:
                    continue
                
                if not self._passes_size_filter(width, height):
                    continue
                
                image_id = str(uuid.uuid4())[:8]
                
                images.append(ExtractedImage(
                    image_id=image_id,
                    image_bytes=image_bytes,
                    image_path=None,
                    page_number=page_num,
                    bounding_box=bbox,
                    width=width,
                    height=height,
                    caption=figure.caption.content if figure.caption else None
                ))
        finally:
            doc.close()
        
        return images
    
    def _crop_image(
        self, 
        doc: fitz.Document, 
        page_num: int, 
        bbox: list
    ) -> Tuple[Optional[bytes], int, int]:
        """
        Crop image from PDF page using Azure polygon coordinates.
        
        Azure bbox format: [x1,y1, x2,y1, x2,y2, x1,y2] (polygon)
        PyMuPDF rect format: [x0, y0, x1, y1]
        
        Returns:
            Tuple of (image_bytes, width, height) or (None, 0, 0) on error
        """
        try:
            # PyMuPDF uses 0-indexed pages
            page = doc[page_num - 1]
            
            # Convert polygon to rectangle
            x_coords = [bbox[i] for i in range(0, len(bbox), 2)]
            y_coords = [bbox[i] for i in range(1, len(bbox), 2)]
            
            rect = fitz.Rect(
                min(x_coords), min(y_coords),
                max(x_coords), max(y_coords)
            )
            
            # Render cropped area at 150 DPI
            pix = page.get_pixmap(clip=rect, dpi=150)
            
            return pix.tobytes("png"), pix.width, pix.height
            
        except Exception as e:
            print(f"Image crop error: {e}")
            return None, 0, 0
    
    def _passes_size_filter(self, width: int, height: int) -> bool:
        """
        COST CONTROL: Filter out too small or too thin images.
        
        Filters:
        - Minimum 100x100 pixels
        - Aspect ratio < 10 (skip decorative borders)
        """
        # Minimum size check
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            return False
        
        # Aspect ratio check (skip thin decorative lines)
        aspect_ratio = max(width, height) / max(min(width, height), 1)
        if aspect_ratio > self.MAX_ASPECT_RATIO:
            return False
        
        return True
    
    def _save_image(self, image_bytes: bytes, image_id: str) -> Path:
        """Save image to output directory"""
        path = self.output_dir / f"{image_id}.png"
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
    
    async def generate_captions(
        self, 
        images: List[ExtractedImage]
    ) -> List[ExtractedImage]:
        """
        Generate captions for images using GPT-4o Vision.
        Only processes images that passed the size filter.
        
        COST OPTIMIZATION: Small/decorative images are already filtered out.
        """
        if not self.vision_client:
            return images
        
        for image in images:
            if image.caption:
                continue  # Already has caption from Azure
            
            try:
                image_b64 = base64.b64encode(image.image_bytes).decode()
                
                response = await self.vision_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url", 
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                    "detail": "high"
                                }
                            },
                            {"type": "text", "text": self._get_caption_prompt()}
                        ]
                    }],
                    max_tokens=500
                )
                
                image.caption = response.choices[0].message.content
                image.image_type = await self._classify_image_type(image_b64)
                
            except Exception as e:
                print(f"Caption generation error for {image.image_id}: {e}")
        
        return images
    
    def _get_caption_prompt(self) -> str:
        """Prompt for image caption generation"""
        return """Bu ders kitabı görselini analiz et:
1. Görselin detaylı açıklaması
2. Hangi matematik/fen konusuyla ilgili
3. Tüm sayısal değerler ve etiketler
4. Öğrencinin bu görselden ne öğrenmesi gerektiği

Türkçe olarak yanıtla."""
    
    async def _classify_image_type(self, image_b64: str) -> str:
        """Classify image type using GPT-4o Vision"""
        if not self.vision_client:
            return "unknown"
        
        try:
            response = await self.vision_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "low"
                            }
                        },
                        {
                            "type": "text",
                            "text": "Bu görseli sınıflandır. Sadece şu kelimelerden birini yaz: graph, diagram, photo, table_image, illustration, chart"
                        }
                    ]
                }],
                max_tokens=20
            )
            return response.choices[0].message.content.strip().lower()
        except Exception:
            return "unknown"
