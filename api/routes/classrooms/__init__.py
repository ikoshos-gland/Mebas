"""
Classroom Management API Routes
Öğretmenler için sınıf yönetimi API'leri.
"""
from fastapi import APIRouter

from api.routes.classrooms.classroom import router as classroom_router
from api.routes.classrooms.enrollments import router as enrollments_router

router = APIRouter(prefix="/classrooms", tags=["Classrooms"])

# Include sub-routers
# IMPORTANT: enrollments_router MUST be included first because it has static paths
# (/join, /enrolled) that would otherwise be matched by dynamic /{classroom_id} routes
router.include_router(enrollments_router)
router.include_router(classroom_router)
