# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Meba is an AI-powered educational platform for personalized tutoring aligned with the Turkish Ministry of National Education (MEB) curriculum. It uses a RAG architecture with LangGraph state machine to provide pedagogically-correct responses to student questions.

**Stack:** Python 3.11 + FastAPI + LangGraph + Azure AI Services (Search, Document Intelligence, OpenAI)

## Commands

### Development
```bash
# Docker setup (preferred)
docker compose up --build

# First-time data ingestion
docker compose run --rm api python scripts/process_pdfs.py

# Access: API http://localhost:8001, Docs http://localhost:8001/docs, Frontend http://localhost:3001
```

### Testing
```bash
pytest tests/                          # All tests
pytest tests/test_agents.py            # LangGraph workflow tests
pytest tests/test_rag_api.py           # API endpoint tests
pytest tests/test_vector_store.py      # Search and retrieval tests
```

### Utility Scripts
```bash
python scripts/process_pdfs.py         # Ingest and index PDFs
python scripts/view_stats.py           # View system statistics
python scripts/create_indexes.py       # Create/recreate Azure indexes
```

## Architecture

### Request Flow
```
Question (Text/Image) → Input Analysis → Kazanım Retrieval → Textbook Retrieval → Reranking → Response Generation
```

### Core Components

**LangGraph State Machine** (`src/agents/`): Stateful workflow with nodes for input analysis, retrieval, reranking, and response generation. Uses `QuestionAnalysisState` (TypedDict with `total=False`). Nodes return only modified fields, not full state.

**FastAPI Backend** (`api/`): Routes for `/analyze/image`, `/analyze/text`, `/analyze/stream`, `/chat`. Rate-limited with CORS middleware.

**Vector Store** (`src/vector_store/`): Azure AI Search with hybrid search (vector + keyword + semantic reranking). Four indexes: kazanimlar, kitaplar, images, sentetik-sorular.

**RAG Pipeline** (`src/rag/`): Response generation with structured output, question analysis, gap finder, reranker, and supervisor for routing.

**Document Processing** (`src/document_processing/`): Azure Document Intelligence for layout analysis, semantic chunking preserving hierarchy (Unit → Topic → Section).

**Vision** (`src/vision/`): GPT-4o Vision for image/question analysis with grade estimation.

## Critical Patterns

### Grade Filtering
Always filter by grade/subject to prevent incorrect curriculum level:
```python
from src.agents.state import get_effective_grade
grade = get_effective_grade(state)  # user_grade takes priority over ai_estimated_grade

# School Mode: exact grade match
filter = f"grade eq {grade}"
# YKS/Exam Mode: cumulative grades
filter = f"grade le {grade}"
```

### State Updates
Nodes must return partial state updates only:
```python
async def my_node(state: QuestionAnalysisState) -> Dict[str, Any]:
    return {"question_text": text, "status": "processing"}  # Only modified fields
```

### Error Handling
All nodes require timeout decorators:
```python
@with_timeout(30.0)
@log_node_execution("node_name")
async def my_node(state):
    try:
        # implementation
    except Exception as e:
        return {"error": str(e), "status": "failed"}
```

### Structured Output
Use `with_structured_output` for guaranteed JSON parsing:
```python
llm = AzureChatOpenAI(...).with_structured_output(AnalysisOutput)
response = llm.invoke(prompt)  # Returns valid Pydantic instance
```

## Key Configuration

Environment variables in `.env`:
- `AZURE_SEARCH_*` - Azure AI Search credentials and index names
- `AZURE_OPENAI_*` - Azure OpenAI endpoint and deployments
- `DOCUMENTINTELLIGENCE_*` - Azure Document Intelligence
- `DATABASE_URL` - SQLite (dev) or PostgreSQL (prod)

## Development Notes

- System prompts and content are Turkish-centric
- Cost optimization is important (batch embeddings in groups of 16, cache aggressively)
- Max 3 retries with filter relaxation on retrieval failures
- Use gpt-4o-mini for synthetic question generation (cheaper)
- Detailed implementation guide available at `docs/IMPLEMENTATION_GUIDE.md`
