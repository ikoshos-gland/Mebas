"""
Role-Based Access Control (RBAC) System
Rol tabanlı erişim kontrolü için permission ve decorator sistemi.
"""
from enum import Enum
from typing import Set, Optional, List, Callable
from functools import wraps
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from src.database.models import User, School, Classroom, StudentEnrollment


class Role(str, Enum):
    """Kullanıcı rolleri"""
    STUDENT = "student"
    TEACHER = "teacher"
    SCHOOL_ADMIN = "school_admin"
    PLATFORM_ADMIN = "platform_admin"


class Permission(str, Enum):
    """Sistem izinleri"""
    # Öğrenci izinleri
    VIEW_OWN_PROGRESS = "view_own_progress"
    CHAT_WITH_AI = "chat_with_ai"
    VIEW_OWN_CONVERSATIONS = "view_own_conversations"
    GENERATE_PERSONAL_EXAM = "generate_personal_exam"
    JOIN_CLASSROOM = "join_classroom"
    VIEW_ENROLLED_CLASSROOMS = "view_enrolled_classrooms"
    VIEW_MY_ASSIGNMENTS = "view_my_assignments"
    SUBMIT_ASSIGNMENT = "submit_assignment"

    # Öğretmen izinleri
    VIEW_CLASSROOM = "view_classroom"
    CREATE_CLASSROOM = "create_classroom"
    MANAGE_CLASSROOM = "manage_classroom"
    VIEW_STUDENT_PROGRESS = "view_student_progress"
    CREATE_ASSIGNMENT = "create_assignment"
    DISTRIBUTE_ASSIGNMENT = "distribute_assignment"
    VIEW_CLASSROOM_ANALYTICS = "view_classroom_analytics"
    MANAGE_ENROLLMENTS = "manage_enrollments"

    # Okul admin izinleri
    VIEW_SCHOOL_USERS = "view_school_users"
    MANAGE_SCHOOL_USERS = "manage_school_users"
    INVITE_USERS = "invite_users"
    VIEW_SCHOOL_ANALYTICS = "view_school_analytics"
    MANAGE_SCHOOL_SETTINGS = "manage_school_settings"

    # Platform admin izinleri
    CREATE_SCHOOL = "create_school"
    MANAGE_SCHOOLS = "manage_schools"
    VIEW_ALL_USERS = "view_all_users"
    MANAGE_SUBSCRIPTIONS = "manage_subscriptions"
    VIEW_PLATFORM_ANALYTICS = "view_platform_analytics"
    MANAGE_BILLING = "manage_billing"


# Rol -> İzin eşleştirmesi
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.STUDENT: {
        Permission.VIEW_OWN_PROGRESS,
        Permission.CHAT_WITH_AI,
        Permission.VIEW_OWN_CONVERSATIONS,
        Permission.GENERATE_PERSONAL_EXAM,
        Permission.JOIN_CLASSROOM,
        Permission.VIEW_ENROLLED_CLASSROOMS,
        Permission.VIEW_MY_ASSIGNMENTS,
        Permission.SUBMIT_ASSIGNMENT,
    },
    Role.TEACHER: {
        # Öğrenci izinlerini miras alır
        Permission.VIEW_OWN_PROGRESS,
        Permission.CHAT_WITH_AI,
        Permission.VIEW_OWN_CONVERSATIONS,
        Permission.GENERATE_PERSONAL_EXAM,
        # Öğretmene özel
        Permission.VIEW_CLASSROOM,
        Permission.CREATE_CLASSROOM,
        Permission.MANAGE_CLASSROOM,
        Permission.VIEW_STUDENT_PROGRESS,
        Permission.CREATE_ASSIGNMENT,
        Permission.DISTRIBUTE_ASSIGNMENT,
        Permission.VIEW_CLASSROOM_ANALYTICS,
        Permission.MANAGE_ENROLLMENTS,
    },
    Role.SCHOOL_ADMIN: {
        # Öğretmen izinlerini miras alır
        Permission.VIEW_OWN_PROGRESS,
        Permission.CHAT_WITH_AI,
        Permission.VIEW_OWN_CONVERSATIONS,
        Permission.GENERATE_PERSONAL_EXAM,
        Permission.VIEW_CLASSROOM,
        Permission.CREATE_CLASSROOM,
        Permission.MANAGE_CLASSROOM,
        Permission.VIEW_STUDENT_PROGRESS,
        Permission.CREATE_ASSIGNMENT,
        Permission.DISTRIBUTE_ASSIGNMENT,
        Permission.VIEW_CLASSROOM_ANALYTICS,
        Permission.MANAGE_ENROLLMENTS,
        # Okul admin'e özel
        Permission.VIEW_SCHOOL_USERS,
        Permission.MANAGE_SCHOOL_USERS,
        Permission.INVITE_USERS,
        Permission.VIEW_SCHOOL_ANALYTICS,
        Permission.MANAGE_SCHOOL_SETTINGS,
    },
    Role.PLATFORM_ADMIN: {
        # Tüm izinler
        *[p for p in Permission],
    },
}


