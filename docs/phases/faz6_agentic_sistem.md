# Faz 6: LangGraph State Machine Tasarımı

## 🎯 Amaç
Sonsuz döngü riskini ortadan kaldırmak için LangGraph ile katı (rigid) bir State Machine.

---

## ⚠️ KRİTİK: Retry Mantığı

| Sorun | Hata | Düzeltme |
|-------|------|----------|
| Çift retry | Node + Graph = 4 deneme | Sadece **Graph edge** ile retry |
| Return tipi | Tüm state | **Partial update** (dict) |
| Grade | AI tahmini | **user_grade** öncelikli |

---

## 🔧 Uygulama Adımları

### 6.1 Ek Bağımlılıklar (requirements.txt)

```txt
# LangGraph Persistence
langgraph-checkpoint-postgres>=0.0.3
psycopg2-binary>=2.9.9
asyncpg>=0.29.0
```

### 6.2 State Tanımı (user_grade ekli!)

```python
# src/agents/state.py
from typing import TypedDict, Literal, Optional, List

class QuestionAnalysisState(TypedDict, total=False):
    """
    total=False: Tüm alanlar opsiyonel, partial update için gerekli
    """
    # Input
    raw_input: str
    input_type: Literal["image", "text"]
    user_grade: Optional[int]    # KRİTİK: Frontend'den gelir, öncelikli!
    user_subject: Optional[str]  # İsteğe bağlı ders filtresi
    
    # Soru Analizi Sonucu
    extracted_text: str
    question_topics: List[str]
    estimated_grade: Optional[int]  # AI tahmini (fallback)
    question_type: str
    
    # Retrieval Sonucu
    matched_kazanimlar: List[dict]
    matched_textbook_sections: List[dict]
    retrieval_scores: List[float]
    
    # Reranking Sonucu
    top_kazanimlar: List[dict]
    top_sections: List[dict]
    
    # Final Cevap
    gap_analysis: dict
    explanation: str
    recommendations: List[str]
    
    # Meta
    current_step: str
    error: Optional[str]
    retry_count: int
```

### 6.3 Timeout Decorator (State-Safe)

```python
# src/agents/decorators.py
import asyncio
from functools import wraps

def with_timeout(seconds: int):
    """
    Timeout decorator - STATE YAPISINI BOZMAZ!
    Hata durumunda {"error": ...} döndürür.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, state: dict) -> dict:
            try:
                return await asyncio.wait_for(
                    func(self, state), 
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                # State yapısını koruyarak error döndür
                return {
                    "error": f"Timeout: {func.__name__} {seconds}s aşıldı",
                    "current_step": f"{func.__name__}_timeout"
                }
            except Exception as e:
                return {
                    "error": f"Exception in {func.__name__}: {str(e)}",
                    "current_step": f"{func.__name__}_error"
                }
        return wrapper
    return decorator
```

### 6.4 Node'lar (Partial Update!)

