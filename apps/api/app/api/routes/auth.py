from fastapi import APIRouter, Depends

from app.security.auth import Principal, current_principal


router = APIRouter()


@router.get("/me", response_model=Principal, summary="Return the server-verified principal and role")
def me(principal: Principal = Depends(current_principal)) -> Principal:
    return principal
