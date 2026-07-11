from fastapi import APIRouter
from app.api.routes import venues

router = APIRouter()
router.include_router(venues.router, prefix="/venues", tags=["venues"])
