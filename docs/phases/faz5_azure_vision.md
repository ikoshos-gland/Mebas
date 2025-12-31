# Faz 5: Azure GPT-4o Vision Entegrasyonu

## 🎯 Amaç
Soru görüntülerini Azure GPT-4o Vision ile **asenkron** olarak analiz etmek.

---

## ⚠️ KRİTİK: FastAPI Uyumluluğu

| Sorun | Eski | Yeni |
|-------|------|------|
| Client tipi | Sync (donma riski) | **Async** |
| Görsel işleme | Disk I/O | **RAM (BytesIO)** |
| JSON parse | Direkt loads | **Markdown temizle** |

---

## 🔧 Uygulama Adımları

### 5.1 Azure Vision Client (ASYNC!)

```python
# src/vision/azure_vision_client.py
from openai import AsyncAzureOpenAI  # ASYNC versiyon!
from config.settings import get_settings
from dataclasses import dataclass
from typing import Optional, List
import json
import re

@dataclass
class VisionAnalysisResult:
    extracted_text: str
    question_type: str
    topics: List[str]
    math_expressions: List[str]
    estimated_grade: Optional[int]  # null olabilir!
    confidence: float
    raw_response: Optional[str] = None

class AzureVisionClient:
    """
    GPT-4o Vision için ASYNC client.
    FastAPI uyumlu - sunucu donmaz!
    """
    
    def __init__(self):
        settings = get_settings()
        # ASYNC Client - KRİTİK!
        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version
        )
        self.model = settings.azure_openai_chat_deployment
    
    async def analyze_question_image(self, base64_image: str) -> VisionAnalysisResult:
        """
        Görsel analizi - base64 string alır (disk I/O yok!)
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }
                    },
                    {"type": "text", "text": self._get_extraction_prompt()}
                ]
            }],
            max_tokens=2000,
            temperature=0
        )
        return self._parse_response(response)
    
    def _get_extraction_prompt(self) -> str:
        return """Bu soru görüntüsünü analiz et ve şunları çıkar:

1. Sorunun tam metni (matematiksel ifadeler LaTeX formatında: $x^2$ gibi)
2. Soru tipi (matematik, fen, edebiyat, tarih vb.)
3. İlgili konular/kavramlar (liste)
4. Matematiksel ifadeler varsa ayrı liste halinde
5. Tahmini sınıf seviyesi (EĞer EMİN DEĞİLSEN null döndür!)

⚠️ ÖNEMLİ: Sadece JSON döndür, başka açıklama yazma!

{
    "extracted_text": "...",
    "question_type": "...",
    "topics": ["...", "..."],
    "math_expressions": ["$...$"],
    "estimated_grade": null veya sayı
}"""

    def _parse_response(self, response) -> VisionAnalysisResult:
        """
        JSON parse - Markdown bloklarını temizle!
        GPT bazen ```json ... ``` ile sarar
        """
        content = response.choices[0].message.content
        
        # Markdown kod bloklarını temizle
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            match = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', content)
            if match:
                content = match.group(1).strip()
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # Fallback: Ham içeriği logla
            print(f"⚠️ JSON Parse Hatası: {e}")
            print(f"Ham içerik: {content[:200]}...")
            
            # Basit bir fallback döndür
            return VisionAnalysisResult(
                extracted_text=content,
                question_type="unknown",
                topics=[],
                math_expressions=[],
                estimated_grade=None,
                confidence=0.5,
                raw_response=content
            )
        
        return VisionAnalysisResult(
            extracted_text=data.get("extracted_text", ""),
            question_type=data.get("question_type", "unknown"),
            topics=data.get("topics", []),
            math_expressions=data.get("math_expressions", []),
            estimated_grade=data.get("estimated_grade"),  # null olabilir
            confidence=0.95
        )
```

### 5.2 Görüntü Ön İşleme (BELLEK TABANLI!)

