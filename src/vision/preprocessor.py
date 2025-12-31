"""
MEB RAG Sistemi - Image Preprocessor
RAM-only görüntü işleme (diske yazma yok!)
"""
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, Union
import base64


class ImagePreprocessor:
    """
    Image preprocessing for better OCR/Vision results.
    
    CRITICAL: All operations in RAM (BytesIO), NO disk I/O!
    This is essential for FastAPI async performance.
    """
    
    # Target size for vision API (balance quality vs cost)
    MAX_DIMENSION = 2048
    MIN_DIMENSION = 512
    
    # Quality settings
    JPEG_QUALITY = 85
    
    def __init__(self):
        pass
    
    def enhance_for_ocr_memory(
        self, 
        image_path: Union[str, Path]
    ) -> Tuple[bytes, str]:
        """
        Enhance image for OCR, operating entirely in memory.
        
        Args:
            image_path: Path to source image
            
        Returns:
            Tuple of (enhanced image bytes, base64 string)
        """
        # Load image
        with Image.open(image_path) as img:
            return self._enhance_image(img)
    
    def enhance_from_bytes(
        self, 
        image_bytes: bytes
    ) -> Tuple[bytes, str]:
        """
        Enhance image from bytes (for FastAPI UploadFile).
        
        CRITICAL: For non-blocking API use!
        
        Args:
            image_bytes: Raw image bytes from upload
            
        Returns:
            Tuple of (enhanced image bytes, base64 string)
        """
        img = Image.open(BytesIO(image_bytes))
        return self._enhance_image(img)
    
    def _enhance_image(self, img: Image.Image) -> Tuple[bytes, str]:
        """
        Core image enhancement pipeline.
        
        Steps:
        1. Convert to RGB (handle transparency)
        2. Resize if too large/small
        3. Enhance contrast
        4. Sharpen for text clarity
        5. Convert to bytes
        """
        # Step 1: Convert to RGB
        if img.mode in ('RGBA', 'P'):
            # Handle transparency by adding white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Step 2: Resize if needed
        img = self._resize_if_needed(img)
        
        # Step 3: Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)  # 20% more contrast
        
        # Step 4: Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        
        # Step 5: Convert to bytes (PNG for lossless)
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=True)
        image_bytes = buffer.getvalue()
        
        # Also return base64 for convenience
        base64_str = base64.b64encode(image_bytes).decode('utf-8')
        
        return image_bytes, base64_str
    
    def _resize_if_needed(self, img: Image.Image) -> Image.Image:
        """
        Resize image to optimal dimensions.
        
        - Too large: Scale down to MAX_DIMENSION
        - Too small: Scale up to MIN_DIMENSION (for better OCR)
        """
        width, height = img.size
        max_dim = max(width, height)
        min_dim = min(width, height)
        
        # Scale down if too large
        if max_dim > self.MAX_DIMENSION:
            ratio = self.MAX_DIMENSION / max_dim
            new_size = (int(width * ratio), int(height * ratio))
            return img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Scale up if too small (helps OCR)
        if max_dim < self.MIN_DIMENSION and min_dim > 50:
            ratio = self.MIN_DIMENSION / max_dim
            new_size = (int(width * ratio), int(height * ratio))
            return img.resize(new_size, Image.Resampling.LANCZOS)
        
        return img
    
    def get_image_info(
        self, 
        image_bytes: bytes
    ) -> dict:
        """
        Get basic image information.
        
        Args:
            image_bytes: Image data
            
        Returns:
            Dict with format, size, mode info
        """
        img = Image.open(BytesIO(image_bytes))
        return {
            "format": img.format,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "size_bytes": len(image_bytes)
        }
    
    def compress_for_api(
        self, 
        image_bytes: bytes, 
        target_size_kb: int = 500
    ) -> Tuple[bytes, str]:
        """
        Compress image to target size for API cost control.
        
        Args:
            image_bytes: Original image bytes
            target_size_kb: Target size in KB
            
        Returns:
            Tuple of (compressed bytes, base64 string)
        """
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Try different quality levels
        for quality in range(self.JPEG_QUALITY, 20, -10):
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=quality)
            
            if buffer.tell() <= target_size_kb * 1024:
                compressed = buffer.getvalue()
                return compressed, base64.b64encode(compressed).decode('utf-8')
        
        # If still too large, resize
        ratio = 0.8
        while True:
            new_size = (int(img.width * ratio), int(img.height * ratio))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            resized.save(buffer, format='JPEG', quality=50)
            
            if buffer.tell() <= target_size_kb * 1024 or ratio < 0.3:
                compressed = buffer.getvalue()
                return compressed, base64.b64encode(compressed).decode('utf-8')
            
            ratio -= 0.1
