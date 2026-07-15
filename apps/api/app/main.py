from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.ai.local import LocalDemoAIProvider
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.service import VenueService
from app.domain.workflow.service import WorkflowService


logger = logging.getLogger("venuesignal")


def create_app(venue_service: VenueService | None = None) -> FastAPI:
    service = venue_service or VenueService()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        service.ensure_loaded()
        application.state.venue_service = service
        venue = service.get_venue()
        application.state.operational_state_service = OperationalStateService(venue)
        application.state.routing_service = RoutingService(venue)
        application.state.ai_provider = LocalDemoAIProvider()
        application.state.workflow_service = WorkflowService(
            venue,
            application.state.operational_state_service,
            application.state.routing_service,
            application.state.ai_provider,
        )
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
        version="0.2.0",
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.get("/health", tags=["Health"], summary="Process health")
    def health_check():
        return {"status": "ok", "service": "venuesignal-api", "version": "0.2.0"}

    @application.get("/ready", tags=["Health"], summary="Canonical venue readiness")
    def readiness(request: Request):
        validation = request.app.state.venue_service.get_validation_status()
        return {
            "status": "ready" if validation.valid else "not_ready",
            "venueGraphValid": validation.valid,
        }

    application.include_router(api_router, prefix="/api")
    return application


app = create_app()
