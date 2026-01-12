# Meba - AI-Powered Educational Platform

Meba is an intelligent tutoring system aligned with the Turkish Ministry of National Education (MEB) curriculum. It uses Retrieval-Augmented Generation (RAG) with LangGraph state machines to provide pedagogically-correct, curriculum-grounded responses to student questions.

## Features

- **Curriculum-Aligned Responses**: All answers are grounded in official MEB textbooks and kazanımlar (learning objectives)
- **Image Question Analysis**: Upload photos of homework problems for instant analysis using GPT-4o Vision
- **Grade-Appropriate Filtering**: Responses are filtered by grade level to ensure age-appropriate content
- **Progress Tracking**: Track mastery of individual kazanımlar over time
- **Prerequisite Gap Detection**: Identifies missing foundational knowledge and suggests remediation
- **Exam Mode**: Special mode for YKS (university entrance exam) preparation with cumulative grade access

## Tech Stack

### Backend
- **Python 3.11** with **FastAPI**
- **LangGraph** for stateful AI workflows
- **Azure AI Search** for hybrid vector + keyword search
- **Azure OpenAI** (GPT-4o, GPT-4o-mini, text-embedding-3-large)
- **Azure Document Intelligence** for PDF processing
- **SQLAlchemy** with PostgreSQL/SQLite
- **JWT** authentication with Google OAuth support

### Frontend
- **React 19** with **TypeScript**
- **Vite** for development and building
- **Tailwind CSS** for styling
- **React Query** for data fetching
- **React Router** for navigation

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Azure account with:
  - Azure AI Search
  - Azure OpenAI
  - Azure Document Intelligence

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/meba.git
   cd meba
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

3. **Start the services**
   ```bash
   docker compose up --build
   ```

4. **Ingest curriculum content (first time only)**
   ```bash
   docker compose run --rm api python scripts/process_pdfs.py
   ```

5. **Access the application**
   - Frontend: http://localhost:3001
   - API Documentation: http://localhost:8001/docs

## Architecture

### System Overview

```
┌─────────────┐     ┌─────────────────────────────────────────────────────────┐
│   Frontend  │────▶│                      FastAPI Backend                     │
│  (React)    │     │                                                          │
└─────────────┘     │  ┌─────────────────────────────────────────────────────┐ │
                    │  │                  LangGraph Workflow                  │ │
                    │  │                                                      │ │
                    │  │  analyze_input ──▶ retrieve_kazanimlar ──▶ retrieve │ │
                    │  │       │                    │              _textbook  │ │
                    │  │       ▼                    ▼                  │      │ │
                    │  │  [Vision API]       [Azure Search]            ▼      │ │
                    │  │                                          rerank      │ │
                    │  │                                              │       │ │
                    │  │       ┌───────────────────┬──────────────────┘       │ │
                    │  │       ▼                   ▼                          │ │
                    │  │  find_gaps ──▶ synthesize ──▶ generate_response     │ │
                    │  │                                      │               │ │
                    │  └──────────────────────────────────────┼───────────────┘ │
                    │                                         ▼                  │
                    │                               [Structured Response]        │
                    └────────────────────────────────────────────────────────────┘
                              │           │              │
                              ▼           ▼              ▼
                    ┌──────────────┐ ┌──────────┐ ┌─────────────┐
                    │ Azure Search │ │ Azure    │ │ PostgreSQL  │
                    │  (4 indexes) │ │ OpenAI   │ │  Database   │
                    └──────────────┘ └──────────┘ └─────────────┘
```

### Azure Search Indexes

| Index | Content |
|-------|---------|
| `meb-kazanimlar-index` | Learning objectives with grade/subject metadata |
| `meb-kitaplar-index` | Textbook chunks preserving Unit → Topic → Section hierarchy |
| `meb-images-index` | Extracted images with GPT-4o generated captions |
| `meb-sentetik-sorular-index` | Generated practice questions |

### LangGraph Nodes

1. **analyze_input**: Processes text or uses GPT-4o Vision to extract question from images
2. **retrieve_kazanimlar**: Hybrid search for matching learning objectives
3. **retrieve_textbook**: Fetches relevant textbook content with grade filtering
4. **rerank_results**: LLM-based reranking for quality
5. **track_progress**: Auto-tracks high-confidence matches to user progress
6. **find_prerequisite_gaps**: Identifies missing foundational knowledge
7. **synthesize_interdisciplinary**: Generates learning path suggestions
8. **generate_response**: Produces structured response with solution steps

