# Faz 4: Azure AI Search ve Sentetik Soru Üretimi

## 🎯 Amaç
Semantic Gap sorununu çözmek için her kazanım için GPT ile sentetik soru üretip, **Hybrid Search** ile eşleştirme yapmak.

---

## ⚠️ KRİTİK: Maliyet ve Performans

| Parametre | Eski (Pahalı) | Yeni (Optimize) |
|-----------|---------------|-----------------|
| Model | gpt-4o | **gpt-4o-mini** (20x ucuz) |
| Soru sayısı | 50 | **15-20** (yeterli coverage) |
| Arama | Sadece vektör | **Hybrid** (vektör + keyword) |

**Hesap:** 3.000 kazanım × 50 soru = 150.000 çağrı ❌
**Optimize:** 3.000 kazanım × 20 soru = 60.000 çağrı, mini model ile ✅

---

## 🔧 Uygulama Adımları

### 4.1 Embedding Fonksiyonu (EKSİK OLAN!)

```python
# src/vector_store/embeddings.py
from openai import AzureOpenAI
from config.settings import get_settings

_client = None

def get_embedding_client() -> AzureOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AzureOpenAI(
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint
        )
    return _client


async def embed_text(text: str) -> list[float]:
    """Metni vektöre çevir (text-embedding-ada-002)"""
    settings = get_settings()
    client = get_embedding_client()
    
    # Yeni satır karakterlerini temizle (embedding kalitesini artırır)
    text = text.replace("\n", " ").strip()
    
    # Boş veya çok kısa metin kontrolü
    if len(text) < 3:
        raise ValueError("Metin çok kısa, embedding oluşturulamaz")
    
    response = client.embeddings.create(
        input=[text],
        model=settings.azure_openai_embedding_deployment
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    """Toplu embedding (maliyet optimizasyonu)"""
    settings = get_settings()
    client = get_embedding_client()
    
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip() for t in texts[i:i+batch_size]]
        response = client.embeddings.create(
            input=batch,
            model=settings.azure_openai_embedding_deployment
        )
        all_embeddings.extend([d.embedding for d in response.data])
    
    return all_embeddings
```

### 4.2 Sentetik Soru Üreticisi (MALİYET OPTİMİZE)

```python
# src/vector_store/question_generator.py
from openai import AzureOpenAI
from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class SyntheticQuestion:
    question_text: str
    difficulty: str
    question_type: str
    parent_kazanim_id: str
    parent_kazanim_code: str
    related_textbook_section: str

class SyntheticQuestionGenerator:
    # MALİYET OPTİMİZASYONU: 20 soru yeterli coverage sağlar
    DEFAULT_COUNT = 20
    
    GENERATION_PROMPT = """Sen bir MEB sınav hazırlama uzmanısın.

KAZANIM: {kazanim_code} - {kazanim_description}
SINIF: {grade}. Sınıf
DERS: {subject}

Bu kazanımı ölçen {count} farklı soru üret.

KURALLAR:
1. Zorluk dağılımı: 8 kolay, 8 orta, 4 zor
2. Soru tipleri: çoktan_seçmeli, boşluk_doldurma, problem, doğru_yanlış
3. Matematik/Fen için formülleri LaTeX formatında yaz ($x^2$ gibi)
4. Sadece bu kazanımı test et, başka konuya karışma!
5. Gerçekçi ve çözülebilir olmalı

JSON formatında döndür (başka açıklama yazma):
[{{"question": "...", "difficulty": "kolay/orta/zor", "type": "çoktan_seçmeli/problem/..."}}]"""

    def __init__(self, client: AzureOpenAI):
        self.client = client
    
    async def generate_for_kazanim(
        self, 
        kazanim: dict, 
        textbook_sections: Optional[List[str]] = None,
        count: int = DEFAULT_COUNT
    ) -> List[SyntheticQuestion]:
        """Her kazanım için sentetik soru üret"""
        
        prompt = self.GENERATION_PROMPT.format(
            count=count,
            kazanim_code=kazanim["code"],
            kazanim_description=kazanim["description"],
            grade=kazanim["grade"],
            subject=kazanim.get("subject", "")
        )
        
        # Ders kitabı bağlamı varsa ekle
        if textbook_sections:
            prompt += f"\n\nDERS KİTABI BAĞLAMI:\n{chr(10).join(textbook_sections[:2])}"
        
        # MALİYET: gpt-4o-mini kullan! (20x ucuz)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",  # ÖNEMLİ: mini model yeterli!
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=3000,
                    response_format={"type": "json_object"}  # JSON garantisi
                )
                
                content = response.choices[0].message.content
                questions = json.loads(content)
                
                # JSON root bir liste değilse düzelt
                if isinstance(questions, dict):
                    questions = questions.get("questions", [])
                
                return [
                    SyntheticQuestion(
                        question_text=q["question"],
                        difficulty=q.get("difficulty", "orta"),
                        question_type=q.get("type", "problem"),
                        parent_kazanim_id=str(kazanim["id"]),
                        parent_kazanim_code=kazanim["code"],
                        related_textbook_section=textbook_sections[0] if textbook_sections else ""
                    ) for q in questions
                ]
            except json.JSONDecodeError as e:
                print(f"JSON parse hatası (deneme {attempt+1}): {e}")
                if attempt == max_retries - 1:
                    return []  # Son denemede boş dön
            except Exception as e:
                print(f"Soru üretim hatası: {e}")
                return []
```

