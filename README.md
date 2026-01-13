# Meba - MEB Mufredat Uyumlu Yapay Zeka Egitim Asistani

**Yediiklim Okullari Kisisellestirilmis Yapay Zeka Asistani** - Turk Milli Egitim Bakanligi (MEB) mufredatiyla tam uyumlu, RAG (Retrieval-Augmented Generation) ve LangGraph state machine mimarisi kullanan yapay zeka destekli egitim platformu.

## Ozellikler

- **Akilli Soru Analizi**: Metin ve gorsel tabanli soru analizi (GPT-4o Vision)
- **Kazanim Eslestirme**: Otomatik MEB kazanim tespiti ve takibi
- **Pedagojik Yanitlar**: Ders kitabi kaynakli, sinif seviyesine uygun aciklamalar
- **Onkoşul Analizi**: Eksik bilgi tespiti ve ogrenme yolu onerisi
- **Sinav Olusturma**: Kisisellestirilmis PDF sinav uretimi
- **Ilerleme Takibi**: Ogrenci bazli kazanim ilerleme izleme
- **Coklu Rol Destegi**: Ogrenci, Ogretmen ve Admin panelleri

## Teknoloji Yigini

### Backend
| Teknoloji | Versiyon | Amac |
|-----------|----------|------|
| Python | 3.11 | Ana dil |
| FastAPI | 0.109+ | REST API framework |
| LangGraph | 0.0.10+ | State machine workflow |
| SQLAlchemy | 2.0+ | ORM |
| PostgreSQL | 15 | Veritabani |
| Redis | 7 | Cache katmani |

### Frontend
| Teknoloji | Versiyon | Amac |
|-----------|----------|------|
| React | 19 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7.2 | Build tool |
| Tailwind CSS | 3.4 | Styling |
| React Query | 5.90 | Data fetching |

### Azure Servisleri
| Servis | Amac |
|--------|------|
| Azure OpenAI | GPT-4o, GPT-5.2, text-embedding-3-large |
| Azure AI Search | Hybrid vector/keyword arama |
| Azure Document Intelligence | PDF layout analizi |

### DevOps
- Docker & Docker Compose
- Multi-stage builds
- Health checks
- Firebase Authentication

## Hizli Baslangic

### Gereksinimler
- Docker & Docker Compose
- Azure hesabi (OpenAI, Search, Document Intelligence)
- Firebase projesi

### Kurulum

1. **Repository'yi klonlayin**
```bash
git clone https://github.com/your-org/meba.git
cd meba
```

2. **Environment dosyasini olusturun**
```bash
cp .env.example .env
# .env dosyasini duzenleyin
```

3. **Servisleri baslatin**
```bash
docker compose up --build
```

4. **Ilk PDF yukleme (bir kerelik)**
```bash
docker compose run --rm api python scripts/process_pdfs.py
```

### Erisim Noktalari
| Servis | URL |
|--------|-----|
| Frontend | http://localhost:3001 |
| API | http://localhost:8001 |
| Swagger Docs | http://localhost:8001/docs |

## Proje Yapisi

```
Meba/
├── api/                          # FastAPI backend
│   ├── auth/                     # Firebase JWT & OAuth
│   ├── routes/                   # API endpoint'leri
│   │   ├── analysis.py           # Soru analizi & RAG
│   │   ├── conversations.py      # Sohbet gecmisi
│   │   ├── progress.py           # Kazanim takibi
│   │   ├── exams.py              # Sinav olusturma
│   │   ├── admin/                # Admin islemleri
│   │   ├── classrooms/           # Sinif yonetimi
│   │   └── assignments/          # Odev yonetimi
│   ├── models.py                 # Pydantic modelleri
│   └── main.py                   # FastAPI app
│
├── src/                          # Core business logic
│   ├── agents/                   # LangGraph state machine
│   │   ├── graph.py              # RAG workflow
│   │   ├── nodes.py              # Islem node'lari
│   │   ├── state.py              # State tanimlari
│   │   └── conditions.py         # Edge kosullari
│   ├── rag/                      # Response generation
│   │   ├── reranker.py           # LLM-based reranking
│   │   ├── gap_finder.py         # Onkosul tespiti
│   │   ├── teacher_synthesizer.py # Ogretmen aciklamalari
│   │   └── output_models.py      # Structured outputs
│   ├── vector_store/             # Azure AI Search
│   │   ├── hybrid_retriever.py   # Hibrit arama
│   │   └── indexing_pipeline.py  # Indexleme
│   ├── document_processing/      # PDF isleme
│   │   ├── layout_analyzer.py    # Layout analizi
│   │   ├── semantic_chunker.py   # Akilli parcalama
│   │   └── image_extractor.py    # Gorsel cikarma
│   ├── database/                 # SQLAlchemy modelleri
│   ├── cache/                    # Redis/Memory cache
│   ├── vision/                   # GPT-4o Vision
│   ├── exam/                     # Sinav olusturma
│   └── utils/                    # Yardimci araclar
│
├── frontend-new/                 # React SPA
│   ├── src/
│   │   ├── pages/                # Sayfa bileşenleri
│   │   │   ├── Chat.tsx          # AI sohbet arayuzu
│   │   │   ├── Dashboard.tsx     # Ogrenci paneli
│   │   │   ├── Kazanimlar.tsx    # Ilerleme takibi
│   │   │   ├── teacher/          # Ogretmen sayfalari
│   │   │   └── admin/            # Admin sayfalari
│   │   ├── components/           # Yeniden kullanilabilir
│   │   ├── context/              # React Context
│   │   ├── hooks/                # Custom hooks
│   │   └── utils/                # Yardimci fonksiyonlar
│   └── package.json
│
├── config/                       # Yapilandirma
│   ├── settings.py               # Pydantic settings
│   └── azure_config.py           # Azure client factory
│
├── scripts/                      # Yardimci scriptler
│   ├── process_pdfs.py           # PDF yukleme
│   ├── create_indexes.py         # Index olusturma
│   └── view_stats.py             # Istatistikler
│
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest fixtures
│   ├── test_agents.py            # Workflow testleri
│   └── test_rag_api.py           # API testleri
│
├── docker-compose.yml            # Servis orkestrasyon
├── Dockerfile                    # Backend container
└── requirements.txt              # Python bagimliliklar
```

