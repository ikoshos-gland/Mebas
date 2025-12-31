# MEB RAG Sistemi - Detaylı Uygulama Rehberi

> **Bu döküman bir LLM'in 8 fazı adım adım uygulaması için hazırlanmıştır.**
> Her adımı sırasıyla takip edin. Bir fazı bitirmeden diğerine geçmeyin.

---

## 📋 MASTER CHECKLIST

### FAZ 1: Proje Altyapısı [9/16] ✅
- [x] 1.1 Proje dizin yapısını oluştur
- [x] 1.2 Tüm `__init__.py` dosyalarını oluştur (import hataları için kritik!)
- [x] 1.3 `requirements.txt` dosyasını oluştur (langgraph dahil!)
- [ ] 1.4 `pip install -r requirements.txt` çalıştır
- [x] 1.5 `.env.example` dosyasını oluştur
- [x] 1.6 `.gitignore` dosyasını oluştur
- [ ] 1.7 Azure Document Intelligence kaynağı oluştur
- [ ] 1.8 Azure AI Search kaynağı oluştur (NOT: Semantic Ranker için Standard önerilir)
- [ ] 1.9 Azure OpenAI kaynağı oluştur
- [ ] 1.10 Azure OpenAI'da gpt-4o deployment oluştur
- [ ] 1.11 Azure OpenAI'da text-embedding-ada-002 deployment oluştur
- [ ] 1.12 `.env` dosyasına TÜM API key'leri ekle (OpenAI dahil!)
- [x] 1.13 `config/settings.py` - Pydantic V2 Settings modülü yaz
- [x] 1.14 `config/azure_config.py` - Client factory fonksiyonları yaz
- [x] 1.15 `tests/test_config.py` - Konfigürasyon testleri yaz
- [ ] 1.16 **DOĞRULAMA:** `pytest tests/test_config.py` + Azure OpenAI bağlantı testi

### FAZ 2: PDF İşleme [19/20] ✅
- [x] 2.1 `pymupdf>=1.23.0` requirements.txt'e ekle
- [x] 2.2 `src/document_processing/__init__.py` oluştur
- [x] 2.3 `ElementType` enum'ını tanımla (sidebar dahil!)
- [x] 2.4 `LayoutElement` dataclass'ını tanımla (`is_sidebar` alanı ile)
- [x] 2.5 `LayoutAnalyzer` sınıfını yaz
- [x] 2.6 **KRİTİK:** `output_content_format="markdown"` kullan (LaTeX için!)
- [x] 2.7 `_is_in_sidebar_region` metodu - Yan sütun tespiti
- [x] 2.8 `SemanticChunk` dataclass'ını tanımla
- [x] 2.9 `SemanticChunker` sınıfını yaz
- [x] 2.10 Ana içerik ve sidebar'ları AYIR
- [x] 2.11 Sidebar'ları ayrı chunk olarak oluştur
- [x] 2.12 `ExtractedImage` dataclass'ını tanımla
- [x] 2.13 `ImageExtractor` sınıfını yaz (PyMuPDF ile)
- [x] 2.14 `_crop_image` metodu - Azure koordinatlarıyla kesim
- [x] 2.15 **MALİYET:** `_passes_size_filter` - Min 100x100, aspect ratio <10
- [x] 2.16 **MALİYET:** Sadece filtreyi geçen görsellere caption üret
- [x] 2.17 `_generate_caption` metodunu GPT-4o ile implemente et
- [x] 2.18 `_classify_image_type` metodunu implemente et
- [x] 2.19 `HierarchyBuilder` sınıfını yaz
- [ ] 2.20 **DOĞRULAMA:** PDF test et, görsel kesim + sidebar ayrımı çalışmalı

