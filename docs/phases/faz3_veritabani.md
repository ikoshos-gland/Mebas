# Faz 3: Veritabanı Şeması ve Veri Modelleme

## 🎯 Amaç
Faz 2'de üretilen chunk'lar ve görseller için tam uyumlu veritabanı şeması tasarlamak.

---

## ⚠️ KRİTİK: Faz 2 Uyumu

| Faz 2 Çıktısı | Faz 3 Tablosu |
|---------------|---------------|
| `SemanticChunk` | `BookChunk` |
| `ExtractedImage` | `TextbookImage` |
| Hiyerarşi | `hierarchy_path` alanı |

---

## 🔧 Uygulama Adımları

### 3.1 Temel Modeller

```python
# src/database/models.py
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Float, DateTime, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

# ================== DERS VE KAZANIM ==================

class Subject(Base):
    """Ders (Matematik, Fizik, vb.)"""
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True)   # M, F, T, B...
    name = Column(String(100))               # Matematik, Fizik...
    
    kazanimlar = relationship("Kazanim", back_populates="subject")
    textbooks = relationship("Textbook", back_populates="subject")


class Kazanim(Base):
    """MEB Kazanımları - Müfredat hiyerarşisi ile"""
    __tablename__ = "kazanimlar"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, index=True)  # M.5.1.2.3
    description = Column(Text)
    grade = Column(Integer, index=True)                  # 1-12
    
    # MEB Müfredat Hiyerarşisi
    learning_area = Column(String(255))       # Öğrenme Alanı: "Sayılar ve İşlemler"
    sub_learning_area = Column(String(255))   # Alt Alan: "Doğal Sayılar"
    unit_number = Column(Integer)
    topic_number = Column(Integer)
    
    # Eğitim Taksonomisi (Opsiyonel)
    bloom_level = Column(String(50))          # "Hatırlama", "Anlama", "Uygulama", "Analiz"
    
    # İlişkiler
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    subject = relationship("Subject", back_populates="kazanimlar")
    
    # Chunk ilişkisi (hangi kitap bölümleri bu kazanımla ilgili)
    related_chunks = relationship("BookChunk", back_populates="kazanim")


# ================== DERS KİTABI ==================

class Textbook(Base):
    """Ders Kitabı"""
    __tablename__ = "textbooks"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    grade = Column(Integer, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    publisher = Column(String(100))
    year = Column(Integer)
    pdf_path = Column(String(512))  # PDF dosya yolu
    
    subject = relationship("Subject", back_populates="textbooks")
    chapters = relationship("Chapter", back_populates="textbook")


class Chapter(Base):
    """Ders Kitabı Bölümü - Sadece metadata, içerik chunk'larda"""
    __tablename__ = "chapters"
    
    id = Column(Integer, primary_key=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"))
    number = Column(Integer)
    title = Column(String(200))
    page_start = Column(Integer)
    page_end = Column(Integer)
    
    # NOT: content sütunu YOK - içerik chunk'larda!
    
    textbook = relationship("Textbook", back_populates="chapters")
    chunks = relationship("BookChunk", back_populates="chapter")


# ================== CHUNK VE GÖRSEL (FAZ 2 UYUMLU) ==================

class BookChunk(Base):
    """
    Faz 2'deki SemanticChunk ile 1:1 eşleşir.
    RAG citation için kritik!
    """
    __tablename__ = "book_chunks"
    
    id = Column(String(50), primary_key=True)  # UUID (Faz 2'den gelen)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    
    # İçerik
    content = Column(Text)
    chunk_type = Column(String(30))           # concept, example, info_box, sidebar
    hierarchy_path = Column(String(255))      # "Ünite1/Konu2/AltBaşlık3"
    page_range = Column(String(50))           # "45-46"
    is_sidebar = Column(Boolean, default=False)
    
    # Kazanım ilişkisi (AI tarafından tespit edilirse)
    related_kazanim_id = Column(Integer, ForeignKey("kazanimlar.id"), nullable=True)
    
    # Metadata
    element_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # İlişkiler
    chapter = relationship("Chapter", back_populates="chunks")
    kazanim = relationship("Kazanim", back_populates="related_chunks")
    images = relationship("TextbookImage", back_populates="chunk")


class TextbookImage(Base):
    """
    Faz 2'deki ExtractedImage ile 1:1 eşleşir.
    RAG'ın "Bakınız Şekil 3.1" demesi için gerekli!
    """
    __tablename__ = "textbook_images"
    
    id = Column(String(50), primary_key=True)  # UUID
    chunk_id = Column(String(50), ForeignKey("book_chunks.id"))
    
    # Dosya bilgileri
    image_path = Column(String(512))          # Disk yolu veya Blob URL
    width = Column(Integer)
    height = Column(Integer)
    
    # AI üretimi
    caption = Column(Text)                    # GPT-4o açıklaması
    image_type = Column(String(50))           # graph, diagram, photo, table_image
    
    # Konum
    page_number = Column(Integer)
    
    chunk = relationship("BookChunk", back_populates="images")


# ================== GERİ BİLDİRİM (FAZ 8 İÇİN) ==================

class Feedback(Base):
    """Kullanıcı geri bildirimi - sistem iyileştirme için"""
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True)
    analysis_id = Column(String(50), index=True)
    rating = Column(Integer)                  # -1: thumbs down, 1: thumbs up
    comment = Column(Text, nullable=True)
    correct_kazanim = Column(String(20), nullable=True)
    
    # Debugging için
    question_text = Column(Text)
    matched_kazanim = Column(String(20))
    response_time_ms = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 3.2 Veritabanı Kurulumu

```python
# src/database/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from src.database.models import Base

