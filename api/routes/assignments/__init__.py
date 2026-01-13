"""
Assignment Routes Module
Routes for managing assignments and submissions
"""
from fastapi import APIRouter

from .assignment import router as assignment_router
from .submissions import router as submissions_router

router = APIRouter(prefix="/assignments", tags=["assignments"])

# Include sub-routers
router.include_router(assignment_router)
router.include_router(submissions_router)
