from types import SimpleNamespace

import pytest

from app.ai.gemini import (
    AIProviderMalformedResponse,
    AIProviderQuotaError,
    AIProviderTimeout,
    GeminiProvider,
)
from app.ai.local import LocalDemoAIProvider
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.enums import AssetStatus
from app.domain.venue.service import VenueService
from app.domain.workflow.impact import ImpactAnalyzer
from app.domain.workflow.models import PlanAction, PlanSource, PlanValidationError, ReportExtraction


class Models:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def extraction():
    return ReportExtraction(
        category="FACILITY_OUTAGE",
        summary="Lift report",
        candidateAssetIds=["A_LIFT_2"],
        urgencySuggestion="HIGH",
        confidence=0.8,
        unverifiedClaims=["Lift L2 is stuck"],
        provider="MODEL",
    )


def test_gemini_uses_structured_schema_and_authoritative_context():
    models = Models([SimpleNamespace(parsed=extraction(), text=None)])
    provider = GeminiProvider(None, client=SimpleNamespace(models=models))
    result = provider.extract_report("Lift L2 is stuck", "en", VenueService().load_canonical_venue())
    assert result.provider == "GEMINI"
    assert models.calls[0]["config"]["response_mime_type"] == "application/json"
    assert "Authoritative assets" in models.calls[0]["contents"]
    assert "untrusted operational evidence" in models.calls[0]["contents"]


def test_gemini_rejects_malformed_structured_output():
    models = Models([SimpleNamespace(parsed=None, text="not-json")] * 3)
    provider = GeminiProvider(None, client=SimpleNamespace(models=models))
    with pytest.raises(AIProviderMalformedResponse):
        provider.extract_report("Lift L2 is stuck", "en", VenueService().load_canonical_venue())
    assert len(models.calls) == 3


def test_gemini_retries_malformed_structured_output(monkeypatch):
    monkeypatch.setattr("app.ai.gemini.time.sleep", lambda _seconds: None)
    models = Models(
        [
            SimpleNamespace(parsed=None, text="not-json"),
            SimpleNamespace(parsed=extraction(), text=None),
        ]
    )
    provider = GeminiProvider(None, client=SimpleNamespace(models=models))

    result = provider.extract_report(
        "Lift L2 is stuck", "en", VenueService().load_canonical_venue()
    )

    assert result.provider == "GEMINI"
    assert len(models.calls) == 2


def test_gemini_classifies_quota_and_retries_timeouts(monkeypatch):
    monkeypatch.setattr("app.ai.gemini.time.sleep", lambda _seconds: None)
    quota_models = Models([RuntimeError("429 quota")] * 3)
    quota = GeminiProvider(None, client=SimpleNamespace(models=quota_models))
    with pytest.raises(AIProviderQuotaError):
        quota.extract_report("Lift L2 is stuck", "en", VenueService().load_canonical_venue())
    assert len(quota_models.calls) == 3

    timeout = GeminiProvider(
        None,
        client=SimpleNamespace(models=Models([TimeoutError(), TimeoutError(), TimeoutError()])),
    )
    with pytest.raises(AIProviderTimeout):
        timeout.extract_report("Lift L2 is stuck", "en", VenueService().load_canonical_venue())


def test_gemini_retries_transient_quota_exhaustion(monkeypatch):
    monkeypatch.setattr("app.ai.gemini.time.sleep", lambda _seconds: None)
    models = Models(
        [RuntimeError("429 resource exhausted"), SimpleNamespace(parsed=extraction(), text=None)]
    )
    provider = GeminiProvider(None, client=SimpleNamespace(models=models))

    result = provider.extract_report(
        "Lift L2 is stuck", "en", VenueService().load_canonical_venue()
    )

    assert result.provider == "GEMINI"
    assert len(models.calls) == 2


def test_gemini_repair_prompt_is_authoritative_and_has_one_model_attempt():
    venue = VenueService().load_canonical_venue()
    state = OperationalStateService(venue)
    state.set_asset_status("A_LIFT_2", AssetStatus.OUT_OF_SERVICE)
    state.set_asset_status("A_CORRIDOR_W3", AssetStatus.OUT_OF_SERVICE)
    impact = ImpactAnalyzer(venue, state, RoutingService(venue)).analyze("A_LIFT_2")
    local = LocalDemoAIProvider()
    valid_repair = local.propose_plan([], [], impact, venue)
    invalid = valid_repair.model_copy(deep=True)
    invalid.actions.append(
        PlanAction(
            action_type="STAFF_VERIFIED_ROUTE",
            title="Unsafe route action",
            assigned_team="VENUE_OPERATIONS",
            location_id="A_CORRIDOR_W3",
            rationale="Invalid model output",
        )
    )
    errors = [
        PlanValidationError(
            code="NO_VERIFIED_ROUTE",
            message="A route action cannot be approved when no verified route exists",
            action_index=len(invalid.actions) - 1,
        )
    ]
    models = Models([SimpleNamespace(parsed=valid_repair, text=None)])
    provider = GeminiProvider(None, client=SimpleNamespace(models=models))

    repaired = provider.repair_plan(invalid, errors, [], [], impact, venue)

    assert repaired.plan_source == PlanSource.GEMINI_REPAIRED
    assert len(models.calls) == 1
    prompt = models.calls[0]["contents"]
    assert "Current contextVersion" in prompt
    assert "Exact validation errors" in prompt
    assert "STAFF_VERIFIED_ROUTE and any positive route-guidance action are prohibited" in prompt
    assert "Authoritative nodes" in prompt
