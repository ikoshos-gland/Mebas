"""
Classroom CRUD Routes
Öğretmenler için sınıf CRUD operasyonları.
"""
import logging
import secrets
import string
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from api.auth.deps import (
    get_current_active_user,
    get_current_teacher,
    verify_teacher_owns_classroom,
    require_school_membership,
    get_db
)
from api.auth.permissions import Role
from src.database.models import (
    User, School, Classroom, StudentEnrollment, UserKazanimProgress,
    Assignment, AssignmentSubmission, ClassAssignment
)

logger = logging.getLogger("api.classrooms")

router = APIRouter(tags=["Classrooms"])


# ================== SCHEMAS ==================

class ClassroomCreate(BaseModel):
    """Sınıf oluşturma şeması"""
    name: str = Field(..., min_length=2, max_length=100)
    grade: int = Field(..., ge=1, le=12)
    subject: Optional[str] = Field(None, max_length=50)


class ClassroomUpdate(BaseModel):
    """Sınıf güncelleme şeması"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    subject: Optional[str] = Field(None, max_length=50)
    join_enabled: Optional[bool] = None


class ClassroomResponse(BaseModel):
    """Sınıf yanıt şeması"""
    id: int
    name: str
    grade: int
    subject: Optional[str]
    join_code: str
    join_enabled: bool
    student_count: int = 0
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class ClassroomListResponse(BaseModel):
    """Sınıf listesi yanıtı"""
    items: List[ClassroomResponse]
    total: int


class EnrollmentInfo(BaseModel):
    """Öğrenci kayıt bilgisi"""
    id: int
    student_id: int
    student_name: str
    student_email: str
    student_grade: Optional[int] = None
    status: str
    enrolled_at: datetime
    removed_at: Optional[datetime] = None


class ClassroomDetailResponse(ClassroomResponse):
    """Sınıf detay yanıtı - kayıtlı öğrencilerle birlikte"""
    enrollments: List[EnrollmentInfo] = []


class StudentProgressSummary(BaseModel):
    """Öğrenci ilerleme özeti"""
    student_id: int
    student_name: str
    email: str
    tracked_count: int
    understood_count: int
    in_progress_count: int
    last_activity: Optional[datetime]


class ClassProgressResponse(BaseModel):
    """Sınıf ilerleme yanıtı"""
    classroom_id: int
    classroom_name: str
    total_students: int
    students: List[StudentProgressSummary]
    aggregate: dict


class CurriculumKazanim(BaseModel):
    """Müfredat kazanımı"""
    code: str
    description: str
    title: Optional[str] = None
    semester: Optional[int] = None
    grade: Optional[int] = None
    subject: Optional[str] = None


class StudentKazanimProgressItem(BaseModel):
    """Öğrencinin tek bir kazanım üzerindeki ilerlemesi"""
    kazanim_code: str
    status: str  # understood, in_progress, tracked, not_started
    initial_confidence_score: Optional[float] = None
    understanding_confidence: Optional[float] = None
    tracked_at: Optional[datetime] = None
    understood_at: Optional[datetime] = None


class StudentProgressDetailResponse(BaseModel):
    """Öğrenci detaylı ilerleme yanıtı - müfredatla birlikte"""
    student: Dict[str, Any]
    classroom: Dict[str, Any]
    summary: Dict[str, int]
    progress_by_code: Dict[str, StudentKazanimProgressItem]
    curriculum: List[CurriculumKazanim]


# ================== HELPER FUNCTIONS ==================

def generate_join_code() -> str:
    """Benzersiz 8 karakterlik katılım kodu oluşturur."""
    chars = string.ascii_uppercase + string.digits
    # I, O, 0, 1 gibi karışıklık yaratabilecek karakterleri çıkar
    chars = chars.replace('I', '').replace('O', '').replace('0', '').replace('1', '')
    return ''.join(secrets.choice(chars) for _ in range(8))


def get_classroom_with_count(db: Session, classroom: Classroom) -> ClassroomResponse:
    """Sınıfı öğrenci sayısıyla birlikte döndürür."""
    student_count = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).count()

    teacher = db.query(User).filter(User.id == classroom.teacher_id).first()

    return ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        grade=classroom.grade,
        subject=classroom.subject,
        join_code=classroom.join_code,
        join_enabled=classroom.join_enabled,
        student_count=student_count,
        is_active=classroom.is_active,
        is_archived=classroom.is_archived,
        created_at=classroom.created_at,
        updated_at=classroom.updated_at,
        teacher_name=teacher.full_name if teacher else None
    )


async def fetch_kazanimlar_by_codes(codes: List[str]) -> List[CurriculumKazanim]:
    """
    Azure Search'ten belirli kazanım kodlarına göre kazanımları getirir.
    """
    import asyncio
    from config.azure_config import get_search_client
    from config.settings import get_settings

    if not codes:
        return []

    settings = get_settings()
    client = get_search_client(settings.azure_search_index_kazanim)

    # OData filter: code eq 'X' or code eq 'Y' ...
    code_filters = " or ".join([f"code eq '{c}'" for c in codes])
    filter_str = f"({code_filters})"

    try:
        results = await asyncio.to_thread(
            client.search,
            search_text="*",
            filter=filter_str,
            top=len(codes),
            select=["code", "description", "title", "semester", "grade", "subject"]
        )

        kazanimlar = []
        found_codes = set()
        for r in results:
            code = r.get("code", "")
            found_codes.add(code)
            kazanimlar.append(CurriculumKazanim(
                code=code,
                description=r.get("description", ""),
                title=r.get("title"),
                semester=r.get("semester"),
                grade=r.get("grade"),
                subject=r.get("subject")
            ))

        # Bulunamayan kodlar için placeholder ekle
        for code in codes:
            if code not in found_codes:
                kazanimlar.append(CurriculumKazanim(
                    code=code,
                    description="Kazanım detayı bulunamadı",
                    title=None,
                    semester=None,
                    grade=None,
                    subject=None
                ))

        return kazanimlar
    except Exception as e:
        logger.error(f"Error fetching kazanimlar by codes: {e}")
        # Hata durumunda placeholder döndür
        return [CurriculumKazanim(
            code=c,
            description="Kazanım detayı yüklenemedi",
            title=None,
            semester=None,
            grade=None,
            subject=None
        ) for c in codes]


async def fetch_curriculum_kazanimlar(
    grade: int,
    subject: Optional[str] = None
) -> List[CurriculumKazanim]:
    """
    Azure Search'ten belirli bir sınıf/ders için tüm kazanımları getirir.
    """
    import asyncio
    from config.azure_config import get_search_client
    from config.settings import get_settings

    settings = get_settings()
    client = get_search_client(settings.azure_search_index_kazanim)

    # Filter oluştur
    filters = [f"grade eq {grade}"]
    if subject:
        filters.append(f"subject eq '{subject}'")
    filter_str = " and ".join(filters)

    try:
        # Tüm kazanımları getir (müfredat sınırlı olduğundan pagination gerekmiyor)
        results = await asyncio.to_thread(
            client.search,
            search_text="*",
            filter=filter_str,
            top=500,
            order_by=["code asc"],
            select=["code", "description", "title", "semester", "grade", "subject"]
        )

        kazanimlar = []
        for r in results:
            kazanimlar.append(CurriculumKazanim(
                code=r.get("code", ""),
                description=r.get("description", ""),
                title=r.get("title"),
                semester=r.get("semester"),
                grade=r.get("grade"),
                subject=r.get("subject")
            ))

        return kazanimlar
    except Exception as e:
        logger.error(f"Error fetching curriculum kazanimlar: {e}")
        return []


# ================== TEACHER ROUTES ==================

@router.get("/", response_model=ClassroomListResponse)
async def list_classrooms(
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db),
    include_archived: bool = Query(False),
    grade: Optional[int] = Query(None, ge=1, le=12),
    subject: Optional[str] = None
):
    """
    Öğretmenin sınıflarını listeler.
    Öğretmen yetkisi gerektirir.
    """
    query = db.query(Classroom).filter(
        Classroom.teacher_id == current_user.id,
        Classroom.school_id == current_user.school_id
    )

    if not include_archived:
        query = query.filter(Classroom.is_archived == False)

    if grade:
        query = query.filter(Classroom.grade == grade)

    if subject:
        query = query.filter(Classroom.subject == subject)

    classrooms = query.order_by(Classroom.created_at.desc()).all()

    items = [get_classroom_with_count(db, c) for c in classrooms]

    return ClassroomListResponse(items=items, total=len(items))


@router.post("/", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    request: ClassroomCreate,
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Yeni sınıf oluşturur.
    Öğretmen yetkisi gerektirir.
    """
    # Okul kontrolü
    if not current_user.school_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sınıf oluşturmak için bir okula üye olmalısınız"
        )

    school = db.query(School).filter(School.id == current_user.school_id).first()
    if not school or not school.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Okul aktif değil"
        )

    # Benzersiz join kodu oluştur
    join_code = generate_join_code()
    while db.query(Classroom).filter(Classroom.join_code == join_code).first():
        join_code = generate_join_code()

    classroom = Classroom(
        school_id=current_user.school_id,
        teacher_id=current_user.id,
        name=request.name,
        grade=request.grade,
        subject=request.subject,
        join_code=join_code,
    )

    db.add(classroom)
    db.commit()
    db.refresh(classroom)

    logger.info(f"Classroom created: {classroom.name} by {current_user.email}")

    return get_classroom_with_count(db, classroom)