settings = get_settings()

# Engine oluştur
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Tüm tabloları oluştur"""
    Base.metadata.create_all(bind=engine)
    print("✅ Veritabanı tabloları oluşturuldu!")


def get_db():
    """Dependency injection için session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 3.3 Faz 2 → Faz 3 Veri Aktarımı

```python
# src/database/import_chunks.py
from src.database.db import SessionLocal
from src.database.models import BookChunk, TextbookImage, Chapter

def import_semantic_chunks(chunks: list, chapter_id: int):
    """Faz 2'deki SemanticChunk'ları veritabanına aktar"""
    db = SessionLocal()
    
    for chunk in chunks:
        db_chunk = BookChunk(
            id=chunk.chunk_id,
            chapter_id=chapter_id,
            content=chunk.content,
            chunk_type=chunk.chunk_type,
            hierarchy_path=chunk.hierarchy_path,
            page_range=f"{chunk.page_range[0]}-{chunk.page_range[1]}",
            is_sidebar=chunk.is_sidebar_content,
            element_count=chunk.metadata.get("element_count", 0)
        )
        db.add(db_chunk)
    
    db.commit()
    db.close()

def import_extracted_images(images: list, chunk_id: str):
    """Faz 2'deki ExtractedImage'ları veritabanına aktar"""
    db = SessionLocal()
    
    for img in images:
        db_image = TextbookImage(
            id=img.image_id,
            chunk_id=chunk_id,
            image_path=str(img.image_path) if img.image_path else None,
            width=img.width,
            height=img.height,
            caption=img.caption,
            image_type=img.image_type,
            page_number=img.page_number
        )
        db.add(db_image)
    
    db.commit()
    db.close()
```

---

## 📊 ER Diyagramı

```
┌─────────────┐         ┌─────────────┐
│  Subjects   │────────►│  Textbooks  │
└──────┬──────┘  1:N    └──────┬──────┘
       │                       │
       │1:N                    │1:N
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│  Kazanimlar │◄───────►│  Chapters   │
└─────────────┘   N:M   └──────┬──────┘
       ▲   (BookChunk)         │1:N
       │                       ▼
       │              ┌─────────────────┐
       └──────────────│   BookChunks    │
         related_     └────────┬────────┘
         kazanim_id            │1:N
                               ▼
                      ┌─────────────────┐
                      │ TextbookImages  │
                      └─────────────────┘
```

---

## ✅ Doğrulama

```python
def test_database_schema():
    from src.database.db import init_db, SessionLocal
    from src.database.models import BookChunk, TextbookImage
    
    init_db()
    
    db = SessionLocal()
    
    # Test chunk oluştur
    chunk = BookChunk(
        id="test-001",
        chapter_id=1,
        content="Test içerik",
        chunk_type="concept",
        hierarchy_path="Ünite1/Konu1"
    )
    db.add(chunk)
    db.commit()
    
    # Sorgula
    result = db.query(BookChunk).filter_by(id="test-001").first()
    assert result is not None
    assert result.content == "Test içerik"
    
    print("✅ Veritabanı şeması çalışıyor!")
    db.close()
```

---

## ⏭️ Sonraki: Faz 4 - Azure AI Search
