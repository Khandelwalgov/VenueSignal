from fastapi import APIRouter, Depends
from app.api.routes import auth, operations, venues, workflow
from app.security.auth import current_principal

router = APIRouter(dependencies=[Depends(current_principal)])
router.include_router(venues.router, prefix="/venues", tags=["venues"])
router.include_router(operations.router, prefix="/operations", tags=["operations"])
router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
