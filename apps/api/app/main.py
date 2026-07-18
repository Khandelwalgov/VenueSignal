from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.ai import GeminiProvider, LocalDemoAIProvider
from app.ai.gemini import AIProviderError
from app.config import Settings
from app.domain.operations.repository import (
    FirestoreOperationalStateRepository,
    InMemoryOperationalStateRepository,
    SQLiteOperationalStateRepository,
)
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.service import VenueService
from app.domain.workflow.service import WorkflowService
from app.domain.workflow.repository import (
    FirestoreWorkflowRepository,
    InMemoryWorkflowRepository,
    SQLiteWorkflowRepository,
)
from app.security.auth import AuthService
from app.security.middleware import SecurityMiddleware


logger = logging.getLogger("venuesignal")


def create_app(
    venue_service: VenueService | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    service = venue_service or VenueService()
    configuration = settings or Settings.from_environment()
    configuration.validate()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        service.ensure_loaded()
        application.state.venue_service = service
        venue = service.get_venue()
        if configuration.persistence_backend == "sqlite":
            state_repository = SQLiteOperationalStateRepository(configuration.sqlite_path)
            workflow_repository = SQLiteWorkflowRepository(configuration.sqlite_path)
        elif configuration.persistence_backend == "firestore":
            from google.cloud import firestore

            firestore_client = firestore.Client(project=configuration.firebase_project_id)
            state_repository = FirestoreOperationalStateRepository(firestore_client)
            workflow_repository = FirestoreWorkflowRepository(firestore_client)
        else:
            state_repository = InMemoryOperationalStateRepository()
            workflow_repository = InMemoryWorkflowRepository()
        application.state.operational_state_service = OperationalStateService(
            venue, state_repository
        )
        application.state.routing_service = RoutingService(venue)
        application.state.ai_provider = (
            GeminiProvider(
                configuration.gemini_api_key,
                model=configuration.gemini_model,
            )
            if configuration.ai_provider == "gemini"
            else LocalDemoAIProvider()
        )
        application.state.workflow_service = WorkflowService(
            venue,
            application.state.operational_state_service,
            application.state.routing_service,
            application.state.ai_provider,
            workflow_repository,
        )
        application.state.auth_service = AuthService(
            configuration.auth_mode, configuration.firebase_project_id
        )
        application.state.settings = configuration
        validation = service.get_validation_status()
        for warning in validation.warnings:
            logger.warning("Venue graph warning %s: %s", warning.code, warning.message)
        yield

    application = FastAPI(
        title="VenueSignal API",
        description=(
            "Deterministic venue graph, accessibility reachability, and operations "
            "intelligence APIs for the synthetic Unity Stadium prototype."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if configuration.environment == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if configuration.environment == "production" else "/openapi.json",
    )
    application.add_middleware(SecurityMiddleware, settings=configuration)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(configuration.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @application.exception_handler(AIProviderError)
    async def ai_provider_failure(_request: Request, _error: AIProviderError):
        return JSONResponse(
            status_code=503,
            content={"detail": "AI advisory service is temporarily unavailable; no workflow state was changed"},
        )

    @application.get("/health", tags=["Health"], summary="Process health")
    def health_check():
        return {"status": "ok", "service": "venuesignal-api", "version": "1.0.0"}

    @application.get("/ready", tags=["Health"], summary="Canonical venue readiness")
    def readiness(request: Request):
        validation = request.app.state.venue_service.get_validation_status()
        return {
            "status": "ready" if validation.valid else "not_ready",
            "venueGraphValid": validation.valid,
            "persistenceBackend": configuration.persistence_backend,
            "aiProvider": application.state.ai_provider.name,
            "authMode": configuration.auth_mode,
        }

    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
