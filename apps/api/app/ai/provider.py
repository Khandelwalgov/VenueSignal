from __future__ import annotations

from typing import Protocol

from app.domain.workflow.models import (
    ImpactAnalysis,
    IncidentMatchCandidate,
    Report,
    ReportExtraction,
    ResponsePlan,
    PlanValidationError,
)
from app.domain.venue.models import Venue


class AIProvider(Protocol):
    name: str

    def extract_report(self, raw_text: str, language: str, venue: Venue) -> ReportExtraction: ...

    def assess_incident_match(
        self, extraction: ReportExtraction, candidate: Report
    ) -> IncidentMatchCandidate: ...

    def propose_plan(
        self,
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        venue: Venue,
    ) -> ResponsePlan: ...

    def repair_plan(
        self,
        original_plan: ResponsePlan,
        validation_errors: list[PlanValidationError],
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        venue: Venue,
    ) -> ResponsePlan: ...

    def explain_reassessment(
        self, old_context_version: int, impact: ImpactAnalysis
    ) -> str: ...


class GeminiNotConfiguredError(RuntimeError):
    pass
