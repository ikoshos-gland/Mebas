# Faz 7: RAG Pipeline ve Response Generator

## 🎯 Amaç
Faz 6'daki `generate_response` node'unun içini **Pydantic Structured Output** ile doldurmak.

---

## ⚠️ KRİTİK: Bu Faz Yeni Pipeline Değil!

| Yanlış | Doğru |
|--------|-------|
| `RetrievalQA.from_chain_type` (Legacy) | Faz 6 Node implementasyonu |
| `vectorstore.as_retriever()` (Bypass) | Faz 4 `ParentDocumentRetriever` |
| JSON string parse | **Pydantic Structured Output** |

**Faz 7 = Faz 6'daki boş node'ları doldur!**

---

## 🔧 Uygulama Adımları

### 7.1 Pydantic Output Modeli (JSON Garantili!)

```python
# src/rag/output_models.py
from pydantic import BaseModel, Field
from typing import List, Optional

class MatchedKazanim(BaseModel):
    """Tek bir eşleşen kazanım"""
    kazanim_code: str = Field(description="MEB kazanım kodu, örn: M.5.1.4.2")
    kazanim_description: str = Field(description="Kazanım açıklaması")
    relevance_score: float = Field(description="0-1 arası alaka skoru")
    is_direct_match: bool = Field(description="Doğrudan mı yoksa dolaylı mı eşleşme")

class PrerequisiteGap(BaseModel):
    """Eksik ön koşul bilgisi"""
    topic: str = Field(description="Eksik konu adı")
    related_kazanim_codes: List[str] = Field(description="İlgili kazanım kodları")
    recommended_section: Optional[str] = Field(description="Okunması gereken kitap bölümü")

class AnalysisOutput(BaseModel):
    """
    LLM çıktısı - Pydantic ile garanti altında!
    GPT bazen JSON bozar, bu yapı ile hata almayız.
    """
    tested_kazanimlar: List[MatchedKazanim] = Field(
        description="Sorunun test ettiği kazanımlar (en fazla 3)"
    )
    prerequisite_gaps: List[PrerequisiteGap] = Field(
        description="Öğrencinin eksik olabileceği ön koşul konuları"
    )
    explanation: str = Field(
        description="Öğrenciye yönelik eğitici açıklama (çözümü değil, mantığı anlat)"
    )
    study_recommendations: List[str] = Field(
        description="Çalışması gereken kitap bölümleri ve konular"
    )
    confidence: float = Field(
        description="Analiz güven skoru (0-1)",
        ge=0.0, le=1.0
    )
```

### 7.2 Response Generator (Structured Output!)

```python
# src/rag/generator.py
from langchain_openai import AzureChatOpenAI
from src.rag.output_models import AnalysisOutput
from config.settings import get_settings

class ResponseGenerator:
    """
    Faz 6'daki generate_response node'u tarafından çağrılır.
    Pydantic ile yapısal çıktı garantisi!
    """
    
    def __init__(self):
        settings = get_settings()
        
        base_llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=0
        )
        
        # KRİTİK: Yapısal çıktıya zorla!
        self.structured_llm = base_llm.with_structured_output(AnalysisOutput)
    
    async def generate(self, state: dict) -> AnalysisOutput:
        """State'ten cevap üret"""
        
        prompt = self._build_prompt(state)
        
        # Structured output - JSON parse hatası OLMAZ!
        result = await self.structured_llm.ainvoke(prompt)
        
        return result
    
    def _build_prompt(self, state: dict) -> str:
        return f"""SEN BİR MEB EĞİTİM ASİSTANISIN.

ÖĞRENCİ SORUSU:
{state.get('extracted_text', '')}

SORU TİPİ: {state.get('question_type', 'bilinmiyor')}
KONULAR: {', '.join(state.get('question_topics', []))}

BULUNAN EN İLGİLİ KAZANIMLAR (Faz 4 Parent Document Retrieval ile):
{self._format_kazanimlar(state.get('top_kazanimlar', []))}

İLGİLİ DERS KİTABI BÖLÜMLERİ:
{self._format_sections(state.get('top_sections', []))}

GÖREV:
1. Sorunun hangi kazanımları test ettiğini belirle (max 3).
2. Öğrenci bu soruyu yapamıyorsa, hangi alt konularda eksiği olabilir?
3. Eksik konuları anlaması için kitaptan hangi bölümleri okumalı?
4. Sorunun çözüm mantığını (cevabı değil!) anlatan kısa bir açıklama yaz.
5. Güven skorunu belirle (0-1, eşleşme kalitesine göre).

⚠️ ÖNEMLİ: Cevabı VERME, sadece mantığı anlat!"""

    def _format_kazanimlar(self, kazanimlar: list) -> str:
        if not kazanimlar:
            return "Kazanım bulunamadı."
        
        lines = []
        for k in kazanimlar[:5]:
            code = k.get('kazanim_code', 'N/A')
            desc = k.get('kazanim_description', '')[:100]
            score = k.get('score', 0)
            lines.append(f"- [{code}] (skor: {score:.2f}): {desc}")
        
        return "\n".join(lines)
    
    def _format_sections(self, sections: list) -> str:
        if not sections:
            return "İlgili bölüm bulunamadı."
        
        lines = []
        for s in sections[:3]:
            path = s.get('hierarchy_path', '')
            content = s.get('content', '')[:150]
            lines.append(f"- {path}: {content}...")
        
        return "\n".join(lines)
```