@router.get("/{classroom_id}", response_model=ClassroomDetailResponse)
async def get_classroom(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıf detaylarını kayıtlı öğrencilerle birlikte getirir.
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    # Temel sınıf bilgilerini al
    base_response = get_classroom_with_count(db, classroom)

    # Kayıtlı öğrencileri getir
    enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id
    ).all()

    enrollment_list = []
    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.student_id).first()
        if student:
            enrollment_list.append(EnrollmentInfo(
                id=enrollment.id,
                student_id=student.id,
                student_name=student.full_name,
                student_email=student.email,
                student_grade=student.grade,
                status=enrollment.status,
                enrolled_at=enrollment.enrolled_at,
                removed_at=enrollment.removed_at
            ))

    return ClassroomDetailResponse(
        **base_response.model_dump(),
        enrollments=enrollment_list
    )


@router.put("/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    request: ClassroomUpdate,
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıf bilgilerini günceller.
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(classroom, key, value)

    db.commit()
    db.refresh(classroom)

    logger.info(f"Classroom updated: {classroom.name}")

    return get_classroom_with_count(db, classroom)


@router.post("/{classroom_id}/regenerate-code", response_model=ClassroomResponse)
async def regenerate_join_code(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıf katılım kodunu yeniler.
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    new_code = generate_join_code()
    while db.query(Classroom).filter(Classroom.join_code == new_code).first():
        new_code = generate_join_code()

    classroom.join_code = new_code
    db.commit()
    db.refresh(classroom)

    logger.info(f"Join code regenerated for classroom: {classroom.name}")

    return get_classroom_with_count(db, classroom)


@router.post("/{classroom_id}/archive", response_model=ClassroomResponse)
async def archive_classroom(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıfı arşivler.
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    classroom.is_archived = True
    classroom.join_enabled = False
    db.commit()
    db.refresh(classroom)

    logger.info(f"Classroom archived: {classroom.name}")

    return get_classroom_with_count(db, classroom)


@router.post("/{classroom_id}/unarchive", response_model=ClassroomResponse)
async def unarchive_classroom(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıfı arşivden çıkarır.
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    classroom.is_archived = False
    db.commit()
    db.refresh(classroom)

    logger.info(f"Classroom unarchived: {classroom.name}")

    return get_classroom_with_count(db, classroom)


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_classroom(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıfı siler (hard delete).
    Dikkat: Tüm kayıtlar silinir!
    Sınıfın sahibi öğretmen yetkisi gerektirir.
    """
    classroom_name = classroom.name
    db.delete(classroom)
    db.commit()

    logger.info(f"Classroom deleted: {classroom_name}")

    return None


# ================== PROGRESS ROUTES ==================

@router.get("/{classroom_id}/progress", response_model=ClassProgressResponse)
async def get_classroom_progress(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Sınıftaki tüm öğrencilerin ilerleme özetini getirir.
    Öğretmen yetkisi gerektirir.

    Optimized: Tek bir JOIN + GROUP BY sorgusu kullanır (N+1 yerine 2 sorgu).
    """
    # Aktif öğrenci ID'lerini al
    student_subq = db.query(StudentEnrollment.student_id).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).subquery()

    # Tek sorguda tüm verileri çek (JOIN + conditional aggregation)
    progress_stats = db.query(
        User.id.label("student_id"),
        User.full_name.label("student_name"),
        User.email,
        func.count(case((UserKazanimProgress.status == "tracked", 1))).label("tracked_count"),
        func.count(case((UserKazanimProgress.status == "understood", 1))).label("understood_count"),
        func.count(case((UserKazanimProgress.status == "in_progress", 1))).label("in_progress_count"),
        func.max(UserKazanimProgress.tracked_at).label("last_activity")
    ).select_from(User)\
    .outerjoin(UserKazanimProgress, UserKazanimProgress.user_id == User.id)\
    .filter(User.id.in_(student_subq))\
    .group_by(User.id, User.full_name, User.email)\
    .all()

    # Sonuçları StudentProgressSummary listesine dönüştür
    students = []
    total_tracked = 0
    total_understood = 0
    total_in_progress = 0

    for stat in progress_stats:
        students.append(StudentProgressSummary(
            student_id=stat.student_id,
            student_name=stat.student_name,
            email=stat.email,
            tracked_count=stat.tracked_count,
            understood_count=stat.understood_count,
            in_progress_count=stat.in_progress_count,
            last_activity=stat.last_activity
        ))

        total_tracked += stat.tracked_count
        total_understood += stat.understood_count
        total_in_progress += stat.in_progress_count

    # Sıralama: anlaşılan sayısına göre azalan
    students.sort(key=lambda x: x.understood_count, reverse=True)

    return ClassProgressResponse(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        total_students=len(students),
        students=students,
        aggregate={
            "total_tracked": total_tracked,
            "total_understood": total_understood,
            "total_in_progress": total_in_progress,
            "avg_understood": round(total_understood / len(students), 1) if students else 0
        }
    )


@router.get("/{classroom_id}/progress/{student_id}", response_model=StudentProgressDetailResponse)
async def get_student_progress_detail(
    student_id: int,
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Belirli bir öğrencinin detaylı ilerleme bilgisini müfredatla birlikte getirir.
    Öğretmen yetkisi gerektirir.
    Tüm müfredat kazanımlarını döndürür, öğrenci ilerlemesiyle eşleştirir.
    """
    # Öğrencinin sınıfa kayıtlı olduğunu doğrula
    enrollment = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bu sınıfa kayıtlı değil"
        )

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bulunamadı"
        )

    # Tüm ilerleme kayıtlarını getir
    progress_records = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == student_id
    ).order_by(UserKazanimProgress.tracked_at.desc()).all()

    # Müfredat kazanımlarını getir
    curriculum = await fetch_curriculum_kazanimlar(
        grade=classroom.grade,
        subject=classroom.subject
    )

    # İlerleme kayıtlarını kod bazında dict'e çevir
    progress_by_code: Dict[str, StudentKazanimProgressItem] = {}
    for p in progress_records:
        progress_by_code[p.kazanim_code] = StudentKazanimProgressItem(
            kazanim_code=p.kazanim_code,
            status=p.status,
            initial_confidence_score=p.initial_confidence_score,
            understanding_confidence=p.understanding_confidence,
            tracked_at=p.tracked_at,
            understood_at=p.understood_at
        )

    # Müfredattaki kazanımlar için not_started durumlarını ekle
    for k in curriculum:
        if k.code not in progress_by_code:
            progress_by_code[k.code] = StudentKazanimProgressItem(
                kazanim_code=k.code,
                status="not_started"
            )

    # Öğrencinin takip ettiği ama müfredatta olmayan kazanımları da ekle
    curriculum_codes = {k.code for k in curriculum}
    extra_codes = [p.kazanim_code for p in progress_records if p.kazanim_code not in curriculum_codes]

    if extra_codes:
        # Azure Search'ten bu kazanımların detaylarını getir
        extra_kazanimlar = await fetch_kazanimlar_by_codes(extra_codes)
        curriculum.extend(extra_kazanimlar)

    # İstatistikleri hesapla
    tracked_count = len([p for p in progress_records if p.status == "tracked"])
    in_progress_count = len([p for p in progress_records if p.status == "in_progress"])
    understood_count = len([p for p in progress_records if p.status == "understood"])
    not_started_count = len(curriculum) - len(progress_records)

    return StudentProgressDetailResponse(
        student={
            "id": student.id,
            "full_name": student.full_name,
            "email": student.email,
            "grade": student.grade,
        },
        classroom={
            "id": classroom.id,
            "name": classroom.name,
            "grade": classroom.grade,
            "subject": classroom.subject,
        },
        summary={
            "tracked": tracked_count,
            "in_progress": in_progress_count,
            "understood": understood_count,
            "not_started": max(0, not_started_count),
            "total": len(curriculum),
        },
        progress_by_code=progress_by_code,
        curriculum=curriculum
    )


# ================== DASHBOARD ROUTES ==================

class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response"""
    total_classrooms: int
    total_students: int
    active_assignments: int
    pending_submissions: int
    avg_performance: float
    this_week_activity: int


class ActivityItem(BaseModel):
    """Activity feed item"""
    id: int
    type: str  # enrollment, submission, assignment
    description: str
    student_name: Optional[str] = None
    classroom_name: Optional[str] = None
    timestamp: datetime


class DashboardActivityResponse(BaseModel):
    """Dashboard activity response"""
    items: List[ActivityItem]
    total: int


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_teacher_dashboard_stats(
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated dashboard statistics for the teacher.
    """
    from datetime import timedelta

    # Get teacher's classrooms
    classrooms = db.query(Classroom).filter(
        Classroom.teacher_id == current_user.id,
        Classroom.is_archived == False
    ).all()

    classroom_ids = [c.id for c in classrooms]

    # Total students across all classrooms
    total_students = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id.in_(classroom_ids),
        StudentEnrollment.status == "active"
    ).count() if classroom_ids else 0

    # Active assignments (created by teacher)
    active_assignments = db.query(Assignment).filter(
        Assignment.created_by_id == current_user.id,
        Assignment.is_active == True
    ).count()

    # Pending submissions (not yet submitted)
    pending_submissions = 0
    if classroom_ids:
        # Get all class assignments for teacher's classrooms
        class_assignment_ids = db.query(ClassAssignment.id).filter(
            ClassAssignment.classroom_id.in_(classroom_ids)
        ).all()
        ca_ids = [ca.id for ca in class_assignment_ids]

        if ca_ids:
            # Count submissions that are 'assigned' or 'in_progress' (not submitted)
            pending_submissions = db.query(AssignmentSubmission).filter(
                AssignmentSubmission.class_assignment_id.in_(ca_ids),
                AssignmentSubmission.status.in_(["assigned", "in_progress"])
            ).count()

    # Average performance (avg mastery across students)
    avg_performance = 0.0
    if classroom_ids:
        student_ids = db.query(StudentEnrollment.student_id).filter(
            StudentEnrollment.classroom_id.in_(classroom_ids),
            StudentEnrollment.status == "active"
        ).distinct().all()
        student_ids = [s.student_id for s in student_ids]

        if student_ids:
            total_understood = db.query(UserKazanimProgress).filter(
                UserKazanimProgress.user_id.in_(student_ids),
                UserKazanimProgress.status == "understood"
            ).count()
            total_tracked = db.query(UserKazanimProgress).filter(
                UserKazanimProgress.user_id.in_(student_ids)
            ).count()
            if total_tracked > 0:
                avg_performance = round((total_understood / total_tracked) * 100, 1)

    # Activity this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    this_week_activity = 0

    if classroom_ids:
        # Enrollments this week
        enrollments_this_week = db.query(StudentEnrollment).filter(
            StudentEnrollment.classroom_id.in_(classroom_ids),
            StudentEnrollment.enrolled_at >= week_ago
        ).count()
        this_week_activity += enrollments_this_week

    return DashboardStatsResponse(
        total_classrooms=len(classrooms),
        total_students=total_students,
        active_assignments=active_assignments,
        pending_submissions=pending_submissions,
        avg_performance=avg_performance,
        this_week_activity=this_week_activity
    )


@router.get("/dashboard/activity", response_model=DashboardActivityResponse)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """
    Returns recent activity feed for the teacher's classrooms.
    """
    # Get teacher's classroom IDs
    classrooms = db.query(Classroom).filter(
        Classroom.teacher_id == current_user.id
    ).all()
    classroom_map = {c.id: c.name for c in classrooms}
    classroom_ids = list(classroom_map.keys())

    if not classroom_ids:
        return DashboardActivityResponse(items=[], total=0)

    activities = []

    # Get recent enrollments
    enrollments = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id.in_(classroom_ids)
    ).order_by(StudentEnrollment.enrolled_at.desc()).limit(limit).all()

    for enrollment in enrollments:
        student = db.query(User).filter(User.id == enrollment.student_id).first()
        if student:
            activities.append(ActivityItem(
                id=enrollment.id,
                type="enrollment",
                description=f"{student.full_name} sinifa katildi",
                student_name=student.full_name,
                classroom_name=classroom_map.get(enrollment.classroom_id, ""),
                timestamp=enrollment.enrolled_at
            ))

    # Sort by timestamp and limit
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    activities = activities[:limit]

    return DashboardActivityResponse(
        items=activities,
        total=len(activities)
    )


# ================== ANALYTICS ROUTES ==================

class KazanimStatistic(BaseModel):
    """Kazanım bazında sınıf istatistiği"""
    kazanim_code: str
    kazanim_description: str
    grade: Optional[int] = None
    subject: Optional[str] = None
    understood_count: int      # Anlayan öğrenci sayısı
    in_progress_count: int     # Çalışan öğrenci sayısı
    tracked_count: int         # Takip eden öğrenci sayısı
    total_students: int        # Bu kazanımı takip eden toplam öğrenci
    mastery_rate: float        # Başarı oranı (%)


class KazanimAnalyticsResponse(BaseModel):
    """Sınıf kazanım analitik yanıtı"""
    classroom_id: int
    classroom_name: str
    total_students: int
    most_understood: List[KazanimStatistic]    # En çok anlaşılan 10
    least_understood: List[KazanimStatistic]   # En az anlaşılan 10
    all_kazanimlar: List[KazanimStatistic]
    summary: Dict[str, Any]


@router.get("/{classroom_id}/analytics", response_model=KazanimAnalyticsResponse)
async def get_classroom_analytics(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Kazanım bazında sınıf analizi getirir.
    Her kazanım için kaç öğrenci anladı/çalışıyor/takipte bilgisini verir.
    Hangi konularda öğrenciler zorlanıyor, hangi konular iyi anlaşılmış görülür.
    """
    # Aktif öğrenci ID'lerini al
    student_ids = [e.student_id for e in db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).all()]

    if not student_ids:
        return KazanimAnalyticsResponse(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            total_students=0,
            most_understood=[],
            least_understood=[],
            all_kazanimlar=[],
            summary={"avg_mastery_rate": 0, "total_unique_kazanimlar": 0}
        )

    # Kazanım bazında aggregation
    kazanim_stats = db.query(
        UserKazanimProgress.kazanim_code,
        func.count(case((UserKazanimProgress.status == "understood", 1))).label("understood_count"),
        func.count(case((UserKazanimProgress.status == "in_progress", 1))).label("in_progress_count"),
        func.count(case((UserKazanimProgress.status == "tracked", 1))).label("tracked_count"),
        func.count(UserKazanimProgress.id).label("total_students")
    ).filter(
        UserKazanimProgress.user_id.in_(student_ids)
    ).group_by(
        UserKazanimProgress.kazanim_code
    ).all()

    if not kazanim_stats:
        return KazanimAnalyticsResponse(
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            total_students=len(student_ids),
            most_understood=[],
            least_understood=[],
            all_kazanimlar=[],
            summary={"avg_mastery_rate": 0, "total_unique_kazanimlar": 0}
        )

    # Azure Search'ten kazanım detaylarını getir
    kazanim_codes = [k.kazanim_code for k in kazanim_stats]
    kazanim_details = await fetch_kazanimlar_by_codes(kazanim_codes)
    details_map = {k.code: k for k in kazanim_details}

    # İstatistik listesini oluştur
    all_stats = []
    for stat in kazanim_stats:
        detail = details_map.get(stat.kazanim_code)
        mastery_rate = (stat.understood_count / stat.total_students * 100) if stat.total_students > 0 else 0

        all_stats.append(KazanimStatistic(
            kazanim_code=stat.kazanim_code,
            kazanim_description=detail.description if detail else "Bilinmiyor",
            grade=detail.grade if detail else None,
            subject=detail.subject if detail else None,
            understood_count=stat.understood_count,
            in_progress_count=stat.in_progress_count,
            tracked_count=stat.tracked_count,
            total_students=stat.total_students,
            mastery_rate=round(mastery_rate, 1)
        ))

    # Başarı oranına göre sırala
    sorted_by_mastery = sorted(all_stats, key=lambda x: x.mastery_rate, reverse=True)

    # Ortalama başarı oranı
    avg_mastery = sum(s.mastery_rate for s in all_stats) / len(all_stats) if all_stats else 0

    return KazanimAnalyticsResponse(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        total_students=len(student_ids),
        most_understood=sorted_by_mastery[:10],
        least_understood=sorted_by_mastery[-10:][::-1] if len(sorted_by_mastery) > 10 else sorted_by_mastery[::-1],
        all_kazanimlar=all_stats,
        summary={
            "avg_mastery_rate": round(avg_mastery, 1),
            "total_unique_kazanimlar": len(all_stats)
        }
    )


# ================== EXPORT ROUTES ==================

from fastapi.responses import StreamingResponse
import csv
import io


@router.get("/{classroom_id}/export/csv")
async def export_classroom_progress_csv(
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Sınıf ilerleme verilerini CSV olarak indirir.
    Tüm öğrencilerin kazanım istatistiklerini içerir.
    """
    # Optimize edilmiş sorguyu kullan
    student_subq = db.query(StudentEnrollment.student_id).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.status == "active"
    ).subquery()

    progress_stats = db.query(
        User.id.label("student_id"),
        User.full_name.label("student_name"),
        User.email,
        func.count(case((UserKazanimProgress.status == "tracked", 1))).label("tracked_count"),
        func.count(case((UserKazanimProgress.status == "understood", 1))).label("understood_count"),
        func.count(case((UserKazanimProgress.status == "in_progress", 1))).label("in_progress_count"),
        func.max(UserKazanimProgress.tracked_at).label("last_activity")
    ).select_from(User)\
    .outerjoin(UserKazanimProgress, UserKazanimProgress.user_id == User.id)\
    .filter(User.id.in_(student_subq))\
    .group_by(User.id, User.full_name, User.email)\
    .order_by(User.full_name)\
    .all()

    # CSV oluştur
    output = io.StringIO()
    writer = csv.writer(output)

    # Header (Türkçe)
    writer.writerow([
        "Ogrenci Adi", "E-posta", "Anladi", "Calisiyor",
        "Takipte", "Toplam", "Basari %", "Son Aktivite"
    ])

    # Data rows
    for stat in progress_stats:
        total = stat.understood_count + stat.in_progress_count + stat.tracked_count
        mastery = (stat.understood_count / total * 100) if total > 0 else 0
        last_activity = stat.last_activity.strftime("%Y-%m-%d") if stat.last_activity else "-"

        writer.writerow([
            stat.student_name,
            stat.email,
            stat.understood_count,
            stat.in_progress_count,
            stat.tracked_count,
            total,
            f"{mastery:.1f}%",
            last_activity
        ])

    output.seek(0)

    # Dosya adı
    safe_name = classroom.name.replace(" ", "_").replace("/", "-")
    filename = f"{safe_name}_ilerleme_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{classroom_id}/progress/{student_id}/export/csv")
async def export_student_progress_csv(
    student_id: int,
    classroom: Classroom = Depends(verify_teacher_owns_classroom),
    db: Session = Depends(get_db)
):
    """
    Tek öğrenci ilerleme verilerini CSV olarak indirir.
    Tüm kazanımların detaylarını içerir.
    """
    # Öğrencinin sınıfa kayıtlı olduğunu doğrula
    enrollment = db.query(StudentEnrollment).filter(
        StudentEnrollment.classroom_id == classroom.id,
        StudentEnrollment.student_id == student_id,
        StudentEnrollment.status == "active"
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bu sınıfa kayıtlı değil"
        )

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Öğrenci bulunamadı"
        )

    # İlerleme kayıtlarını getir
    progress_records = db.query(UserKazanimProgress).filter(
        UserKazanimProgress.user_id == student_id
    ).order_by(UserKazanimProgress.kazanim_code).all()

    # Kazanım detaylarını getir
    codes = [p.kazanim_code for p in progress_records]
    kazanim_details = await fetch_kazanimlar_by_codes(codes) if codes else []
    details_map = {k.code: k for k in kazanim_details}

    # CSV oluştur
    output = io.StringIO()
    writer = csv.writer(output)

    # Üst bilgi
    writer.writerow([f"Ogrenci: {student.full_name}"])
    writer.writerow([f"Sinif: {classroom.name}"])
    writer.writerow([f"Tarih: {datetime.utcnow().strftime('%Y-%m-%d')}"])
    writer.writerow([])

    # Sütun başlıkları
    writer.writerow([
        "Kazanim Kodu", "Aciklama", "Durum",
        "Guven Skoru", "Takip Tarihi", "Anlama Tarihi"
    ])

    # Durum etiketleri
    status_labels = {
        "understood": "Anladi",
        "in_progress": "Calisiyor",
        "tracked": "Takipte"
    }

    # Data
    for p in progress_records:
        detail = details_map.get(p.kazanim_code)
        description = detail.description[:80] + "..." if detail and len(detail.description) > 80 else (detail.description if detail else "-")
        confidence = p.understanding_confidence or p.initial_confidence_score or 0

        writer.writerow([
            p.kazanim_code,
            description,
            status_labels.get(p.status, p.status),
            f"{confidence * 100:.0f}%",
            p.tracked_at.strftime("%Y-%m-%d") if p.tracked_at else "-",
            p.understood_at.strftime("%Y-%m-%d") if p.understood_at else "-"
        ])

    output.seek(0)

    # Dosya adı
    safe_name = student.full_name.replace(" ", "_").replace("/", "-")
    filename = f"{safe_name}_ilerleme_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