```python
# src/agents/nodes.py
from src.agents.decorators import with_timeout
from src.agents.state import QuestionAnalysisState
from src.vision.pipeline import QuestionAnalysisPipeline
from src.vector_store.parent_retriever import ParentDocumentRetriever
from typing import Dict, Any

class GraphNodes:
    """
    Her node PARTIAL UPDATE döndürür.
    LangGraph mevcut state ile otomatik merge eder.
    """
    
    def __init__(self, vision_pipeline, retriever, llm):
        self.vision_pipeline = vision_pipeline
        self.retriever = retriever
        self.llm = llm
    
    @with_timeout(30)
    async def analyze_input(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """Adım 1: Soru Analizi - PARTIAL RETURN"""
        
        if state.get("input_type") == "image":
            result = await self.vision_pipeline.process_from_path(state["raw_input"])
            return {
                "extracted_text": result["text"],
                "question_topics": result["topics"],
                "estimated_grade": result.get("estimated_grade"),
                "question_type": result["type"],
                "current_step": "analyze_input_complete"
            }
        else:
            # Metin analizi
            return {
                "extracted_text": state["raw_input"],
                "question_topics": [],  # Sonra LLM ile doldurulabilir
                "current_step": "analyze_input_complete"
            }
    
    @with_timeout(20)
    async def retrieve_kazanimlar(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """
        Adım 2: Kazanım Retrieval
        RETRY MANTIĞI: Node içinde döngü YOK!
        Graph edge tekrar çağırır.
        """
        retry_count = state.get("retry_count", 0)
        
        # KRİTİK: user_grade öncelikli!
        target_grade = state.get("user_grade") or state.get("estimated_grade")
        target_subject = state.get("user_subject")
        
        # Strateji: İlk denemede filtreli, sonraki denemelerde gevşet
        if retry_count == 0:
            grade_filter = target_grade
            subject_filter = target_subject
        elif retry_count == 1:
            grade_filter = target_grade  # Sadece sınıf filtresi
            subject_filter = None
        else:
            grade_filter = None  # Hiç filtre yok
            subject_filter = None
        
        results = await self.retriever.search(
            student_question=state["extracted_text"],
            grade=grade_filter,
            subject=subject_filter,
            top_k=10
        )
        
        # retry_count'u burada artır (Graph tekrar çağırırsa hazır)
        return {
            "matched_kazanimlar": results,
            "retrieval_scores": [r["score"] for r in results] if results else [],
            "retry_count": retry_count + 1,  # Her çağrıda artır
            "current_step": "retrieve_kazanimlar_complete"
        }
    
    @with_timeout(20)
    async def retrieve_textbook(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """Adım 3: Ders Kitabı Bölüm Retrieval"""
        
        kazanim_codes = [k["kazanim_code"] for k in state.get("matched_kazanimlar", [])[:5]]
        
        if not kazanim_codes:
            return {
                "matched_textbook_sections": [],
                "current_step": "retrieve_textbook_empty"
            }
        
        sections = await self.retriever.search_textbook_by_kazanimlar(
            kazanim_codes=kazanim_codes,
            question_text=state["extracted_text"]
        )
        
        return {
            "matched_textbook_sections": sections,
            "current_step": "retrieve_textbook_complete"
        }
    
    @with_timeout(15)
    async def rerank_results(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """Adım 4: Cross-Encoder Reranking (Opsiyonel)"""
        
        # Basit yaklaşım: Zaten skorlu geldi, ilk 5'i al
        top_kazanimlar = state.get("matched_kazanimlar", [])[:5]
        top_sections = state.get("matched_textbook_sections", [])[:3]
        
        return {
            "top_kazanimlar": top_kazanimlar,
            "top_sections": top_sections,
            "current_step": "rerank_complete"
        }
    
    @with_timeout(30)
    async def generate_response(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """Adım 5: Final Cevap Üretimi"""
        
        prompt = self._build_response_prompt(state)
        response = await self.llm.ainvoke(prompt)
        
        return {
            "explanation": response.content,
            "recommendations": self._extract_recommendations(response.content),
            "current_step": "generate_response_complete"
        }
    
    async def handle_error(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """Fallback - Hata durumu"""
        return {
            "explanation": "Üzgünüm, sorunuzu analiz ederken bir hata oluştu.",
            "recommendations": ["Lütfen soruyu tekrar deneyin."],
            "current_step": "error_handled"
        }
    
    def _build_response_prompt(self, state: QuestionAnalysisState) -> str:
        kazanimlar = state.get("top_kazanimlar", [])
        sections = state.get("top_sections", [])
        
        return f"""Öğrenci sorusu: {state.get('extracted_text', '')}

Eşleşen Kazanımlar:
{chr(10).join([f"- {k['kazanim_code']}: {k['kazanim_description']}" for k in kazanimlar])}

İlgili Ders Kitabı Bölümleri:
{chr(10).join([f"- {s.get('hierarchy_path', '')}: {s.get('content', '')[:200]}..." for s in sections])}

Bu soruyu çözmek için hangi kazanımları bilmesi gerektiğini açıkla.
Eksik olduğu konuları ve çalışması gereken bölümleri öner."""
```

### 6.5 Conditional Edge Logic

