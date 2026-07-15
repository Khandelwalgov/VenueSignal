from __future__ import annotations

from typing import Protocol

from app.domain.workflow.models import (
    ImpactAnalysis,
    ReportExtraction,
    ResponsePlan,
)
from app.domain.venue.models import Venue


class AIProvider(Protocol):
    name: str

    def extract_report(self, raw_text: str, language: str, venue: Venue) -> ReportExtraction: ...

    def propose_plan(
        self,
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


class GeminiProvider:
    """Credential-gated boundary; runtime integration is intentionally not faked."""

    name = "GEMINI"

    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise GeminiNotConfiguredError(
                "GEMINI_API_KEY is not configured; use LocalDemoAIProvider for local demo and tests."
            )
