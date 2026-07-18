import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.ai.gemini import AIProviderTimeout
from app.main import create_app
from app.security.auth import AuthService, AuthenticationError, Role


def test_production_requires_firebase_authentication():
    with pytest.raises(ValueError, match="requires AUTH_MODE=firebase"):
        Settings(environment="production", auth_mode="disabled").validate()


def test_production_rejects_demo_reset_even_when_explicitly_enabled():
    with pytest.raises(ValueError, match="ALLOW_DEMO_RESET=false"):
        Settings(
            environment="production",
            auth_mode="firebase",
            firebase_project_id="project",
            persistence_backend="firestore",
            cors_allowed_origins=("https://ops.example.com",),
            allow_demo_reset=True,
        ).validate()


def test_production_requires_durable_persistence_and_non_loopback_cors():
    with pytest.raises(ValueError, match="PERSISTENCE_BACKEND=firestore"):
        Settings(
            environment="production", auth_mode="firebase", firebase_project_id="project",
            cors_allowed_origins=("https://ops.example.com",),
        ).validate()
    with pytest.raises(ValueError, match="loopback"):
        Settings(
            environment="production", auth_mode="firebase", firebase_project_id="project",
            persistence_backend="firestore",
        ).validate()


def test_explicit_cors_allow_list_is_required():
    with pytest.raises(ValueError, match="explicit"):
        Settings(cors_allowed_origins=("*",)).validate()


def test_test_authentication_enforces_controller_and_viewer_roles():
    settings = Settings(auth_mode="test")
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/venues").status_code == 401
        viewer_headers = {"Authorization": "Bearer test-viewer"}
        controller_headers = {"Authorization": "Bearer test-controller"}
        assert client.get("/api/venues", headers=viewer_headers).status_code == 200
        assert client.post(
            "/api/workflow/reports",
            headers=viewer_headers,
            json={"rawText": "Lift L2 is stuck"},
        ).status_code == 403
        created = client.post(
            "/api/workflow/reports",
            headers=controller_headers,
            json={"rawText": "Lift L2 is stuck"},
        )
        assert created.status_code == 200
        identity = client.get("/api/auth/me", headers=viewer_headers).json()
        assert identity == {
            "uid": "test-viewer",
            "displayName": "Test Viewer",
            "role": "VIEWER",
            "authMode": "test",
        }


def test_security_headers_request_id_and_body_limit():
    settings = Settings(max_request_bytes=100)
    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/health", headers={"X-Request-ID": "evaluation-123"})
        assert response.headers["x-request-id"] == "evaluation-123"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cache-control"] == "no-store"
        oversized = client.post(
            "/api/workflow/reports",
            content=b"x" * 101,
            headers={"Content-Type": "application/json"},
        )
        assert oversized.status_code == 413
        assert oversized.headers["x-content-type-options"] == "nosniff"
        dishonest_length = client.post(
            "/api/workflow/reports",
            content=b"x" * 101,
            headers={"Content-Type": "application/json", "Content-Length": "1"},
        )
        assert dishonest_length.status_code == 413
        invalid_length = client.get("/api/venues", headers={"Content-Length": "-1"})
        assert invalid_length.status_code == 400


def test_rate_limit_returns_retry_after():
    settings = Settings(rate_limit_requests=2, rate_limit_window_seconds=60)
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/api/venues").status_code == 200
        assert client.get("/api/venues").status_code == 200
        limited = client.get("/api/venues")
        assert limited.status_code == 429
        assert limited.headers["retry-after"] == "60"


def test_demo_reset_can_be_disabled_independently_of_role():
    settings = Settings(allow_demo_reset=False)
    with TestClient(create_app(settings=settings)) as client:
        response = client.post("/api/operations/reset")
        assert response.status_code == 403
        assert response.json()["detail"] == "Demo reset is disabled in this environment"


def test_firebase_claims_are_server_verified_and_default_to_viewer():
    controller = AuthService(
        "firebase",
        "project",
        token_verifier=lambda token: {"uid": token, "name": "Ops Lead", "role": "CONTROLLER"},
    ).authenticate("verified-user")
    assert controller.uid == "verified-user"
    assert controller.role == Role.CONTROLLER

    viewer = AuthService(
        "firebase", "project", token_verifier=lambda _token: {"uid": "viewer"}
    ).authenticate("verified-viewer")
    assert viewer.role == Role.VIEWER

    def reject(_token):
        raise ValueError("bad signature")

    with pytest.raises(AuthenticationError, match="verification failed"):
        AuthService("firebase", "project", token_verifier=reject).authenticate("invalid")


def test_initial_ai_failure_is_sanitized_and_changes_no_workflow_state():
    class UnavailableProvider:
        name = "GEMINI"

        def extract_report(self, *_args, **_kwargs):
            raise AIProviderTimeout("internal upstream detail")

    with TestClient(create_app()) as client:
        client.app.state.workflow_service.ai_provider = UnavailableProvider()
        response = client.post(
            "/api/workflow/reports", json={"rawText": "Lift L2 is stuck"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == (
            "AI advisory service is temporarily unavailable; no workflow state was changed"
        )
        assert "internal upstream detail" not in response.text
        assert client.get("/api/workflow/reports").json() == []
