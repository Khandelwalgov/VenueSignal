from __future__ import annotations

import re
from uuid import uuid4

from app.domain.operations.routing import NO_STEP_FREE_ROUTE
from app.domain.workflow.models import (
    ImpactAnalysis,
    IncidentMatchCandidate,
    PlanAction,
    PlanSource,
    PlanValidationError,
    PlanValidity,
    ReportExtraction,
    Report,
    ResponsePlan,
)
from app.domain.venue.models import Venue


INSTRUCTION_PATTERNS = re.compile(
    r"(ignore (all |the )?(previous|system) instructions|system prompt|developer message|act as)",
    re.IGNORECASE,
)


class LocalDemoAIProvider:
    """Deterministic offline provider used only for tests and credential-free demos."""

    name = "LOCAL_DEMO_PROVIDER"

    def extract_report(
        self, raw_text: str, language: str, venue: Venue
    ) -> ReportExtraction:
        text = raw_text.strip()
        lower = text.lower()
        injection = bool(INSTRUCTION_PATTERNS.search(text))
        candidate_assets: list[str] = []
        candidate_zones: list[str] = []
        affected_groups: list[str] = []
        symptoms: list[str] = []

        if "lift" in lower or "section 214" in lower:
            candidate_assets.append("A_LIFT_2")
            candidate_zones.extend(["Z_L2_W_CONCOURSE", "Z_SEC_209_218"])
            symptoms.append("lift interruption")
        if "corridor w3" in lower or "accessible path" in lower or "cleaning spill" in lower:
            candidate_assets.append("A_CORRIDOR_W3")
            candidate_zones.append("Z_L2_W_CONCOURSE")
            symptoms.append("step-free path obstruction")
        if "scanner" in lower or "north gate" in lower:
            candidate_assets.append("A_SCANNER_N2")
            candidate_zones.append("Z_N_SEC")
            symptoms.append("scanner throughput interruption")
        if "west stairs" in lower:
            candidate_zones.append("Z_L2_W_CONCOURSE")
        if "wheelchair" in lower or "accessible" in lower:
            affected_groups.append("WHEELCHAIR_OR_STEP_FREE_USERS")
        if "crowd" in lower or "buildup" in lower:
            symptoms.append("crowd buildup")

        category = (
            "CROWD_CONGESTION"
            if "crowd" in lower
            else "ACCESS_OBSTRUCTION"
            if "blocked" in lower or "closed" in lower or "spill" in lower
            else "FACILITY_OUTAGE"
        )
        safe_summary = (
            "Untrusted instruction-like text detected; retained only as report evidence."
            if injection
            else text[:220]
        )
        return ReportExtraction(
            category=category,
            summary=safe_summary,
            candidate_zone_ids=sorted(set(candidate_zones)),
            candidate_asset_ids=sorted(set(candidate_assets)),
            affected_groups=affected_groups,
            observed_symptoms=sorted(set(symptoms)),
            urgency_suggestion="HIGH" if affected_groups or "closed" in lower else "MEDIUM",
            confidence=0.88 if candidate_assets else 0.45,
            unverified_claims=[text],
            missing_information=["Controller verification of the reported facility state"],
            clarification_questions=["Can venue staff confirm the asset status at the reported location?"],
            untrusted_instruction_detected=injection,
            provider=self.name,
        )

    def assess_incident_match(
        self, extraction: ReportExtraction, candidate: Report
    ) -> IncidentMatchCandidate:
        shared_assets = sorted(
            set(extraction.candidate_asset_ids).intersection(candidate.extraction.candidate_asset_ids)
        )
        shared_zones = sorted(
            set(extraction.candidate_zone_ids).intersection(candidate.extraction.candidate_zone_ids)
        )
        score = min(1.0, 0.62 * bool(shared_assets) + 0.28 * bool(shared_zones) + 0.1)
        recommendation = "LINK" if score >= 0.75 else "HUMAN_REVIEW_REQUIRED"
        return IncidentMatchCandidate(
            report_id=candidate.id,
            score=score,
            recommendation=recommendation,
            reasons=[
                *(f"Shared asset {asset_id}" for asset_id in shared_assets),
                *(f"Shared zone {zone_id}" for zone_id in shared_zones),
            ] or ["Category-compatible report requires controller comparison"],
            meaningful_differences=(
                ["Reports describe different symptoms or downstream consequences"]
                if extraction.observed_symptoms != candidate.extraction.observed_symptoms
                else []
            ),
        )

    def propose_plan(
        self,
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        venue: Venue,
    ) -> ResponsePlan:
        if impact.route_result.found:
            actions = [
                PlanAction(
                    action_type="INSPECT_ASSET",
                    title="Dispatch maintenance to inspect Lift L2",
                    assigned_team="MAINTENANCE",
                    location_id="A_LIFT_2",
                    rationale="The controller confirmed the accessibility-critical lift outage.",
                ),
                PlanAction(
                    action_type="DISPATCH_ACCESSIBILITY_TEAM",
                    title="Assist waiting step-free users",
                    assigned_team="ACCESSIBILITY_TEAM",
                    location_id="N_L2_W3",
                    rationale="Affected users require supported movement while the normal route is unavailable.",
                ),
                PlanAction(
                    action_type="STAFF_VERIFIED_ROUTE",
                    title="Staff the verified Corridor W3 fallback",
                    assigned_team="VENUE_OPERATIONS",
                    location_id="A_CORRIDOR_W3",
                    rationale="Deterministic routing verified W3 under the current context.",
                ),
            ]
            objective = "Maintain verified step-free access while Lift L2 is unavailable."
            validity = PlanValidity.VALID
        else:
            actions = [
                PlanAction(
                    action_type="ESTABLISH_WAITING_POINT",
                    title="Establish a staffed accessible waiting point",
                    assigned_team="ACCESSIBILITY_TEAM",
                    location_id="N_L2_WAIT_2",
                    rationale=NO_STEP_FREE_ROUTE,
                ),
                PlanAction(
                    action_type="VERIFY_ROUTE_STATUS",
                    title="Verify Lift L2 and Corridor W3 conditions",
                    assigned_team="VENUE_OPERATIONS",
                    location_id="Z_L2_W_CONCOURSE",
                    rationale="Do not publish unverified route guidance.",
                ),
            ]
            objective = "Contain affected spectators safely until a route is verified."
            validity = PlanValidity.AWAITING_VERIFICATION

        return ResponsePlan(
            id=f"PLAN-{uuid4().hex[:8].upper()}",
            situation_assessment=" ".join(verified_facts),
            operational_objective=objective,
            actions=actions,
            risks=["Conditions may change before tasks are completed"],
            assumptions=[
                "The deterministic route result matches the current operational context version"
            ],
            missing_information=["Estimated repair time for Lift L2"],
            confidence=0.86 if impact.route_result.found else 0.72,
            reassessment_triggers=[
                "Lift L2 status changes",
                "Corridor W3 status changes",
                "Crowd constraints invalidate the route",
            ],
            context_version=impact.context_version,
            validity=validity,
            plan_source=PlanSource.LOCAL_DETERMINISTIC,
        )

    def repair_plan(
        self,
        original_plan: ResponsePlan,
        validation_errors: list[PlanValidationError],
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        venue: Venue,
    ) -> ResponsePlan:
        """Local mode is deterministic; regeneration cannot repeat an invalid action."""
        return self.propose_plan(verified_facts, unverified_claims, impact, venue)

    def explain_reassessment(
        self, old_context_version: int, impact: ImpactAnalysis
    ) -> str:
        if not impact.route_result.found:
            return (
                f"Context changed from v{old_context_version} to v{impact.context_version}. "
                "The previously verified fallback now depends on an unavailable Corridor W3, "
                "so deterministic validation found no safe step-free route. The approved plan "
                "must not be silently rewritten and requires controller review."
            )
        return (
            f"Context changed from v{old_context_version} to v{impact.context_version}; "
            "the step-free route remains deterministically valid."
        )
