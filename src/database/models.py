"""
MEB RAG Sistemi - Veritabanı Modelleri
SQLAlchemy ORM Models for MEB Educational Content
"""
from sqlalchemy import (
    Column, String, Integer, ForeignKey, Text, Float,
    DateTime, Boolean, Table, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


# ================== OKUL/TENANT (SaaS) ==================

class School(Base):
    """
    Okul/Organizasyon tenant modeli - Platform admin tarafından oluşturulur.
    Flat tier pricing: small, medium, large
    """
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)  # URL-safe identifier

    # İletişim bilgileri
    admin_email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)

    # Abonelik tier'ı
    tier = Column(String(20), default="small")  # small, medium, large
    max_students = Column(Integer, default=100)  # small:100, medium:500, large:2000
    max_teachers = Column(Integer, default=10)   # small:10, medium:50, large:200

    # Aktif özellikler
    features = Column(JSON, default=dict)  # {"exam_generator": true, "analytics": true}

    # Durum
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    users = relationship("User", back_populates="school")
    classrooms = relationship("Classroom", back_populates="school", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="school", cascade="all, delete-orphan")
    billing_records = relationship("BillingRecord", back_populates="school", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<School {self.slug}: {self.name}>"


class BillingRecord(Base):
    """Okul faturalama geçmişi"""
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)

    # Faturalama dönemi
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Plan detayları
    tier = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)  # TRY cinsinden
    currency = Column(String(3), default="TRY")

    # Durum
    status = Column(String(20), default="pending")  # pending, paid, overdue, cancelled

    # Ödeme takibi
    invoice_number = Column(String(50), unique=True)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Notlar
    notes = Column(Text, nullable=True)

    # Zaman damgası
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    school = relationship("School", back_populates="billing_records")

    def __repr__(self):
        return f"<BillingRecord {self.invoice_number}: {self.status}>"


# ================== KULLANICI VE ABONELİK ==================

