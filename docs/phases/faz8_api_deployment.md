# Faz 8: API ve Deployment

## 🎯 Amaç
Tüm fazları birleştiren **FastAPI** backend ile production-ready API.

---

## ⚠️ KRİTİK: Önceki Faz Entegrasyonu

| Faz | Entegrasyon |
|-----|-------------|
| Faz 5 | RAM'den oku, diske YAZMA! |
| Faz 6 | `MebRagGraph.ainvoke()` çağır |
| Faz 7 | `AnalysisOutput` Pydantic modeli |

---

## 🔧 Uygulama Adımları

### 8.1 Pydantic API Modelleri

```python
# api/models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class AnalysisRequest(BaseModel):
    question: str = Field(description="Soru metni")
    grade: Optional[int] = Field(None, description="Sınıf seviyesi (1-12)")
    subject: Optional[str] = Field(None, description="Ders adı")

class KazanimModel(BaseModel):
    code: str
    description: str
    relevance_score: float

class SectionModel(BaseModel):
    title: str
    hierarchy_path: str
    page_range: Optional[str]

class PrerequisiteGapModel(BaseModel):
    topic: str
    related_kazanim_codes: List[str]

class AnalysisResponse(BaseModel):
    """Faz 7 AnalysisOutput ile uyumlu"""
    tested_kazanimlar: List[KazanimModel]
    prerequisite_gaps: List[PrerequisiteGapModel]
    recommended_sections: List[SectionModel]
    explanation: str
    confidence: float
    processing_time_ms: int

class FeedbackRequest(BaseModel):
    analysis_id: str
    rating: int = Field(ge=-1, le=1, description="-1: thumbs down, 1: thumbs up")
    comment: Optional[str] = None
    correct_kazanim: Optional[str] = None
```