### 4.3 Index Şeması (Semantic Reranker ile)

```python
# src/vector_store/index_schema.py
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticField, SemanticPrioritizedFields,
    SemanticSearch
)

def create_question_index_schema() -> SearchIndex:
    """Sentetik sorular için Hybrid Search index"""
    return SearchIndex(
        name="meb-sentetik-sorular-index",
        fields=[
            SearchField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(name="question_text", type=SearchFieldDataType.String, 
                       searchable=True, analyzer_name="tr.microsoft"),  # Türkçe analyzer!
            SearchField(name="difficulty", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(name="question_type", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="parent_kazanim_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="parent_kazanim_code", type=SearchFieldDataType.String, filterable=True, searchable=True),
            SearchField(name="parent_kazanim_desc", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="grade", type=SearchFieldDataType.Int32, filterable=True, facetable=True),
            SearchField(name="subject", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SearchField(
                name="embedding", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,
                vector_search_profile_name="question-profile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
            profiles=[VectorSearchProfile(
                name="question-profile", 
                algorithm_configuration_name="hnsw-algo"
            )]
        ),
        # SEMANTIC RERANKER - %20-30 doğruluk artışı!
        semantic_search=SemanticSearch(
            configurations=[SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="question_text"),
                    content_fields=[SemanticField(field_name="parent_kazanim_desc")]
                )
            )]
        )
    )
```

### 4.4 Hybrid Search ile Parent Retrieval (KRİTİK!)

```python
# src/vector_store/parent_retriever.py
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from src.vector_store.embeddings import embed_text
from typing import List, Optional

class ParentDocumentRetriever:
    """
    Hybrid Search: Vektör + Keyword + Semantic Reranker
    Öğrenci sorusu → Eşleşen sentetik sorular → Parent Kazanım
    """
    
    def __init__(self, search_client: SearchClient, kazanim_db):
        self.search_client = search_client
        self.kazanim_db = kazanim_db
    
    async def search(
        self, 
        student_question: str, 
        grade: Optional[int] = None,
        subject: Optional[str] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Hybrid Search ile kazanım bul.
        KRİTİK: grade ve subject filtreleri pedagojik doğruluk için şart!
        """
        
        # 1. Embedding oluştur
        query_embedding = await embed_text(student_question)
        
        # 2. Filtre oluştur (pedagojik doğruluk için KRİTİK!)
        filters = []
        if grade:
            filters.append(f"grade eq {grade}")
        if subject:
            filters.append(f"subject eq '{subject}'")
        filter_str = " and ".join(filters) if filters else None
        
        # 3. HYBRID SEARCH (Vektör + Keyword + Semantic)
        results = self.search_client.search(
            search_text=student_question,      # Keyword arama
            vector_queries=[VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=50,        # Geniş havuz al
                fields="embedding"
            )],
            filter=filter_str,                 # Sınıf/ders filtresi
            query_type="semantic",             # Semantic reranker aktif
            semantic_configuration_name="semantic-config",
            top=50,
            select=["parent_kazanim_id", "parent_kazanim_code", "parent_kazanim_desc", 
                    "question_text", "difficulty"]
        )
        
        # 4. Parent Kazanımları grupla ve skorla
        kazanim_scores = {}
        for result in results:
            kid = result["parent_kazanim_id"]
            if kid not in kazanim_scores:
                kazanim_scores[kid] = {
                    "score": 0, 
                    "code": result["parent_kazanim_code"],
                    "desc": result["parent_kazanim_desc"],
                    "matches": []
                }
            kazanim_scores[kid]["score"] += result["@search.score"]
            kazanim_scores[kid]["matches"].append({
                "question": result["question_text"],
                "difficulty": result["difficulty"]
            })
        
        # 5. En alakalı kazanımları sırala
        top_kazanimlar = sorted(
            kazanim_scores.items(), 
            key=lambda x: x[1]["score"], 
            reverse=True
        )[:top_k]
        
        return [
            {
                "kazanim_id": kid,
                "kazanim_code": data["code"],
                "kazanim_description": data["desc"],
                "score": data["score"],
                "matched_questions": data["matches"][:3]
            } 
            for kid, data in top_kazanimlar
        ]
```