class User(Base):
    """Kullanıcı modeli - Firebase Authentication ile"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    avatar_url = Column(String(512), nullable=True)

    # Rol ve seviye - SaaS için genişletildi
    role = Column(String(20), default="student")  # student, teacher, school_admin, platform_admin
    grade = Column(Integer, nullable=True)  # 1-12, null for teachers/admins

    # Okul ilişkisi (SaaS multi-tenant)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True, index=True)

    # Profil durumu (Firebase login sonrası rol/sınıf seçimi)
    profile_complete = Column(Boolean, default=False)

    # Durum
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # Firebase email_verified ile senkronize

    # Tercihler (JSON)
    preferences = Column(JSON, default=dict)

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # İlişkiler
    school = relationship("School", back_populates="users")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    kazanim_progress = relationship("UserKazanimProgress", back_populates="user", cascade="all, delete-orphan")
    generated_exams = relationship("GeneratedExam", back_populates="user", cascade="all, delete-orphan")
    # Öğretmen ilişkileri
    classrooms_teaching = relationship("Classroom", back_populates="teacher", foreign_keys="Classroom.teacher_id")
    created_assignments = relationship("Assignment", back_populates="created_by", foreign_keys="Assignment.created_by_id")

    # Index for school+role queries
    __table_args__ = (
        Index("ix_user_school_role", "school_id", "role"),
    )

    def __repr__(self):
        return f"<User {self.email}>"


class Subscription(Base):
    """Abonelik modeli - Kullanım limitleri"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Plan tipi
    plan = Column(String(20), default="free")  # free, student, school

    # Kullanım limitleri
    questions_used_today = Column(Integer, default=0)
    questions_limit = Column(Integer, default=10)  # free: 10, student: unlimited (-1)

    # Görsel analiz limiti
    images_used_today = Column(Integer, default=0)
    images_limit = Column(Integer, default=0)  # free: 0, student: 20, school: unlimited

    # Sıfırlama zamanı
    last_reset = Column(DateTime, default=datetime.utcnow)

    # Abonelik tarihleri
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # null = lifetime/free

    # İlişkiler
    user = relationship("User", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription {self.user_id}: {self.plan}>"


class Conversation(Base):
    """Sohbet oturumu"""
    __tablename__ = "conversations"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Sohbet bilgileri
    title = Column(String(200), default="Yeni Sohbet")
    subject = Column(String(50), nullable=True)  # Matematik, Fizik, etc.
    grade = Column(Integer, nullable=True)

    # Durum
    is_archived = Column(Boolean, default=False)

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def __repr__(self):
        return f"<Conversation {self.id}: {self.title}>"


class Message(Base):
    """Sohbet mesajı"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=False, index=True)

    # Mesaj içeriği
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)

    # Görsel (varsa) - Base64 encoded images can be very large
    image_url = Column(Text, nullable=True)

    # RAG analiz referansı
    analysis_id = Column(String(50), nullable=True)

    # Extra data (kazanımlar, kaynaklar vs.)
    extra_data = Column(JSON, default=dict)

    # Zaman damgası
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.id}: {self.role}>"


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


# ================== KULLANICI KAZANIM İLERLEME TAKİBİ ==================

class GeneratedExam(Base):
    """
    Oluşturulan sınav PDF'leri.
    Kullanıcının takip ettiği kazanımlara göre LLM destekli sınav oluşturma.
    """
    __tablename__ = "generated_exams"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Sınav bilgileri
    title = Column(String(200), default="Çalışma Sınavı")
    pdf_path = Column(String(512), nullable=False)
    question_count = Column(Integer, nullable=False)

    # Kapsanan kazanımlar ve sorular (JSON)
    kazanimlar_json = Column(JSON, default=list)  # ["MAT.10.1.1", "MAT.10.1.2"]
    questions_json = Column(JSON, default=list)   # [{"file": "...", "kazanim": "...", "difficulty": "...", "answer": "..."}]

    # Zorluk dağılımı
    difficulty_distribution = Column(JSON, default=dict)  # {"kolay": 3, "orta": 5, "zor": 2}

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    user = relationship("User", back_populates="generated_exams")

    def __repr__(self):
        return f"<GeneratedExam {self.id}: {self.title}>"


class UserKazanimProgress(Base):
    """
    Kullanıcı kazanım ilerleme takibi.
    Sohbette yüksek güven skorlu kazanımlar otomatik takibe alınır.
    AI, öğrencinin anlayışını tespit ettiğinde durum güncellenir.
    """
    __tablename__ = "user_kazanim_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kazanim_code = Column(String(50), nullable=False, index=True)

    # Durum: tracked -> in_progress -> understood
    status = Column(String(20), default="tracked")

    # Güven skorları
    initial_confidence_score = Column(Float, default=0.0)  # İlk takip edildiğindeki skor
    understanding_confidence = Column(Float, nullable=True)  # AI'ın anlama tespiti güveni

    # Kaynak takibi
    source_conversation_id = Column(String(50), ForeignKey("conversations.id"), nullable=True)

    # Zaman damgaları
    tracked_at = Column(DateTime, default=datetime.utcnow)
    understood_at = Column(DateTime, nullable=True)

    # AI tespit sinyalleri (JSON array)
    # Örnek: ["correct_explanation", "teach_back"]
    understanding_signals = Column(JSON, default=list)

    # İlişkiler
    user = relationship("User", back_populates="kazanim_progress")
    source_conversation = relationship("Conversation")

    # Composite unique constraint - bir kullanıcı bir kazanımı sadece bir kez takip edebilir
    __table_args__ = (
        Index("ix_user_kazanim_progress_user_status", "user_id", "status"),
        Index("ix_user_kazanim_progress_user_code", "user_id", "kazanim_code", unique=True),
    )

    def __repr__(self):
        return f"<UserKazanimProgress {self.user_id}:{self.kazanim_code}:{self.status}>"


# ================== SINIF VE ÖDEV YÖNETİMİ (SaaS) ==================

class Classroom(Base):
    """
    Öğretmen tarafından yönetilen sınıf.
    Öğrenciler join_code ile sınıfa katılır.
    """
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Sınıf bilgileri
    name = Column(String(100), nullable=False)  # "10-A Matematik"
    grade = Column(Integer, nullable=False)  # 1-12
    subject = Column(String(50), nullable=True)  # Matematik, Fizik, vb.

    # Katılım kodu
    join_code = Column(String(8), unique=True, index=True, nullable=False)
    join_enabled = Column(Boolean, default=True)

    # Durum
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    school = relationship("School", back_populates="classrooms")
    teacher = relationship("User", back_populates="classrooms_teaching", foreign_keys=[teacher_id])
    enrollments = relationship("StudentEnrollment", back_populates="classroom", cascade="all, delete-orphan")
    class_assignments = relationship("ClassAssignment", back_populates="classroom", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_classroom_school_teacher", "school_id", "teacher_id"),
    )

    def __repr__(self):
        return f"<Classroom {self.id}: {self.name}>"


class StudentEnrollment(Base):
    """Öğrenci sınıf kaydı"""
    __tablename__ = "student_enrollments"

    id = Column(Integer, primary_key=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Durum
    status = Column(String(20), default="active")  # active, inactive, removed
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)

    # İlişkiler
    classroom = relationship("Classroom", back_populates="enrollments")
    student = relationship("User")

    __table_args__ = (
        Index("ix_enrollment_unique", "classroom_id", "student_id", unique=True),
    )

    def __repr__(self):
        return f"<StudentEnrollment {self.classroom_id}:{self.student_id}>"


class Assignment(Base):
    """
    Öğretmen tarafından oluşturulan ödev/sınav.
    Birden fazla sınıfa dağıtılabilir.
    """
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Ödev bilgileri
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Ödev tipi
    assignment_type = Column(String(30), default="practice")  # practice, exam, homework

    # Hedef kazanımlar
    target_kazanimlar = Column(JSON, default=list)  # ["M.10.1.1", "M.10.1.2"]

    # İlişkili sınav (opsiyonel)
    exam_id = Column(String(50), ForeignKey("generated_exams.id"), nullable=True)

    # Tarihler
    assigned_at = Column(DateTime, default=datetime.utcnow)
    due_at = Column(DateTime, nullable=True)

    # Durum
    is_active = Column(Boolean, default=True)

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    school = relationship("School", back_populates="assignments")
    created_by = relationship("User", back_populates="created_assignments", foreign_keys=[created_by_id])
    exam = relationship("GeneratedExam")
    class_assignments = relationship("ClassAssignment", back_populates="assignment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Assignment {self.id}: {self.title}>"


class ClassAssignment(Base):
    """Ödevin sınıfa dağıtımı"""
    __tablename__ = "class_assignments"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False, index=True)

    # Sınıfa özel son tarih
    due_at_override = Column(DateTime, nullable=True)

    # Dağıtım takibi
    distributed_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    assignment = relationship("Assignment", back_populates="class_assignments")
    classroom = relationship("Classroom", back_populates="class_assignments")
    submissions = relationship("AssignmentSubmission", back_populates="class_assignment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_class_assignment_unique", "assignment_id", "classroom_id", unique=True),
    )

    def __repr__(self):
        return f"<ClassAssignment {self.assignment_id}:{self.classroom_id}>"


class AssignmentSubmission(Base):
    """Öğrenci ödev teslimi/ilerlemesi"""
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True)
    class_assignment_id = Column(Integer, ForeignKey("class_assignments.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Durum takibi
    status = Column(String(20), default="pending")  # pending, started, submitted, graded

    # Tamamlama metrikleri
    started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)

    # Sınav tipi ödevler için
    score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)

    # Ödev sırasında kazanım ilerlemesi
    kazanimlar_progress = Column(JSON, default=dict)  # {"M.10.1.1": "understood"}

    # Zaman damgaları
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    class_assignment = relationship("ClassAssignment", back_populates="submissions")
    student = relationship("User")

    __table_args__ = (
        Index("ix_submission_unique", "class_assignment_id", "student_id", unique=True),
    )

    def __repr__(self):
        return f"<AssignmentSubmission {self.class_assignment_id}:{self.student_id}:{self.status}>"