### 7.3 Faz 6 Node Entegrasyonu

```python
# src/agents/nodes.py içine ekle:

from src.rag.generator import ResponseGenerator
from src.rag.output_models import AnalysisOutput

class GraphNodes:
    def __init__(self, ...):
        # ... mevcut init ...
        self.response_generator = ResponseGenerator()
    
    @with_timeout(30)
    async def generate_response(self, state: QuestionAnalysisState) -> Dict[str, Any]:
        """
        Faz 7 implementasyonu!
        Faz 6'daki boş node artık dolu.
        """
        
        # Structured output döner
        result: AnalysisOutput = await self.response_generator.generate(state)
        
        return {
            "gap_analysis": {
                "tested_kazanimlar": [k.model_dump() for k in result.tested_kazanimlar],
                "prerequisite_gaps": [g.model_dump() for g in result.prerequisite_gaps]
            },
            "explanation": result.explanation,
            "recommendations": result.study_recommendations,
            "confidence": result.confidence,
            "current_step": "generate_response_complete"
        }
```

### 7.4 Prerequisite İlişkisi (Veritabanı Güncellemesi)

```python
# src/database/models.py'e ekle:

# Many-to-Many: Hangi kazanım hangi kazanımın ön koşulu?
kazanim_prerequisites = Table(
    'kazanim_prerequisites',
    Base.metadata,
    Column('kazanim_id', Integer, ForeignKey('kazanimlar.id'), primary_key=True),
    Column('prerequisite_id', Integer, ForeignKey('kazanimlar.id'), primary_key=True)
)

class Kazanim(Base):
    # ... mevcut alanlar ...
    
    # Prerequisites ilişkisi
    prerequisites = relationship(
        "Kazanim",
        secondary=kazanim_prerequisites,
        primaryjoin="Kazanim.id == kazanim_prerequisites.c.kazanim_id",
        secondaryjoin="Kazanim.id == kazanim_prerequisites.c.prerequisite_id",
        backref="required_by"
    )
```

### 7.5 Gap Finder (Veritabanı Destekli)

```python
# src/rag/gap_finder.py
from src.database.db import SessionLocal
from src.database.models import Kazanim

class GapFinder:
    """
    LLM'in "eksik konu" tahminini veritabanıyla doğrula.
    LLM müfredat ağacını ezbere bilmez, biz yardım ederiz.
    """
    
    def find_prerequisites(self, kazanim_codes: list[str]) -> list[dict]:
        """Verilen kazanımların ön koşullarını bul"""
        db = SessionLocal()
        
        prerequisites = []
        for code in kazanim_codes:
            kazanim = db.query(Kazanim).filter_by(code=code).first()
            if kazanim and kazanim.prerequisites:
                for prereq in kazanim.prerequisites:
                    prerequisites.append({
                        "code": prereq.code,
                        "description": prereq.description,
                        "parent_code": code
                    })
        
        db.close()
        return prerequisites
```

---

## 📊 Güncellenmiş Akış Diyagramı

```
┌─────────────────┐
│ Öğrenci Sorusu  │
│ (Metin/Görsel)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GPT-4o Vision   │ (Faz 5)
│ Soru Çıkarma    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ ParentDocumentRetriever │ (Faz 4)
│ Sentetik Soru Eşleştirme│
│ Hybrid Search           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│ Reranker        │ (Faz 6 Node)
│ Cross-Encoder   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ ResponseGenerator       │ (Faz 7)
│ Pydantic Structured     │
│ Output                  │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│ AnalysisOutput  │
│ (JSON Garantili)│
└─────────────────┘
```

---

## ✅ Avantajlar

| Eski (Legacy) | Yeni (Modern) |
|---------------|---------------|
| RetrievalQA chain | **Faz 6 Node** |
| Standart vektör arama | **Faz 4 Parent Retrieval** |
| JSON string parse | **Pydantic Structured** |
| Manuel skor hesabı | **Faz 6 Reranker** |
| Gap tahmini (LLM) | **DB Prerequisite** |

---

## ⏭️ Sonraki: Faz 8 - API ve Deployment
