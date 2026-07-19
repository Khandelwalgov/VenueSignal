from __future__ import annotations

from copy import deepcopy

import pytest

from app.ai.gemini import (
    AIProviderMalformedResponse,
    AIProviderQuotaError,
    AIProviderTimeout,
)
from app.ai.local import LocalDemoAIProvider
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.enums import AssetStatus
from app.domain.venue.service import VenueService
from app.domain.workflow.impact import ImpactAnalyzer
from app.domain.workflow.models import (
    ApprovalRequest,
    IncidentCreate,
    PlanAction,
    PlanSource,
    PlanValidity,
    ReportCreate,
)
from app.domain.workflow.plan_validation import PlanValidator
from app.domain.workflow.service import WorkflowService


REPORT = "Lift near Section 214 is stuck again. Two wheelchair users are waiting."


class ScriptedGeminiProvider:
    name = "GEMINI"

    def __init__(self, *, repair_mode: str = "valid", invalid_no_route_plan: bool = False):
        self.local = LocalDemoAIProvider()
        self.repair_mode = repair_mode
        self.invalid_no_route_plan = invalid_no_route_plan
        self.repair_calls = 0

    def extract_report(self, raw_text, language, venue):
        result = self.local.extract_report(raw_text, language, venue)
        result.provider = self.name
        return result

    def assess_incident_match(self, extraction, candidate):
        return self.local.assess_incident_match(extraction, candidate)

    def propose_plan(self, verified_facts, unverified_claims, impact, venue):
        plan = self.local.propose_plan(verified_facts, unverified_claims, impact, venue)
        if self.invalid_no_route_plan and not impact.route_result.found:
            plan.actions.append(
                PlanAction(
                    action_type="STAFF_VERIFIED_ROUTE",
                    title="Staff an invented positive route",
                    assigned_team="VENUE_OPERATIONS",
                    location_id="A_CORRIDOR_W3",
                    rationale="Model ignored the deterministic no-route result.",
                )
            )
            plan.validity = PlanValidity.VALID
        return plan

    def repair_plan(
        self,
        original_plan,
        validation_errors,
        verified_facts,
        unverified_claims,
        impact,
        venue,
    ):
        self.repair_calls += 1
        if self.repair_mode == "timeout":
            raise AIProviderTimeout("bounded repair timed out")
        if self.repair_mode == "quota":
            raise AIProviderQuotaError("quota unavailable")
        if self.repair_mode == "malformed":
            raise AIProviderMalformedResponse("malformed structured output")
        repaired = self.local.propose_plan(verified_facts, unverified_claims, impact, venue)
        if self.repair_mode == "invalid":
            repaired.actions.append(deepcopy(original_plan.actions[-1]))
            repaired.validity = PlanValidity.VALID
        elif self.repair_mode == "stale":
            repaired.context_version -= 1
        return repaired

    def explain_reassessment(self, old_context_version, impact):
        return self.local.explain_reassessment(old_context_version, impact)


def build_workflow(provider: ScriptedGeminiProvider):
    venue = VenueService().load_canonical_venue()
    state = OperationalStateService(venue)
    return WorkflowService(venue, state, RoutingService(venue), provider)


def create_no_route_incident(workflow: WorkflowService):
    workflow.state_service.set_asset_status("A_CORRIDOR_W3", AssetStatus.OUT_OF_SERVICE)
    report = workflow.create_report(ReportCreate(raw_text=REPORT))
    return workflow.create_incident(
        IncidentCreate(report_ids=[report.id], confirmed_asset_id="A_LIFT_2")
    )


def test_valid_gemini_plan_is_exposed_without_repair():
    provider = ScriptedGeminiProvider()
    workflow = build_workflow(provider)
    report = workflow.create_report(ReportCreate(raw_text=REPORT))
    incident = workflow.create_incident(
        IncidentCreate(report_ids=[report.id], confirmed_asset_id="A_LIFT_2")
    )

    assert provider.repair_calls == 0
    assert incident.current_plan.plan_source == PlanSource.GEMINI
    assert incident.plan_recovery_records == []


def test_invalid_route_action_gets_one_valid_repair_for_review():
    provider = ScriptedGeminiProvider(invalid_no_route_plan=True)
    workflow = build_workflow(provider)
    incident = create_no_route_incident(workflow)

    assert provider.repair_calls == 1
    assert incident.current_plan.plan_source == PlanSource.GEMINI_REPAIRED
    assert incident.current_plan.approved_at is None
    assert all(action.action_type != "STAFF_VERIFIED_ROUTE" for action in incident.current_plan.actions)
    assert incident.plan_recovery_records[0].validation_errors[0].code in {
        "NO_VERIFIED_ROUTE",
        "INVALID_NO_ROUTE_VALIDITY",
    }
    assert incident.tasks == []


def test_invalid_initial_and_repaired_plans_use_deterministic_containment():
    provider = ScriptedGeminiProvider(repair_mode="invalid", invalid_no_route_plan=True)
    workflow = build_workflow(provider)
    incident = create_no_route_incident(workflow)

    assert provider.repair_calls == 1
    assert incident.current_plan.plan_source == PlanSource.DETERMINISTIC_CONTAINMENT
    assert incident.plan_recovery_records[0].fallback_used is True
    assert incident.plan_recovery_records[0].repair_validation_errors