### 8.2 FastAPI Main App

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.routes import analysis, feedback

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="MEB RAG API",
    description="MEB Kazanım Analiz Sistemi",
    version="1.0.0"
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prodüksiyonda kısıtlayın!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
app.include_router(feedback.router, prefix="/api/v1", tags=["Feedback"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

### 8.3 Analysis Routes (RAM-Based Upload!)

```python
# api/routes/analysis.py
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
import time
import json
import uuid

from api.models import AnalysisRequest, AnalysisResponse
from src.agents.graph import MebRagGraph
from src.vision.pipeline import QuestionAnalysisPipeline

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Pipeline ve Graph singletons
vision_pipeline = QuestionAnalysisPipeline()

@router.post("/analyze-image", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def analyze_question_image(
    request: Request,
    file: UploadFile = File(...),
    grade: int = None,
    subject: str = None
):
    """
    Görsel analiz endpoint'i.
    DİSKE YAZMAZ - RAM'den işler!
    """
    start_time = time.time()
    analysis_id = str(uuid.uuid4())[:8]
    
    # 1. RAM'den oku - DİSKE KAYDETME!
    content = await file.read()
    
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "Dosya çok büyük (max 10MB)")
    
    # 2. Faz 5 Pipeline (bytes alır)
    extracted = await vision_pipeline.process_from_bytes(content)
    
    # 3. Faz 6 LangGraph
    workflow = MebRagGraph(use_postgres=True)
    config = {"configurable": {"thread_id": analysis_id}}
    
    result = await workflow.graph.ainvoke(
        input={
            "raw_input": extracted["text"],
            "input_type": "text",  # Artık metin olarak işle
            "user_grade": grade,
            "user_subject": subject,
            "retry_count": 0
        },
        config=config
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return _format_response(result, analysis_id, processing_time)


@router.post("/analyze-text", response_model=AnalysisResponse)
@limiter.limit("20/minute")
async def analyze_question_text(
    request: Request,
    body: AnalysisRequest
):
    """Metin analiz endpoint'i"""
    start_time = time.time()
    analysis_id = str(uuid.uuid4())[:8]
    
    # Faz 6 LangGraph
    workflow = MebRagGraph(use_postgres=True)
    config = {"configurable": {"thread_id": analysis_id}}
    
    result = await workflow.graph.ainvoke(
        input={
            "raw_input": body.question,
            "input_type": "text",
            "user_grade": body.grade,
            "user_subject": body.subject,
            "retry_count": 0
        },
        config=config
    )
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return _format_response(result, analysis_id, processing_time)


@router.post("/analyze-stream")
@limiter.limit("10/minute")
async def analyze_stream(request: Request, body: AnalysisRequest):
    """
    Streaming endpoint - SSE ile token by token.
    UX için kritik: 30s bekleme yok!
    """
    workflow = MebRagGraph(use_postgres=True)
    analysis_id = str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": analysis_id}}
    
    async def event_generator():
        try:
            async for event in workflow.graph.astream_events(
                input={
                    "raw_input": body.question,
                    "input_type": "text",
                    "user_grade": body.grade,
                    "user_subject": body.subject,
                    "retry_count": 0
                },
                config=config,
                version="v2"
            ):
                kind = event["event"]
                
                # Node geçişlerini bildir
                if kind == "on_chain_start":
                    node_name = event.get("name", "unknown")
                    yield f"data: {json.dumps({'type': 'step', 'step': node_name})}\n\n"
                
                # LLM token stream
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done', 'analysis_id': analysis_id})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


def _format_response(result: dict, analysis_id: str, processing_time: int) -> dict:
    """LangGraph state'i API response'a dönüştür"""
    gap_analysis = result.get("gap_analysis", {})
    
    return {
        "analysis_id": analysis_id,
        "tested_kazanimlar": gap_analysis.get("tested_kazanimlar", []),
        "prerequisite_gaps": gap_analysis.get("prerequisite_gaps", []),
        "recommended_sections": [
            {"title": s.get("hierarchy_path", ""), 
             "hierarchy_path": s.get("hierarchy_path", ""),
             "page_range": s.get("page_range")}
            for s in result.get("top_sections", [])
        ],
        "explanation": result.get("explanation", ""),
        "confidence": result.get("confidence", 0.0),
        "processing_time_ms": processing_time
    }
```

### 8.4 Feedback Route

```python
# api/routes/feedback.py
from fastapi import APIRouter, Depends
from datetime import datetime

from api.models import FeedbackRequest
from src.database.db import get_db
from src.database.models import Feedback

router = APIRouter()

@router.post("/feedback")
async def submit_feedback(body: FeedbackRequest, db = Depends(get_db)):
    """Kullanıcı geri bildirimi - sistem iyileştirme için"""
    
    feedback = Feedback(
        analysis_id=body.analysis_id,
        rating=body.rating,
        comment=body.comment,
        correct_kazanim=body.correct_kazanim,
        created_at=datetime.utcnow()
    )
    
    db.add(feedback)
    db.commit()
    
    # Negatif feedback logla (fine-tuning için)
    if body.rating == -1:
        await _log_negative_feedback(body)
    
    return {"status": "success", "message": "Geri bildiriminiz kaydedildi"}

async def _log_negative_feedback(feedback: FeedbackRequest):
    """Negatif feedback'leri ayrı logla"""
    # Bu veriler:
    # 1. Sentetik soru kalitesini ölçmek için
    # 2. Prompt iyileştirmesi için
    # 3. Edge case tespiti için kullanılır
    import logging
    logging.warning(f"Negative feedback: {feedback.analysis_id} - {feedback.comment}")
```

### 8.5 Dockerfile (Sistem Bağımlılıkları!)

```dockerfile
FROM python:3.11-slim

# PyMuPDF ve OpenCV için gerekli sistem kütüphaneleri
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements (cache için ayrı layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama
COPY . .

# Port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.6 Docker Compose (Postgres Dahil!)

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://meb:meb123@postgres:5432/meb_rag
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      - AZURE_SEARCH_ENDPOINT=${AZURE_SEARCH_ENDPOINT}
      - AZURE_SEARCH_API_KEY=${AZURE_SEARCH_API_KEY}
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: meb
      POSTGRES_PASSWORD: meb123
      POSTGRES_DB: meb_rag
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

---

## 📊 API Mimarisi (Final)

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
├──────────────────────────────────────────────────────────┤
│  Rate Limiter Middleware (slowapi)                       │
├────────────┬────────────┬───────────────┬────────────────┤
│ /analyze-  │ /analyze-  │ /analyze-     │ /feedback      │
│   image    │   text     │   stream      │                │
│ (RAM read) │            │   (SSE)       │                │
└─────┬──────┴─────┬──────┴───────┬───────┴────────┬───────┘
      │            │              │                │
      ▼            ▼              ▼                ▼
┌──────────┐ ┌────────────┐ ┌───────────────┐ ┌──────────┐
│ Faz 5    │ │ Faz 6      │ │ SSE Streaming │ │ Postgres │
│ Vision   │ │ MebRagGraph│ │ Token by Token│ │ Feedback │
│ Pipeline │ │ .ainvoke() │ │ astream_events│ │          │
└──────────┘ └────────────┘ └───────────────┘ └──────────┘
```

---

## ✅ Proje Tamamlandı!

Tüm 8 faz uygulandığında:
- ✅ MEB kazanımları veritabanında (Faz 3)
- ✅ Ders kitapları semantic chunking ile (Faz 2)
- ✅ Sentetik soru eşleştirme + Hybrid Search (Faz 4)
- ✅ Görüntü analizi GPT-4o Vision ile (Faz 5)
- ✅ LangGraph State Machine (Faz 6)
- ✅ Pydantic Structured Output (Faz 7)
- ✅ Streaming REST API + Rate Limiting (Faz 8)
- ✅ Feedback döngüsü (Faz 8)

---

## 🚀 Deployment Komutları

```bash
# Geliştirme
uvicorn api.main:app --reload

# Docker Build
docker-compose build

# Docker Run
docker-compose up -d

# Logları izle
docker-compose logs -f api

# Test
pytest tests/ -v
```

---

## 🎉 Final Değerlendirmesi

**Projenin Güçlü Yanları:**
1. **Hiyerarşik Chunking (Faz 2)** - Veri kaybını önleyen yapı
2. **Parent Document Retrieval (Faz 4)** - Semantic Gap çözümü
3. **LangGraph State Machine (Faz 6)** - Deterministik akış
4. **Feedback Loop (Faz 8)** - Sürekli iyileştirme

**Toplam: 140+ Checklist Item, 8 Faz, Enterprise-Grade RAG!**