def has_permission(user: User, permission: Permission) -> bool:
    """
    Kullanıcının belirli bir izne sahip olup olmadığını kontrol eder.

    Args:
        user: Kontrol edilecek kullanıcı
        permission: Kontrol edilecek izin

    Returns:
        bool: Kullanıcının izni varsa True
    """
    try:
        role = Role(user.role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(role, set())


def has_any_permission(user: User, permissions: List[Permission]) -> bool:
    """Kullanıcının verilen izinlerden en az birine sahip olup olmadığını kontrol eder."""
    return any(has_permission(user, p) for p in permissions)


def has_all_permissions(user: User, permissions: List[Permission]) -> bool:
    """Kullanıcının verilen izinlerin tümüne sahip olup olmadığını kontrol eder."""
    return all(has_permission(user, p) for p in permissions)


def get_user_permissions(user: User) -> Set[Permission]:
    """Kullanıcının tüm izinlerini döndürür."""
    try:
        role = Role(user.role)
    except ValueError:
        return set()
    return ROLE_PERMISSIONS.get(role, set())


def require_permission(*permissions: Permission):
    """
    Belirli izinleri gerektiren endpoint decorator'ı.

    Kullanım:
        @router.get("/classroom/{id}")
        @require_permission(Permission.VIEW_CLASSROOM)
        async def get_classroom(current_user: User = Depends(get_current_active_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # current_user'ı kwargs'dan al
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Kimlik doğrulaması gerekli"
                )

            for permission in permissions:
                if not has_permission(current_user, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Bu işlemi yapmak için yetkiniz yok: {permission.value}"
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*roles: Role):
    """
    Belirli rolleri gerektiren endpoint decorator'ı.

    Kullanım:
        @router.post("/classroom")
        @require_role(Role.TEACHER, Role.SCHOOL_ADMIN)
        async def create_classroom(current_user: User = Depends(get_current_active_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Kimlik doğrulaması gerekli"
                )

            try:
                user_role = Role(current_user.role)
            except ValueError:
                user_role = None

            if user_role not in roles:
                role_names = ", ".join([r.value for r in roles])
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Bu sayfaya erişim yetkiniz yok. Gerekli roller: {role_names}"
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_same_school(func: Callable):
    """
    Kullanıcının sadece kendi okulunun kaynaklarına erişebilmesini sağlayan decorator.
    school_id parametresi fonksiyona geçirilmelidir.
    Platform admin tüm okullara erişebilir.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = kwargs.get('current_user')
        school_id = kwargs.get('school_id')

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kimlik doğrulaması gerekli"
            )

        # Platform admin tüm okullara erişebilir
        if current_user.role == Role.PLATFORM_ADMIN.value:
            return await func(*args, **kwargs)

        # Diğer kullanıcılar sadece kendi okullarına erişebilir
        if school_id is not None and current_user.school_id != school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu okula erişim yetkiniz yok"
            )

        return await func(*args, **kwargs)
    return wrapper


# ================== TIER CONFIGURATION ==================

TIER_LIMITS = {
    "small": {
        "max_students": 100,
        "max_teachers": 10,
        "max_classrooms": 20,
        "price_try": 5000.0,
        "features": {
            "exam_generator": True,
            "basic_analytics": True,
            "advanced_analytics": False,
            "api_access": False,
        }
    },
    "medium": {
        "max_students": 500,
        "max_teachers": 50,
        "max_classrooms": 100,
        "price_try": 15000.0,
        "features": {
            "exam_generator": True,
            "basic_analytics": True,
            "advanced_analytics": True,
            "api_access": False,
        }
    },
    "large": {
        "max_students": 2000,
        "max_teachers": 200,
        "max_classrooms": 500,
        "price_try": 40000.0,
        "features": {
            "exam_generator": True,
            "basic_analytics": True,
            "advanced_analytics": True,
            "api_access": True,
        }
    },
}


def get_tier_limits(tier: str) -> dict:
    """Tier limitlerini döndürür."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["small"])


def check_school_limit(school: School, limit_type: str) -> bool:
    """
    Okulun belirli bir limiti aşıp aşmadığını kontrol eder.

    Args:
        school: Kontrol edilecek okul
        limit_type: 'students', 'teachers', 'classrooms'

    Returns:
        bool: Limit dahilindeyse True
    """
    limits = get_tier_limits(school.tier)

    if limit_type == "students":
        return school.max_students <= limits["max_students"]
    elif limit_type == "teachers":
        return school.max_teachers <= limits["max_teachers"]
    elif limit_type == "classrooms":
        return True  # Classroom sayısı ayrıca kontrol edilmeli

    return True
