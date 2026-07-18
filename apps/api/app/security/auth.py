from __future__ import annotations

from enum import Enum
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Role(str, Enum):
    CONTROLLER = "CONTROLLER"
    VIEWER = "VIEWER"


class Principal(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    uid: str
    display_name: str
    role: Role
    auth_mode: str


class AuthenticationError(RuntimeError):
    pass


class AuthService:
    def __init__(
        self,
        mode: str = "disabled",
        project_id: str | None = None,
        token_verifier: Callable[[str], dict[str, Any]] | None = None,
    ) -> None:
        self.mode = mode
        self.project_id = project_id
        self.token_verifier = token_verifier

    def authenticate(self, token: str | None) -> Principal:
        if self.mode == "disabled":
            return Principal(
                uid="local-controller",
                display_name="Local Demo Controller",
                role=Role.CONTROLLER,
                auth_mode=self.mode,
            )
        if not token:
            raise AuthenticationError("Bearer authentication is required")
        if self.mode == "test":
            mapping = {
                "test-controller": Principal(
                    uid="test-controller", display_name="Test Controller", role=Role.CONTROLLER, auth_mode="test"
                ),
                "test-viewer": Principal(
                    uid="test-viewer", display_name="Test Viewer", role=Role.VIEWER, auth_mode="test"
                ),
            }
            principal = mapping.get(token)
            if principal is None:
                raise AuthenticationError("Invalid test authentication token")
            return principal
        return self._verify_firebase(token)

    def _verify_firebase(self, token: str) -> Principal:
        try:
            if self.token_verifier:
                claims = self.token_verifier(token)
                return self._principal_from_claims(claims)
            import firebase_admin
            from firebase_admin import auth, credentials

            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(
                    credentials.ApplicationDefault(),
                    {"projectId": self.project_id},
                )
            claims: dict[str, Any] = auth.verify_id_token(token, check_revoked=True)
        except Exception as error:  # Firebase normalizes several token/transport failures.
            raise AuthenticationError("Firebase ID token verification failed") from error
        return self._principal_from_claims(claims)

    @staticmethod
    def _principal_from_claims(claims: dict[str, Any]) -> Principal:
        role_value = str(claims.get("role", "VIEWER")).upper()
        role = Role.CONTROLLER if role_value == Role.CONTROLLER.value else Role.VIEWER
        return Principal(
            uid=str(claims["uid"]),
            display_name=str(claims.get("name") or claims.get("email") or claims["uid"]),
            role=role,
            auth_mode="firebase",
        )


bearer = HTTPBearer(auto_error=False)


def current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    try:
        return request.app.state.auth_service.authenticate(
            credentials.credentials if credentials else None
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def require_controller(principal: Principal = Depends(current_principal)) -> Principal:
    if principal.role != Role.CONTROLLER:
        raise HTTPException(status_code=403, detail="Controller role is required")
    return principal
