# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Meba is an AI-powered educational platform for personalized tutoring aligned with the Turkish Ministry of National Education (MEB) curriculum. It uses RAG (Retrieval-Augmented Generation) with LangGraph state machines to provide pedagogically-correct responses grounded in official textbooks and kazanımlar (learning objectives).

**Stack:** Python 3.11 + FastAPI + LangGraph + React 19 + Azure AI Services

## Quick Commands

### Development
```bash
docker compose up --build                    # Start all services
docker compose run --rm api python scripts/process_pdfs.py  # First-time PDF ingestion
```

### Testing
```bash
pytest tests/                                # All tests
pytest tests/test_agents.py -v               # LangGraph workflow tests
pytest tests/test_rag_api.py -v              # API endpoint tests
pytest tests/ -m "unit"                      # Only unit tests
pytest tests/ --cov=src --cov-report=html    # With coverage
```

### Scripts
```bash
python scripts/process_pdfs.py               # Ingest PDFs from data/pdfs/
python scripts/create_indexes.py             # Create Azure Search indexes
python scripts/view_stats.py                 # View system statistics
```

### Access Points
- Frontend: http://localhost:3001
- API: http://localhost:8001
- Swagger Docs: http://localhost:8001/docs

## Project Structure

```
Meba/
├── api/                      # FastAPI backend
│   ├── auth/                 # JWT & Google OAuth
│   ├── routes/               # API endpoints
│   ├── models.py             # Pydantic request/response models
│   └── main.py               # FastAPI app with lifespan
├── src/                      # Core business logic
│   ├── agents/               # LangGraph state machine (graph.py, nodes.py, state.py)
│   ├── cache/                # In-memory caching with TTL
│   ├── database/             # SQLAlchemy models (User, Progress, Conversation)
│   ├── document_processing/  # PDF layout analysis & semantic chunking
│   ├── rag/                  # Response generation, reranking, gap finder
│   ├── utils/                # Token manager, circuit breaker, resilience
│   ├── vector_store/         # Azure AI Search hybrid retrieval
│   └── vision/               # GPT-4o Vision image analysis
├── config/                   # Settings & Azure client factories
├── scripts/                  # Utility scripts
├── tests/                    # pytest test suite
├── frontend-new/             # React + Vite + TypeScript + Tailwind
├── data/                     # PDFs, processed files, images
├── docs/                     # Implementation guides (8 phases)
└── docker-compose.yml        # Full stack orchestration
```

## Request Flow

```
Question → analyze_input → retrieve_kazanimlar → retrieve_textbook → rerank_results → track_progress → find_prerequisite_gaps → synthesize_interdisciplinary → generate_response → Response
```

## Critical Patterns

### 1. Grade Filtering (Always Required)

```python
from src.agents.state import get_effective_grade

grade = get_effective_grade(state)  # user_grade takes priority over ai_estimated_grade

if state.get("is_exam_mode"):
    filter = f"grade le {grade}"  # YKS/exam: cumulative grades
else:
    filter = f"grade eq {grade}"  # School mode: exact grade match
```

### 2. LangGraph Node State Updates

Nodes must return **partial state only** - just the fields being modified:

```python
# CORRECT
async def my_node(state: QuestionAnalysisState) -> Dict[str, Any]:
    return {"matched_kazanimlar": results, "status": "processing"}

# WRONG - don't return entire state
# return {**state, "matched_kazanimlar": results}
```

### 3. Error Handling with Decorators

All nodes require timeout and error handling decorators:

```python
@with_timeout(30.0)
@log_node_execution("node_name")
async def my_node(state: QuestionAnalysisState) -> Dict[str, Any]:
    try:
        # implementation
        return {"result": data, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}  # Don't raise!
```

### 4. Structured Output for LLM Responses

```python
from langchain_openai import AzureChatOpenAI
from src.rag.output_models import AnalysisOutput

llm = AzureChatOpenAI(...).with_structured_output(AnalysisOutput)
response = llm.invoke(prompt)  # Returns Pydantic instance, not string
```

### 5. Circuit Breaker for External Services

```python
from src.utils.resilience import with_resilience

@with_resilience(circuit_name="azure_search")
async def search_with_resilience():
    return await azure_search_client.search(...)
```

## Key State Fields (QuestionAnalysisState)

**Input:**
- `question_text`, `question_image_base64`
- `user_grade`, `subject`, `is_exam_mode`
- `conversation_id`, `user_id`

**Output:**
- `matched_kazanimlar`: List of matched learning objectives with scores
- `related_chunks`: Textbook content chunks
- `prerequisite_gaps`: Missing prerequisite knowledge
- `response`: Final structured response with solution steps

## Azure Search Indexes

| Index | Purpose |
|-------|---------|
| `meb-kazanimlar-index` | Learning objectives (kazanımlar) |
| `meb-kitaplar-index` | Textbook chunks with hierarchy |
| `meb-images-index` | Extracted images with captions |
| `meb-sentetik-sorular-index` | Generated practice questions |

## API Routes Summary

| Route | Purpose |
|-------|---------|
| `/analyze/image`, `/analyze/text` | Question analysis |
| `/chat` | Unified chat with follow-up support |
| `/auth/*` | Registration, login, OAuth |
| `/users/me/progress/*` | Kazanım progress tracking |
| `/conversations/*` | Conversation management |
| `/health` | System health check |

## Cost Optimization Notes

- Batch embeddings in groups of 16 with 1s delay
- Use `gpt-4o-mini` for synthetic question generation
- Cache embeddings and analysis results aggressively
- Max 3 retrieval retries with filter relaxation

## Environment Variables

Required in `.env`:
- `AZURE_SEARCH_*` - Azure AI Search credentials
- `AZURE_OPENAI_*` - Azure OpenAI endpoint and deployments
- `DOCUMENTINTELLIGENCE_*` - Azure Document Intelligence
- `DATABASE_URL` - SQLite (dev) or PostgreSQL (prod)
- `JWT_SECRET_KEY` - Authentication secret

## Frontend Notes

- React 19 with Vite and TypeScript
- Tailwind CSS for styling
- React Query for data fetching
- Routes: `/` (landing), `/panel` (dashboard), `/sohbet` (chat), `/giris` (login)
- API calls via axios to `/api/*` (proxied by nginx)
