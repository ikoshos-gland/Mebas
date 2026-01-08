"""
MEB RAG Sistemi - Veritabanı Modelleri
SQLAlchemy ORM Models for MEB Educational Content
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, Text, Float, 
    DateTime, Boolean, Table
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


# ================== MANY-TO-MANY: KAZANIM PREREQUISITES ==================

kazanim_prerequisites = Table(
    'kazanim_prerequisites',
    Base.metadata,
    Column('kazanim_id', Integer, ForeignKey('kazanimlar.id'), primary_key=True),
    Column('prerequisite_id', Integer, ForeignKey('kazanimlar.id'), primary_key=True)
)


# ================== DERS VE KAZANIM ==================

class Subject(Base):
    """Ders (Matematik, Fizik, vb.)"""
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(10), unique=True)   # M, F, T, B...
    name = Column(String(100))               # Matematik, Fizik...
    
    kazanimlar = relationship("Kazanim", back_populates="subject")
    textbooks = relationship("Textbook", back_populates="subject")
    
    def __repr__(self):
        return f"<Subject {self.code}: {self.name}>"


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
    
    # Eğitim Taksonomisi (Bloom's)
    bloom_level = Column(String(50))          # "Hatırlama", "Anlama", "Uygulama", "Analiz"
    
    # İlişkiler
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    subject = relationship("Subject", back_populates="kazanimlar")
    
    # Chunk ilişkisi (hangi kitap bölümleri bu kazanımla ilgili)
    related_chunks = relationship("BookChunk", back_populates="kazanim")
    
    # Prerequisites ilişkisi (Faz 7 için)
    prerequisites = relationship(
        "Kazanim",
        secondary=kazanim_prerequisites,
        primaryjoin="Kazanim.id == kazanim_prerequisites.c.kazanim_id",
        secondaryjoin="Kazanim.id == kazanim_prerequisites.c.prerequisite_id",
        backref="required_by"
    )
    
    def __repr__(self):
        return f"<Kazanim {self.code}>"


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
    chapters = relationship("Chapter", back_populates="textbook", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Textbook {self.title} - Grade {self.grade}>"


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
    chunks = relationship("BookChunk", back_populates="chapter", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chapter {self.number}: {self.title}>"


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
    images = relationship("TextbookImage", back_populates="chunk", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BookChunk {self.id}: {self.chunk_type}>"


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
    
    def __repr__(self):
        return f"<TextbookImage {self.id}: {self.image_type}>"


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
    
    def __repr__(self):
        return f"<Feedback {self.analysis_id}: {self.rating}>"