```python
# src/vision/preprocessor.py
from PIL import Image
from io import BytesIO
import base64
from pathlib import Path

class ImagePreprocessor:
    """
    Görüntü işleme - RAM üzerinde!
    Diske yazmak yavaş ve çöp dosya biriktirir.
    """
    
    MAX_SIZE = 2048  # GPT-4o max çözünürlük
    JPEG_QUALITY = 95
    
    def enhance_for_ocr_memory(self, image_path: str) -> str:
        """
        Görüntüyü işle ve base64 string olarak döndür.
        Diske HİÇ yazmaz!
        """
        img = Image.open(image_path)
        
        # RGB'ye dönüştür (RGBA veya P mode olursa JPEG patlar)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Boyut kontrolü
        if img.size[0] > self.MAX_SIZE or img.size[1] > self.MAX_SIZE:
            img.thumbnail((self.MAX_SIZE, self.MAX_SIZE), Image.Resampling.LANCZOS)
        
        # RAM'e kaydet (BytesIO)
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=self.JPEG_QUALITY)
        
        # Base64 encode
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def enhance_from_bytes(self, image_bytes: bytes) -> str:
        """Bytes'tan direkt base64'e (upload için)"""
        img = Image.open(BytesIO(image_bytes))
        
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        if img.size[0] > self.MAX_SIZE or img.size[1] > self.MAX_SIZE:
            img.thumbnail((self.MAX_SIZE, self.MAX_SIZE), Image.Resampling.LANCZOS)
        
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=self.JPEG_QUALITY)
        
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
```

### 5.3 Analiz Pipeline (TAM ASYNC)

```python
# src/vision/pipeline.py
from src.vision.azure_vision_client import AzureVisionClient, VisionAnalysisResult
from src.vision.preprocessor import ImagePreprocessor
from typing import Union
from pathlib import Path

class QuestionAnalysisPipeline:
    """
    Tam asenkron görsel analiz pipeline.
    FastAPI ile uyumlu - sunucu DONMAZ!
    """
    
    def __init__(self):
        self.vision_client = AzureVisionClient()
        self.preprocessor = ImagePreprocessor()
    
    async def process_from_path(self, image_path: str) -> dict:
        """Disk üzerindeki görseli analiz et"""
        # 1. RAM'de işle (disk I/O yok!)
        base64_image = self.preprocessor.enhance_for_ocr_memory(image_path)
        
        # 2. Async Vision API çağrısı (sunucu donmaz!)
        result = await self.vision_client.analyze_question_image(base64_image)
        
        return self._format_result(result)
    
    async def process_from_bytes(self, image_bytes: bytes) -> dict:
        """Upload edilen görseli analiz et (FastAPI UploadFile için)"""
        # 1. RAM'de işle
        base64_image = self.preprocessor.enhance_from_bytes(image_bytes)
        
        # 2. Async Vision API çağrısı
        result = await self.vision_client.analyze_question_image(base64_image)
        
        return self._format_result(result)
    
    def _format_result(self, result: VisionAnalysisResult) -> dict:
        return {
            "text": result.extracted_text,
            "type": result.question_type,
            "topics": result.topics,
            "math_expressions": result.math_expressions,
            "estimated_grade": result.estimated_grade,
            "confidence": result.confidence,
            "ready_for_rag": len(result.extracted_text) > 10
        }
```

---

## 📊 Akış (Güncellenmiş)

```
Görsel (jpg/png)
         │
         ▼
┌──────────────────┐
│ ImagePreprocessor │
│ (RAM - BytesIO)   │  ← Diske yazmaz!
└────────┬─────────┘
         │ base64 string
         ▼
┌──────────────────┐
│ AsyncAzureOpenAI │  ← await ile çağrılır
│ GPT-4o Vision    │    Sunucu donmaz!
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ JSON Parse       │  ← Markdown temizleme
│ + Fallback       │    JSON hatası = çökmez
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ VisionAnalysisResult │
│ (RAG'a hazır)     │
└──────────────────┘
```

---

## ✅ Avantajlar

| Sorun | Eski | Yeni |
|-------|------|------|
| Sunucu donması | ✗ Sync client | ✅ Async client |
| Disk çöpü | ✗ _enhanced.jpg dosyaları | ✅ RAM işleme |
| JSON hatası | ✗ Çökme | ✅ Markdown temizle + fallback |
| Sınıf tahmini | ✗ Her zaman tahmin et | ✅ Emin değilse null |
| Settings | ✗ settings.openai.xxx | ✅ settings.azure_openai_xxx |

---

## ⏭️ Sonraki: Faz 6 - LangGraph State Machine
