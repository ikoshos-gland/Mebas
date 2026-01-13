"""
Platform Admin API Routes
Platform yöneticisi için okul ve kullanıcı yönetimi API'leri.
"""
from fastapi import APIRouter

from api.routes.admin.schools import router as schools_router
from api.routes.admin.users import router as users_router
from api.routes.admin.classrooms import router as classrooms_router

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include sub-routers
router.include_router(schools_router)
router.include_router(users_router)
router.include_router(classrooms_router)