```python
# src/agents/conditions.py
from src.agents.state import QuestionAnalysisState

MAX_RETRIES = 3

def check_analysis_success(state: QuestionAnalysisState) -> str:
    """Analiz başarılı mı?"""
    if state.get("error"):
        return "error"
    if not state.get("extracted_text"):
        return "error"
    return "success"

def check_retrieval_success(state: QuestionAnalysisState) -> str:
    """Retrieval başarılı mı? Retry gerekiyor mu?"""
    if state.get("error"):
        return "error"
    
    if not state.get("matched_kazanimlar"):
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES:
            return "retry"  # Graph tekrar retrieve_kazanimlar'ı çağıracak
        return "error"  # Max retry aşıldı
    
    return "success"
```

### 6.6 Graph Assembly

```python
# src/agents/graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.agents.state import QuestionAnalysisState
from src.agents.nodes import GraphNodes
from src.agents.conditions import check_analysis_success, check_retrieval_success

class MebRagGraph:
    def __init__(self, nodes: GraphNodes, use_postgres: bool = False):
        self.nodes = nodes
        
        if use_postgres:
            from src.agents.persistence import get_checkpointer
            self.checkpointer = get_checkpointer()
        else:
            self.checkpointer = MemorySaver()
        
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(QuestionAnalysisState)
        
        # Node'ları ekle
        workflow.add_node("analyze_input", self.nodes.analyze_input)
        workflow.add_node("retrieve_kazanimlar", self.nodes.retrieve_kazanimlar)
        workflow.add_node("retrieve_textbook", self.nodes.retrieve_textbook)
        workflow.add_node("rerank_results", self.nodes.rerank_results)
        workflow.add_node("generate_response", self.nodes.generate_response)
        workflow.add_node("handle_error", self.nodes.handle_error)
        
        # Entry point
        workflow.set_entry_point("analyze_input")
        
        # Conditional edges (hata yönetimi)
        workflow.add_conditional_edges(
            "analyze_input",
            check_analysis_success,
            {"success": "retrieve_kazanimlar", "error": "handle_error"}
        )
        
        workflow.add_conditional_edges(
            "retrieve_kazanimlar",
            check_retrieval_success,
            {
                "success": "retrieve_textbook", 
                "retry": "retrieve_kazanimlar",  # RETRY DÖNGÜSÜ!
                "error": "handle_error"
            }
        )
        
        # Normal edges
        workflow.add_edge("retrieve_textbook", "rerank_results")
        workflow.add_edge("rerank_results", "generate_response")
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def invoke(self, input_data: dict, config: dict = None) -> dict:
        """Graph'ı çalıştır"""
        config = config or {"configurable": {"thread_id": "default"}}
        return await self.graph.ainvoke(input_data, config)
```

### 6.7 PostgreSQL Persistence

```python
# src/agents/persistence.py
from langgraph.checkpoint.postgres import PostgresSaver
from config.settings import get_settings
import psycopg2

def get_checkpointer() -> PostgresSaver:
    """Production için PostgreSQL checkpoint"""
    settings = get_settings()
    
    conn = psycopg2.connect(settings.database_url)
    
    # Tabloları oluştur (ilk çalıştırmada)
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()  # Gerekli tabloları oluşturur
    
    return checkpointer
```

---

## 📊 State Machine Diyagramı (Güncellenmiş)

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     error    ┌─────────────┐
│  Analyze    │─────────────►│   Handle    │
│   Input     │              │   Error     │──────►END
└──────┬──────┘              └─────────────┘
       │success
       ▼
┌─────────────┐◄────retry────┐
│  Retrieve   │              │ (max 3x)
│ Kazanimlar  │──────────────┘
└──────┬──────┘
       │success
       ▼
┌─────────────┐
│  Retrieve   │
│  Textbook   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Rerank    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Generate   │
│  Response   │
└──────┬──────┘
       │
       ▼
     [ END ]
```

---

## ✅ Avantajlar (Güncellenmiş)

| Sorun | Eski | Yeni |
|-------|------|------|
| Retry çakışması | Node + Graph = 4x | Sadece Graph edge |
| Grade | AI tahmini | **user_grade öncelikli** |
| Return tipi | Tüm state | **Partial update** |
| Error handling | KeyError riski | State-safe decorator |

---

## ⏭️ Sonraki: Faz 7 - RAG Pipeline
