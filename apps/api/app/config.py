from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


def _boolean(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    auth_mode: str = "disabled"
    persistence_backend: str = "memory"
    sqlite_path: Path = Path("/tmp/venuesignal.db")
    ai_provider: str = "local"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    firebase_project_id: str | None = None
    cors_allowed_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
    rate_limit_requests: int = 180
    rate_limit_window_seconds: int = 60
    max_request_bytes: int = 300_000
    trust_proxy_headers: bool = False
    allow_demo_reset: bool | None = None

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.getenv("ENVIRONMENT", "development").lower()
        origins = tuple(
            item.strip()
            for item in os.getenv(
                "CORS_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if item.strip()
        )
        settings = cls(
            environment=environment,
            auth_mode=os.getenv("AUTH_MODE", "disabled").lower(),
            persistence_backend=os.getenv("PERSISTENCE_BACKEND", "memory").lower(),
            sqlite_path=Path(os.getenv("SQLITE_PATH", "/tmp/venuesignal.db")),
            ai_provider=os.getenv("AI_PROVIDER", "local").lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"),
            cors_allowed_origins=origins,
            rate_limit_requests=int(os.getenv("RATE_LIMIT_REQUESTS", "180")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            max_request_bytes=int(os.getenv("MAX_REQUEST_BYTES", "300000")),
            trust_proxy_headers=_boolean("TRUST_PROXY_HEADERS"),
            allow_demo_reset=_boolean("ALLOW_DEMO_RESET", environment != "production"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment == "production" and self.auth_mode != "firebase":
            raise ValueError("Production requires AUTH_MODE=firebase")
        if self.auth_mode not in {"disabled", "test", "firebase"}:
            raise ValueError(f"Unsupported AUTH_MODE: {self.auth_mode}")
        if self.persistence_backend not in {"memory", "sqlite", "firestore"}:
            raise ValueError(f"Unsupported PERSISTENCE_BACKEND: {self.persistence_backend}")
        if self.environment == "production" and self.persistence_backend != "firestore":
            raise ValueError("Production requires PERSISTENCE_BACKEND=firestore")
        if self.environment == "production" and self.demo_reset_enabled:
            raise ValueError("Production requires ALLOW_DEMO_RESET=false")
        if self.ai_provider not in {"local", "gemini"}:
            raise ValueError(f"Unsupported AI_PROVIDER: {self.ai_provider}")
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
        if self.auth_mode == "firebase" and not self.firebase_project_id:
            raise ValueError("FIREBASE_PROJECT_ID is required when AUTH_MODE=firebase")
        if not self.cors_allowed_origins or "*" in self.cors_allowed_origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must be an explicit non-empty allow-list")
        for origin in self.cors_allowed_origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError(f"Invalid CORS origin: {origin}")
            if self.environment == "production" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Production CORS origins cannot be loopback addresses")
        if self.rate_limit_requests < 1 or self.rate_limit_window_seconds < 1:
            raise ValueError("Rate-limit settings must be positive")
        if self.max_request_bytes < 1:
            raise ValueError("MAX_REQUEST_BYTES must be positive")

    @property
    def demo_reset_enabled(self) -> bool:
        return self.allow_demo_reset if self.allow_demo_reset is not None else self.environment != "production"