### FAZ 3: Veritabanı [12/14] ✅
- [x] 3.1 `src/database/__init__.py` oluştur
- [x] 3.2 `Subject` SQLAlchemy modeli yaz
- [x] 3.3 `Kazanim` modeli yaz (learning_area, sub_learning_area, bloom_level dahil!)
- [x] 3.4 `Textbook` modeli yaz
- [x] 3.5 `Chapter` modeli yaz (content sütunu YOK - chunk'larda!)
- [x] 3.6 **KRİTİK:** `BookChunk` modeli yaz (Faz 2 SemanticChunk ile eşleşir)
- [x] 3.7 **KRİTİK:** `TextbookImage` modeli yaz (Faz 2 ExtractedImage ile eşleşir)
- [x] 3.8 `Feedback` modeli yaz (Faz 8 için)
- [x] 3.9 `db.py` - Engine ve SessionLocal oluştur
- [x] 3.10 `init_db()` fonksiyonunu yaz
- [x] 3.11 `import_chunks.py` - Faz 2 → DB aktarım fonksiyonları
- [ ] 3.12 Alembic migration kurulumu yap
- [x] 3.13 İlişkileri test et (Chapter → Chunks → Images)
- [ ] 3.14 **DOĞRULAMA:** Chunk insert/query testi çalıştır


### FAZ 4: Azure AI Search [21/23] ✅
- [x] 4.1 `src/vector_store/__init__.py` oluştur
- [x] 4.2 **KRİTİK:** `embeddings.py` - `embed_text()` ve `embed_batch()` fonksiyonları
- [x] 4.3 `SyntheticQuestion` dataclass'ını tanımla
- [x] 4.4 `SyntheticQuestionGenerator` sınıfını yaz
- [x] 4.5 **MALİYET:** `gpt-4o-mini` kullan (20x ucuz!)
- [x] 4.6 **MALİYET:** Soru sayısını 20'ye düşür (50 değil)
- [x] 4.7 JSON parse retry mekanizması ekle
- [x] 4.8 `create_question_index_schema()` - Türkçe analyzer ile
- [x] 4.9 **HYBRID:** `SemanticSearch` configuration ekle
- [x] 4.10 `create_image_index_schema()` fonksiyonunu yaz
- [ ] 4.11 Azure AI Search'te indexleri oluştur
- [x] 4.12 `ParentDocumentRetriever` sınıfını yaz
- [x] 4.13 **HYBRID:** `search()` metodu - vektör + keyword + semantic
- [x] 4.14 **KRİTİK:** Grade ve subject filtresi ekle (pedagojik doğruluk!)
- [x] 4.14b **YKS MODU:** `is_exam_mode` - dinamik filtre (grade le X vs grade eq X)
- [x] 4.15 Parent Kazanım gruplama ve skorlama mantığı
- [x] 4.16 `ImageRetriever` sınıfını yaz
- [x] 4.17 `search_by_description` metodunu implemente et
- [x] 4.18 `IndexingPipeline` sınıfını yaz
- [x] 4.19 Batch embedding (16'lık gruplar, maliyet optimizasyonu)
- [x] 4.20 Rate limiting (1s/batch)
- [ ] 4.21 Tüm kazanımlar için sentetik sorular üret ve indeksle
- [ ] 4.22 **DOĞRULAMA:** Hybrid search test et, filtre ile doğru sınıf dönmeli


### FAZ 5: Azure GPT-4o Vision [13/14] ✅
- [x] 5.1 `src/vision/__init__.py` oluştur
- [x] 5.2 `VisionAnalysisResult` dataclass'ını tanımla
- [x] 5.3 **ASYNC:** `AzureVisionClient` sınıfını `AsyncAzureOpenAI` ile yaz
- [x] 5.4 `_get_extraction_prompt` metodunu yaz (emin değilse null dönsün!)
- [x] 5.5 **KRİTİK:** `_parse_response` - Markdown kod bloklarını temizle
- [x] 5.6 JSON parse fallback mekanizması ekle (çökmez!)
- [x] 5.7 `ImagePreprocessor` sınıfını yaz
- [x] 5.8 **BELLEK:** `enhance_for_ocr_memory` - BytesIO kullan, diske yazma!
- [x] 5.9 `enhance_from_bytes` - UploadFile için
- [x] 5.10 `QuestionAnalysisPipeline` sınıfını yaz
- [x] 5.11 `process_from_path` async metodunu implemente et
- [x] 5.12 `process_from_bytes` async metodunu implemente et (FastAPI için)
- [x] 5.13 RGBA/P mode → RGB dönüşümü ekle
- [ ] 5.14 **DOĞRULAMA:** Async çağrı test et, JSON hatası fallback çalışmalı


### FAZ 6: LangGraph State Machine [19/22] ✅
- [x] 6.1 `langgraph-checkpoint-postgres` requirements.txt'e ekle
- [x] 6.2 `src/agents/__init__.py` oluştur
- [x] 6.3 `QuestionAnalysisState` TypedDict (total=False, **user_grade** dahil!)
- [x] 6.4 **KRİTİK:** `@with_timeout` decorator - state-safe error handling
- [x] 6.5 `GraphNodes` sınıfını yaz
- [x] 6.6 **PARTIAL:** `analyze_input` node - dict döndür, tüm state değil!
- [x] 6.7 **PARTIAL:** `retrieve_kazanimlar` node - user_grade öncelikli
- [x] 6.8 **RETRY:** Node içinde döngü YOK, sadece retry_count artır
- [x] 6.9 `retrieve_textbook` node'unu implemente et
- [x] 6.10 `rerank_results` node'unu implemente et
- [x] 6.11 `generate_response` node'unu implemente et
- [x] 6.12 `handle_error` fallback node'unu implemente et
- [x] 6.13 `conditions.py` - check_analysis_success, check_retrieval_success
- [x] 6.14 **KRİTİK:** Retry mantığı sadece Graph edge'de (max 3x)
- [x] 6.15 `MebRagGraph` sınıfını yaz
- [x] 6.16 Conditional edges tanımla (success/retry/error)
- [x] 6.17 `persistence.py` - PostgresCheckpointer
- [ ] 6.18 `streaming.py` - Token by token streaming
- [ ] 6.19 `/analyze-stream` SSE endpoint'i hazırla
- [x] 6.20 Dev/Prod ortam ayrımı (MemorySaver vs PostgresSaver)
- [ ] 6.21 `graph.invoke()` async metodunu test et
- [ ] 6.22 **DOĞRULAMA:** Retry döngüsü test et, max 3x çalışmalı


### FAZ 7: RAG Pipeline [11/12] ✅
- [x] 7.1 `src/rag/__init__.py` oluştur
- [x] 7.2 `output_models.py` - Pydantic `MatchedKazanim`, `PrerequisiteGap`, `AnalysisOutput`
- [x] 7.3 **KRİTİK:** `llm.with_structured_output(AnalysisOutput)` kullan!
- [x] 7.4 `ResponseGenerator` sınıfını yaz
- [x] 7.5 `_build_prompt` metodunu implemente et
- [x] 7.6 **ENTEGRASYON:** Faz 6 `generate_response` node'unu güncelle
- [x] 7.7 **DB:** `kazanim_prerequisites` Many-to-Many tablosu ekle
- [x] 7.8 `GapFinder` sınıfını yaz (prerequisite lookup)
- [x] 7.9 `find_prerequisites` metodunu implemente et
- [x] 7.10 Prompt'ta "cevabı verme, mantığı anlat" kuralı
- [x] 7.11 AnalysisOutput → API Response dönüşümü
- [ ] 7.12 **DOĞRULAMA:** Structured output JSON garantisi test et

### FAZ 8: API ve Deployment [18/22] ✅
- [x] 8.1 `api/__init__.py` oluştur
- [x] 8.2 `api/models.py` - İç içe Pydantic modeller (KazanimModel, SectionModel, vb.)
- [x] 8.3 `api/main.py` - FastAPI app, CORS, rate limiter
- [x] 8.4 **KRİTİK:** Upload = RAM'den oku, diske YAZMA! (`await file.read()`)
- [x] 8.5 `POST /api/v1/analyze-image` - Faz 5 pipeline + Faz 6 graph
- [x] 8.6 `POST /api/v1/analyze-text` - MebRagGraph.ainvoke()
- [x] 8.7 **STREAMING:** `POST /api/v1/analyze-stream` - SSE endpoint
- [x] 8.8 `astream_events()` ile token by token streaming
- [ ] 8.9 `GET /api/v1/kazanimlar/{grade}/{subject}` endpoint'i
- [x] 8.10 `GET /health` endpoint'i
- [x] 8.11 `_format_response()` - State → API Response dönüşümü
- [x] 8.12 **GÜVENLİK:** `slowapi` rate limiter middleware
- [x] 8.13 **GÜVENLİK:** IP bazlı limit: 10/dk image, 20/dk text, 10/dk stream
- [x] 8.14 `api/routes/feedback.py` - Feedback route
- [x] 8.15 Negatif feedback logging
- [x] 8.16 `Dockerfile` - PyMuPDF/OpenCV sistem bağımlılıkları!
- [x] 8.17 `docker-compose.yml` - Postgres dahil
- [x] 8.18 Healthcheck eklentisi
- [ ] 8.19 `tests/test_api.py` - Endpoint testleri
- [ ] 8.20 Streaming SSE testi
- [ ] 8.21 Rate limit testi
- [ ] 8.22 **DOĞRULAMA:** Uçtan uca test: Image → API → Response


---

## 🔴 KRİTİK KURALLAR

### Semantik Gap Çözümü
```
❌ YANLIŞ: Soru metnini doğrudan kazanım tanımıyla karşılaştırma
✅ DOĞRU: Her kazanım için 50 sentetik soru üret, Soru vs Soru karşılaştır
```

### Semantic Chunking
```
❌ YANLIŞ: Sayfayı 1000 karakterlik parçalara böl
✅ DOĞRU: Ünite → Konu → Alt Başlık hiyerarşisini koru
✅ DOĞRU: [BİLGİ KUTUSU], [ÖRNEK] etiketleri kullan
✅ DOĞRU: Görsel + açıklama birlikte tut
```

### Agent Döngü Riski
```
❌ YANLIŞ: Genel maksatlı LangChain Agent
✅ DOĞRU: LangGraph State Machine (katı akış)
✅ DOĞRU: Her adımda timeout (15-30s)
✅ DOĞRU: Max retry = 2
```

### Multimodal Retrieval
```
❌ YANLIŞ: Sadece metin indeksle
✅ DOĞRU: Görselleri GPT-4o ile caption'la
✅ DOĞRU: Caption embedding ile görsel ara
```

---

## 📁 DOSYA YAPISI

```
meba/
├── config/
│   ├── __init__.py
│   ├── settings.py          # FAZ 1.9
│   └── azure_config.py      # FAZ 1.10
├── src/
│   ├── document_processing/
│   │   ├── __init__.py      # FAZ 2.1
│   │   ├── layout_analyzer.py   # FAZ 2.2-2.6
│   │   ├── semantic_chunker.py  # FAZ 2.7-2.10
│   │   ├── image_extractor.py   # FAZ 2.11-2.14
│   │   └── hierarchy_builder.py # FAZ 2.15
│   ├── database/
│   │   ├── __init__.py      # FAZ 3.1
│   │   ├── models.py        # FAZ 3.2-3.6
│   │   └── db.py            # FAZ 3.7-3.8
│   ├── vector_store/
│   │   ├── __init__.py      # FAZ 4.1
│   │   ├── question_generator.py  # FAZ 4.2-4.5
│   │   ├── index_schema.py       # FAZ 4.6-4.7
│   │   ├── parent_retriever.py   # FAZ 4.9-4.11
│   │   ├── image_retriever.py    # FAZ 4.12-4.14
│   │   └── indexing_pipeline.py  # FAZ 4.15-4.16
│   ├── vision/
│   │   ├── __init__.py      # FAZ 5.1
│   │   ├── azure_vision_client.py  # FAZ 5.2-5.5
│   │   ├── preprocessor.py       # FAZ 5.6-5.7
│   │   └── pipeline.py           # FAZ 5.8-5.9
│   ├── agents/
│   │   ├── __init__.py      # FAZ 6.1
│   │   ├── state.py         # FAZ 6.2
│   │   ├── graph.py         # FAZ 6.3-6.6
│   │   ├── nodes.py         # FAZ 6.7-6.13
│   │   └── conditions.py    # FAZ 6.6 (conditional logic)
│   └── rag/
│       ├── __init__.py      # FAZ 7.1
│       ├── prompts.py       # FAZ 7.2-7.3
│       ├── matcher.py       # FAZ 7.4-7.6
│       └── scoring.py       # FAZ 7.7-7.8
├── api/
│   ├── __init__.py          # FAZ 8.1
│   ├── main.py              # FAZ 8.2-8.7
│   └── routes/
│       └── analysis.py      # FAZ 8.4-8.6
├── tests/
│   ├── test_config.py       # FAZ 1.11
│   └── test_api.py          # FAZ 8.11
├── data/
│   ├── pdfs/kazanimlar/     # MEB kazanım PDF'leri
│   ├── pdfs/ders_kitaplari/ # Ders kitabı PDF'leri
│   └── processed/           # İşlenmiş veriler
├── .env                     # FAZ 1.8
├── .env.example             # FAZ 1.3
├── requirements.txt         # FAZ 1.2
├── Dockerfile               # FAZ 8.9
└── docker-compose.yml       # FAZ 8.10
```

---

## 🧪 DOĞRULAMA TESTLERİ

### Faz 1 Testi
```python
from config.settings import get_settings
settings = get_settings()
assert settings.doc_intelligence_endpoint is not None
print("✅ Faz 1 tamamlandı")
```

### Faz 4 Testi
```python
retriever = ParentDocumentRetriever(index, db)
results = await retriever.search("2/3 + 1/5 kaçtır?")
assert len(results) > 0
assert "M.5" in results[0]["kazanim"]["code"]  # Kesir konusu
print("✅ Faz 4 tamamlandı")
```

### Faz 6 Testi
```python
graph = MebRagGraph()
result = await graph.invoke({
    "raw_input": "test_soru.jpg",
    "input_type": "image"
})
assert result["current_step"] != "error_handled"
print("✅ Faz 6 tamamlandı")
```

---

## ⚠️ HATA DURUMLARINDA

1. **Azure bağlantı hatası:** `.env` dosyasını kontrol et
2. **Timeout:** STEP_TIMEOUT değerini artır (max 60s)
3. **Boş sonuç:** Sentetik soru sayısını artır (50 → 100)
4. **Memory hatası:** Batch boyutunu küçült, async kullan