## API Endpoints

### Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analyze/image` | POST | Analyze question from image |
| `/analyze/text` | POST | Analyze text question |
| `/analyze/stream` | POST | Streaming response |
| `/chat` | POST | Unified chat interface |

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | User registration |
| `/auth/login` | POST | JWT login |
| `/auth/google` | POST | Google OAuth |

### Progress
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/me/progress` | GET | List tracked kazanımlar |
| `/users/me/progress/{code}` | PUT | Mark kazanım as understood |
| `/users/me/progress/stats` | GET | Overall statistics |

### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/cache/stats` | GET | Cache statistics |

## Project Structure

```
Meba/
├── api/                      # FastAPI backend
│   ├── auth/                 # Authentication (JWT, Google OAuth)
│   ├── routes/               # API endpoint handlers
│   ├── models.py             # Pydantic models
│   └── main.py               # Application entry point
├── src/                      # Core business logic
│   ├── agents/               # LangGraph state machine
│   ├── cache/                # Caching layer
│   ├── database/             # SQLAlchemy ORM models
│   ├── document_processing/  # PDF ingestion pipeline
│   ├── rag/                  # Response generation components
│   ├── utils/                # Utilities (tokens, resilience)
│   ├── vector_store/         # Azure Search integration
│   └── vision/               # GPT-4o Vision processing
├── config/                   # Configuration & Azure clients
├── scripts/                  # Utility scripts
├── tests/                    # pytest test suite
├── frontend-new/             # React frontend
├── data/                     # Data storage
├── docs/                     # Documentation
└── docker-compose.yml        # Container orchestration
```

## Development

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_agents.py -v

# By category
pytest tests/ -m "unit"
pytest tests/ -m "integration"

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Utility Scripts

```bash
# Ingest PDF textbooks
python scripts/process_pdfs.py

# Create/recreate Azure Search indexes
python scripts/create_indexes.py

# View system statistics
python scripts/view_stats.py

# Browse synthetic questions
python scripts/view_questions.py
```

### Frontend Development

```bash
cd frontend-new
npm install
npm run dev      # Development server at localhost:5173
npm run build    # Production build
```

## Configuration

### Environment Variables

```ini
# Azure Document Intelligence
DOCUMENTINTELLIGENCE_ENDPOINT=https://...
DOCUMENTINTELLIGENCE_API_KEY=...

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://...
AZURE_SEARCH_API_KEY=...
AZURE_SEARCH_INDEX_KAZANIM=meb-kazanimlar-index
AZURE_SEARCH_INDEX_KITAP=meb-kitaplar-index
AZURE_SEARCH_INDEX_IMAGES=meb-images-index
AZURE_SEARCH_INDEX_QUESTIONS=meb-sentetik-sorular-index

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large-957047

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/mebrag

# Authentication
JWT_SECRET_KEY=your-secret-key

# Application
DEBUG=false
LOG_LEVEL=INFO
```

### Key Settings (config/settings.py)

| Setting | Default | Description |
|---------|---------|-------------|
| `rag_confidence_threshold` | 0.50 | Minimum score for kazanım matches |
| `rag_kazanim_top_k` | 5 | Max kazanımlar to return |
| `rag_textbook_top_k` | 5 | Max textbook chunks to return |
| `retrieval_max_retries` | 3 | Retries with filter relaxation |
| `timeout_generate_response` | 60.0s | Response generation timeout |

## Documentation

Detailed implementation documentation is available in the `docs/` directory:

- `IMPLEMENTATION_GUIDE.md` - 8-phase implementation checklist
- `phases/faz1_proje_altyapisi.md` - Project infrastructure
- `phases/faz2_pdf_isleme.md` - PDF processing
- `phases/faz3_veritabani.md` - Database setup
- `phases/faz4_azure_search.md` - Vector store & hybrid search
- `phases/faz5_azure_vision.md` - Vision API integration
- `phases/faz6_agentic_sistem.md` - LangGraph agents
- `phases/faz7_rag_pipeline.md` - Response generation
- `phases/faz8_api_deployment.md` - API & Docker deployment

## License

This project is proprietary software. All rights reserved.