## RAG Pipeline Akisi

```
Ogrenci Sorusu (Metin/Gorsel)
         │
         ▼
┌─────────────────────────────────────────┐
│  1. ANALYZE_INPUT                       │
│  - Mesaj tipi siniflandirma             │
│  - Vision API (gorsel ise)              │
│  - Akademik/sohbet yonlendirme          │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  2. UNDERSTAND_QUERY (SOTA)             │
│  - LLM tabanli mufredat terminolojisi   │
│  - Zenginlestirilmis sorgu olusturma    │
│  - Ders/sinif cikarimi                  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  3. RETRIEVE_KAZANIMLAR                 │
│  - Hibrit arama (vector + keyword)      │
│  - Sinif filtreleme (okul/YKS modu)     │
│  - Sentetik soru eslestirme             │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  4. RETRIEVE_TEXTBOOK                   │
│  - Ders kitabi parcalari                │
│  - Ilgili gorseller/diyagramlar         │
│  - Hiyerarsi koruma                     │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  5. RERANK_RESULTS                      │
│  - LLM tabanli ilgililik skorlama       │
│  - Blended skor hesaplama               │
│  - Hard cutoff filtreleme (0.25)        │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  6. TRACK_PROGRESS                      │
│  - Yuksek guvenli kazanim takibi (≥0.50)│
│  - Kullanici ilerlemesi guncelleme      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  7. FIND_PREREQUISITE_GAPS              │
│  - Onkosul iliskileri analizi           │
│  - Eksik bilgi tespiti                  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  8. SYNTHESIZE_INTERDISCIPLINARY        │
│  - Disiplinlerarasi baglantilar         │
│  - Ogrenme yolu onerisi                 │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  9. GENERATE_RESPONSE                   │
│  - Yapilandirilmis LLM yaniti           │
│  - Cozum adimlari                       │
│  - Kaynak alintilari                    │
└─────────────────────────────────────────┘
         │
         ▼
    FINAL YAPIT
    (Kazanimlar, Cozum, Kaynaklar)
```

## Azure AI Search Indexleri

| Index | Amac | Alanlar |
|-------|------|---------|
| `meb-kazanimlar-index` | Ogrenme hedefleri | code, description, grade, subject |
| `meb-kitaplar-index` | Ders kitabi parcalari | content, hierarchy_path, grade |
| `meb-images-index` | Cikarilmis gorseller | caption, page_number, grade |
| `meb-sentetik-sorular-index` | Uretilmis sorular | question_text, kazanim_code |

## API Endpoint'leri

### Analiz
| Method | Path | Amac |
|--------|------|------|
| POST | `/analyze/image` | Gorsel soru analizi |
| POST | `/analyze/text` | Metin soru analizi |
| POST | `/analyze/image-stream` | Streaming gorsel analiz |
| POST | `/analyze/text-stream` | Streaming metin analiz |
| POST | `/chat` | Birlesik sohbet arayuzu |

### Ilerleme Takibi
| Method | Path | Amac |
|--------|------|------|
| GET | `/users/me/progress` | Takip edilen kazanimlar |
| POST | `/users/me/progress/track` | Yeni kazanim takibi |
| PUT | `/users/me/progress/{code}/understood` | Anlasildi isareti |
| GET | `/users/me/progress/stats` | Ilerleme istatistikleri |

### Sohbet Gecmisi
| Method | Path | Amac |
|--------|------|------|
| GET | `/conversations` | Sohbet listesi |
| POST | `/conversations` | Yeni sohbet |
| GET | `/conversations/{id}` | Sohbet detayi |
| DELETE | `/conversations/{id}` | Sohbet silme |