### 4.5 Batch İndeksleme Pipeline

```python
# src/vector_store/indexing_pipeline.py
import asyncio
from tqdm import tqdm
from src.vector_store.embeddings import embed_batch
from src.vector_store.question_generator import SyntheticQuestionGenerator

class IndexingPipeline:
    """Tüm kazanımlar için sentetik soru üret ve indeksle"""
    
    def __init__(self, openai_client, search_client, kazanim_db):
        self.generator = SyntheticQuestionGenerator(openai_client)
        self.search_client = search_client
        self.kazanim_db = kazanim_db
    
    async def index_all_kazanimlar(self, kazanimlar: list, batch_size: int = 10):
        """Tüm kazanımları işle (rate limiting ile)"""
        
        for i in tqdm(range(0, len(kazanimlar), batch_size), desc="Kazanımlar"):
            batch = kazanimlar[i:i+batch_size]
            
            for kazanim in batch:
                await self._process_single_kazanim(kazanim)
            
            # Rate limiting: her batch arasında bekle
            await asyncio.sleep(1)
    
    async def _process_single_kazanim(self, kazanim: dict):
        """Tek kazanım için soru üret ve indeksle"""
        
        # 1. İlgili chunk'ları bul (opsiyonel)
        textbook_chunks = self._get_related_chunks(kazanim)
        
        # 2. 20 sentetik soru üret
        questions = await self.generator.generate_for_kazanim(
            kazanim, 
            textbook_chunks,
            count=20  # Optimize edilmiş sayı
        )
        
        if not questions:
            print(f"⚠️ {kazanim['code']} için soru üretilemedi")
            return
        
        # 3. Toplu embedding (maliyet optimizasyonu)
        question_texts = [q.question_text for q in questions]
        embeddings = await embed_batch(question_texts)
        
        # 4. İndeksle
        documents = []
        for idx, (q, emb) in enumerate(zip(questions, embeddings)):
            documents.append({
                "id": f"{kazanim['code']}-{idx}",
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "question_type": q.question_type,
                "parent_kazanim_id": q.parent_kazanim_id,
                "parent_kazanim_code": q.parent_kazanim_code,
                "parent_kazanim_desc": kazanim["description"],
                "grade": kazanim["grade"],
                "subject": kazanim.get("subject", ""),
                "embedding": emb
            })
        
        self.search_client.upload_documents(documents)
```

---

## 📊 Hybrid Search Akışı

```
Öğrenci Sorusu: "Ebob Ekok problemleri"
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
   ┌───────────┐            ┌───────────┐
   │  Keyword  │            │  Vektör   │
   │  "Ebob"   │            │ Semantic  │
   └─────┬─────┘            └─────┬─────┘
         │                        │
         └──────────┬─────────────┘
                    ▼
           ┌────────────────┐
           │   Semantic     │
           │   Reranker     │
           └────────┬───────┘
                    ▼
          Filtre: grade=6, subject="Matematik"
                    ▼
          Parent Kazanım: M.6.1.3.2
```

---

## ✅ Avantajlar (Güncellenmiş)

| Sorun | Eski | Yeni (Optimize) |
|-------|------|-----------------|
| Maliyet | 150k GPT-4o çağrısı | 60k gpt-4o-mini |
| Arama | Sadece vektör | Hybrid (keyword+vektör+semantic) |
| Filtreleme | Yok | grade + subject zorunlu |
| Türkçe | Varsayılan | tr.microsoft analyzer |
| Halüsinasyon | Kontrol yok | JSON retry + validation |

---

## ⏭️ Sonraki: Faz 5 - Azure GPT-4o Vision
