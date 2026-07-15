from fastapi import APIRouter
from app.api.routes import operations, venues, workflow

router = APIRouter()
router.include_router(venues.router, prefix="/venues", tags=["venues"])
router.include_router(operations.router, prefix="/operations", tags=["operations"])
router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