### Sinav Olusturma
| Method | Path | Amac |
|--------|------|------|
| POST | `/exams/generate` | Sinav PDF olustur |
| GET | `/exams` | Sinav listesi |
| GET | `/exams/{id}/download` | Sinav indir |

### Kimlik Dogrulama
| Method | Path | Amac |
|--------|------|------|
| POST | `/auth/register/complete` | Kayit tamamla |
| GET | `/auth/me` | Kullanici bilgisi |
| PUT | `/users/me` | Profil guncelle |

## Environment Degiskenleri

```env
# Azure Document Intelligence
DOCUMENTINTELLIGENCE_ENDPOINT=https://...
DOCUMENTINTELLIGENCE_API_KEY=...

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://...
AZURE_SEARCH_API_KEY=...

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/meb_rag

# Redis
REDIS_URL=redis://redis:6379
REDIS_ENABLED=true

# Firebase
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json

# Application
DEBUG=false
LOG_LEVEL=INFO
```

## Gelistirme

### Lokal Gelistirme (Docker olmadan)

```bash
# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8001

# Frontend
cd frontend-new
npm install
npm run dev
```

### Test Calistirma

```bash
# Tum testler
pytest tests/

# Belirli test dosyasi
pytest tests/test_agents.py -v

# Coverage ile
pytest tests/ --cov=src --cov-report=html

# Sadece unit testler
pytest tests/ -m "unit"
```

### Script Kullanimi

```bash
# PDF yukleme
python scripts/process_pdfs.py

# Index olusturma
python scripts/create_indexes.py

# Istatistik goruntuleme
python scripts/view_stats.py
```

## Kritik Kaliplar

### 1. Sinif Filtreleme (Her Zaman Gerekli)

```python
from src.agents.state import get_effective_grade

grade = get_effective_grade(state)  # user_grade oncelikli

if state.get("is_exam_mode"):
    filter = f"grade le {grade}"    # YKS: kumulatif
else:
    filter = f"grade eq {grade}"    # Okul: tam eslesme
```

### 2. Node State Guncellemeleri

```python
# DOGRU - sadece degisen alanlar
async def my_node(state: QuestionAnalysisState) -> Dict[str, Any]:
    return {"matched_kazanimlar": results, "status": "processing"}

# YANLIS - tum state donme
# return {**state, "matched_kazanimlar": results}
```

### 3. Node Decorator'lari

```python
@with_timeout(30.0)
@log_node_execution("node_name")
async def my_node(state: QuestionAnalysisState) -> Dict[str, Any]:
    try:
        return {"result": data, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}  # Raise yapma!
```

### 4. Circuit Breaker

```python
from src.utils.resilience import with_resilience

@with_resilience(circuit_name="azure_search")
async def search_with_resilience():
    return await azure_search_client.search(...)
```

## Veritabani Modelleri

### Ana Tablolar

| Tablo | Amac |
|-------|------|
| `users` | Kullanici profilleri |
| `user_kazanim_progress` | Kazanim takibi |
| `conversations` | Sohbet oturumlari |
| `messages` | Sohbet mesajlari |
| `schools` | Okul kiracilari (SaaS) |
| `classrooms` | Sinif yonetimi |
| `assignments` | Odev yonetimi |
| `assignment_submissions` | Odev teslimleri |

### Iliskiler

```
User (1) ─────< (N) UserKazanimProgress
User (1) ─────< (N) Conversation
Conversation (1) ─────< (N) Message
School (1) ─────< (N) User
Classroom (1) ─────< (N) ClassroomEnrollment
Assignment (1) ─────< (N) AssignmentSubmission
Kazanim (N) >─────< (N) Kazanim (prerequisites)
```

## Performans Optimizasyonlari

### Cache Stratejisi
- **Embedding Cache**: 24 saat TTL, %90 hit rate
- **Response Cache**: Conversation bazli
- **Database Query Cache**: 5-60 dakika

### Paralel Islem
```python
# Hibrit arama paralel calisir
kazanim_search(), question_search() -> gather() (25s timeout)
```

### Token Yonetimi
- Max context: 128,000 token
- Reserved output: 4,096 token
- Warning threshold: %80

## Maliyet Optimizasyonu

1. **Embedding Batch**: 16'li gruplar, 0.5s aralik
2. **Model Secimi**: gpt-4o-mini sentetik sorular icin
3. **Cache**: Embedding'ler 24 saat cache
4. **Secici Islem**: Vision API sadece gorsel sorular icin
5. **Token Verimliligi**: Max 10 kazanim, max 5 kitap parcasi

## Lisans

Bu proje ozel lisans altindadir. Yediiklim Okullari'na aittir.

## Iletisim

- **Proje**: Yediiklim Okullari AI Egitim Asistani
- **Gelistirici**: Meba Development Team