@pytest.mark.parametrize(
    ("repair_mode", "error_type"),
    [
        ("timeout", "AIProviderTimeout"),
        ("quota", "AIProviderQuotaError"),
        ("malformed", "AIProviderMalformedResponse"),
    ],
)
def test_repair_failures_fall_back_once(repair_mode: str, error_type: str):
    provider = ScriptedGeminiProvider(repair_mode=repair_mode, invalid_no_route_plan=True)
    workflow = build_workflow(provider)
    incident = create_no_route_incident(workflow)

    assert provider.repair_calls == 1
    assert incident.current_plan.plan_source == PlanSource.DETERMINISTIC_CONTAINMENT
    assert incident.plan_recovery_records[0].repair_error_category == error_type


def test_stale_repair_cannot_bypass_validation():
    provider = ScriptedGeminiProvider(repair_mode="stale", invalid_no_route_plan=True)
    incident = create_no_route_incident(build_workflow(provider))

    assert incident.current_plan.plan_source == PlanSource.DETERMINISTIC_CONTAINMENT
    assert any(
        error.code == "STALE_CONTEXT_VERSION"
        for error in incident.plan_recovery_records[0].repair_validation_errors
    )


def test_no_route_containment_requires_approval_and_never_creates_route_output():
    provider = ScriptedGeminiProvider(repair_mode="invalid", invalid_no_route_plan=True)
    workflow = build_workflow(provider)
    incident = create_no_route_incident(workflow)

    assert incident.tasks == []
    assert incident.communications == []
    assert incident.current_plan.approved_at is None
    assert all(action.action_type != "STAFF_VERIFIED_ROUTE" for action in incident.current_plan.actions)

    approved = workflow.approve_plan(
        incident.id, ApprovalRequest(approved_by="Venue Controller")
    )
    assert approved.tasks
    assert approved.communications == []
    assert approved.current_plan.validity == PlanValidity.AWAITING_VERIFICATION

    repeated = workflow.approve_plan(
        incident.id, ApprovalRequest(approved_by="Venue Controller")
    )
    assert len(repeated.tasks) == len(approved.tasks)
    assert repeated.communications == []


def test_no_route_staffing_action_is_rejected_even_if_storage_is_tampered():
    provider = ScriptedGeminiProvider()
    workflow = build_workflow(provider)
    incident = create_no_route_incident(workflow)
    stored = workflow.get_incident(incident.id)
    stored.current_plan.actions.append(
        PlanAction(
            action_type="STAFF_VERIFIED_ROUTE",
            title="Unsafe route guidance",
            assigned_team="VENUE_OPERATIONS",
            location_id="A_CORRIDOR_W3",
            rationale="Tampered action",
        )
    )
    workflow.repository.save_incident(stored)

    with pytest.raises(ValueError, match="no verified route"):
        workflow.approve_plan(
            incident.id, ApprovalRequest(approved_by="Venue Controller")
        )


def test_model_invented_identifiers_teams_and_actions_are_structured_errors():
    provider = ScriptedGeminiProvider()
    workflow = build_workflow(provider)
    workflow.state_service.set_asset_status("A_CORRIDOR_W3", AssetStatus.OUT_OF_SERVICE)
    impact = ImpactAnalyzer(
        workflow.venue, workflow.state_service, workflow.routing_service
    ).analyze("A_LIFT_2")
    plan = provider.local.propose_plan([], [], impact, workflow.venue)
    plan.actions.extend(
        [
            PlanAction(
                action_type="INVENTED_ACTION",
                title="Invent an action",
                assigned_team="INVENTED_TEAM",
                location_id="INVENTED_ASSET",
                rationale="Hostile model output",
            ),
            PlanAction(
                action_type="STAFF_VERIFIED_ROUTE",
                title="Invent a route",
                assigned_team="VENUE_OPERATIONS",
                location_id="ROUTE-FAKE",
                rationale="Hostile model output",
            ),
        ]
    )

    codes = {
        error.code
        for error in PlanValidator(
            workflow.venue, workflow.state_service
        ).validate(plan, impact)
    }
    assert {"DISALLOWED_ACTION_TYPE", "UNKNOWN_TEAM", "UNKNOWN_LOCATION", "NO_VERIFIED_ROUTE"} <= codes


def test_plan_provider_outage_uses_approval_gated_deterministic_containment():
    class PlanUnavailableProvider(ScriptedGeminiProvider):
        def propose_plan(self, *_args, **_kwargs):
            raise AIProviderTimeout("plan generation timed out")

    provider = PlanUnavailableProvider()
    workflow = build_workflow(provider)
    report = workflow.create_report(ReportCreate(raw_text=REPORT))
    incident = workflow.create_incident(
        IncidentCreate(report_ids=[report.id], confirmed_asset_id="A_LIFT_2")
    )

    assert incident.current_plan.plan_source == PlanSource.DETERMINISTIC_CONTAINMENT
    assert incident.current_plan.approved_at is None
    assert incident.tasks == []
    assert incident.communications == []
    assert incident.plan_recovery_records[0].original_plan is None
    assert incident.plan_recovery_records[0].repair_error_category == "AIProviderTimeout"
