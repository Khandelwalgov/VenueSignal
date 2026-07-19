from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.ai.gemini import AIProviderQuotaError
from app.ai.provider import AIProvider
from app.domain.operations.models import RouteConstraints, RouteQuery
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.enums import AssetStatus
from app.domain.venue.models import Venue
from app.domain.workflow.models import (
    ApprovalRequest,
    AuditEvent,
    Communication,
    CommunicationStatus,
    CommunicationUpdate,
    ImpactAnalysis,
    Incident,
    IncidentCreate,
    IncidentStatus,
    IncidentStatusUpdate,
    PlanAction,
    PlanRecoveryRecord,
    PlanSource,
    PlanValidationError,
    PlanValidity,
    Reassessment,
    Report,
    ReportCreate,
    ResponsePlan,
    Task,
    TaskStatus,
    TaskUpdate,
)
from app.domain.workflow.repository import InMemoryWorkflowRepository, WorkflowRepository


ALLOWED_ACTION_TYPES = {
    "INSPECT_ASSET",
    "DISPATCH_ACCESSIBILITY_TEAM",
    "STAFF_VERIFIED_ROUTE",
    "ESTABLISH_WAITING_POINT",
    "VERIFY_ROUTE_STATUS",
}
KNOWN_TEAMS = {"MAINTENANCE", "ACCESSIBILITY_TEAM", "VENUE_OPERATIONS"}
TASK_TRANSITIONS = {
    TaskStatus.CREATED: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.ASSIGNED: {TaskStatus.ACKNOWLEDGED, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.ACKNOWLEDGED: {TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {TaskStatus.BLOCKED, TaskStatus.COMPLETED, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.ASSIGNED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.CANCELLED: set(),
}
COMMUNICATION_TRANSITIONS = {
    CommunicationStatus.DRAFT: {CommunicationStatus.UNDER_REVIEW, CommunicationStatus.REJECTED},
    CommunicationStatus.UNDER_REVIEW: {CommunicationStatus.APPROVED, CommunicationStatus.REJECTED},
    CommunicationStatus.APPROVED: {CommunicationStatus.PUBLISHED_SIMULATED, CommunicationStatus.SUPERSEDED},
    CommunicationStatus.PUBLISHED_SIMULATED: {CommunicationStatus.SUPERSEDED},
    CommunicationStatus.SUPERSEDED: set(),
    CommunicationStatus.REJECTED: set(),
}
UNTRUSTED_INSTRUCTION_PATTERN = re.compile(
    r"(ignore (all |the )?(previous|system|venue|safety) (instructions|constraints)|"
    r"system prompt|developer message|override (the )?(route|validator|constraints)|act as)",
    re.IGNORECASE,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowService:
    def __init__(
        self,
        venue: Venue,
        state_service: OperationalStateService,
        routing_service: RoutingService,
        ai_provider: AIProvider,
        repository: WorkflowRepository | None = None,
        guided_demo_fallback_provider: AIProvider | None = None,
    ) -> None:
        self.venue = venue
        self.state_service = state_service
        self.routing_service = routing_service
        self.ai_provider = ai_provider
        self.repository = repository or InMemoryWorkflowRepository()
        self.guided_demo_fallback_provider = guided_demo_fallback_provider
        self._lock = RLock()

    def list_reports(self) -> list[Report]:
        return self.repository.list_reports()

    @staticmethod
    def report_fingerprint(request: ReportCreate) -> str:
        if request.idempotency_key:
            material = f"key:{request.idempotency_key}"
        else:
            material = "|".join(
                (
                    " ".join(request.raw_text.lower().split()),
                    request.language.lower(),
                    request.source.lower(),
                )
            )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def create_report(self, request: ReportCreate) -> Report:
        with self._lock:
            return self._create_report(request)

    def _create_report(self, request: ReportCreate) -> Report:
        fingerprint = self.report_fingerprint(request)
        existing = self.repository.find_report_by_fingerprint(fingerprint)
        if existing:
            return existing
        provider = self.ai_provider
        fallback_used = False
        try:
            extraction = provider.extract_report(request.raw_text, request.language, self.venue)
        except AIProviderQuotaError:
            if request.source != "GUIDED_DEMO" or self.guided_demo_fallback_provider is None:
                raise
            provider = self.guided_demo_fallback_provider
            extraction = provider.extract_report(request.raw_text, request.language, self.venue)
            fallback_used = True
        valid_asset_ids = {asset.id for asset in self.venue.assets}
        valid_zone_ids = {zone.id for zone in self.venue.zones}
        extraction.candidate_asset_ids = [
            asset_id for asset_id in extraction.candidate_asset_ids if asset_id in valid_asset_ids
        ]
        extraction.candidate_zone_ids = [
            zone_id for zone_id in extraction.candidate_zone_ids if zone_id in valid_zone_ids
        ]
        if UNTRUSTED_INSTRUCTION_PATTERN.search(request.raw_text):
            extraction.untrusted_instruction_detected = True
        candidates = []
        stored_reports = self.repository.list_reports()
        if stored_reports:
            extraction_assets = set(extraction.candidate_asset_ids)
            extraction_zones = set(extraction.candidate_zone_ids)

            def relevance(report: Report) -> tuple[int, datetime]:
                shared_assets = extraction_assets.intersection(
                    report.extraction.candidate_asset_ids
                )
                shared_zones = extraction_zones.intersection(
                    report.extraction.candidate_zone_ids
                )
                score = (
                    2 * bool(shared_assets)
                    + bool(shared_zones)
                    + (report.extraction.category == extraction.category)
                )
                return score, report.created_at

            # Relationship reasoning is advisory and quota-sensitive. Select the single
            # strongest recent candidate deterministically, then ask the configured AI
            # provider for the human-reviewable comparison. This prevents a populated
            # Firestore project from causing one model call per historical report.
            candidate_report = max(stored_reports, key=relevance)
            try:
                candidates.append(provider.assess_incident_match(extraction, candidate_report))
            except AIProviderQuotaError:
                if request.source != "GUIDED_DEMO" or self.guided_demo_fallback_provider is None:
                    raise
                candidates.append(
                    self.guided_demo_fallback_provider.assess_incident_match(
                        extraction, candidate_report
                    )
                )
                fallback_used = True
        report = Report(
            id=f"RPT-{fingerprint[:12].upper()}",
            raw_text=request.raw_text,
            language=request.language,
            source=request.source,
            synthetic=request.synthetic,
            extraction=extraction,
            related_report_ids=[candidate.report_id for candidate in candidates],
            match_candidates=sorted(candidates, key=lambda item: item.score, reverse=True),
            fingerprint=fingerprint,
            provenance=(
                "GUIDED_DEMO_QUOTA_FALLBACK"
                if fallback_used
                else "GUIDED_DEMO"
                if request.source == "GUIDED_DEMO"
                else "EVALUATOR_UPLOAD"
                if "UPLOAD" in request.source
                else "MANUAL_ENTRY"
            ),
            created_at=_now(),
        )
        self.repository.save_report(report)
        return report.model_copy(deep=True)

    def list_incidents(self) -> list[Incident]:
        return self.repository.list_incidents()

    def get_incident(self, incident_id: str) -> Incident:
        incident = self.repository.get_incident(incident_id)
        if incident is None:
            raise KeyError(f"Unknown incident: {incident_id}")
        return incident

    def _audit(self, incident: Incident, event_type: str, summary: str, actor: str) -> None:
        incident.audit_events.append(
            AuditEvent(
                id=f"AUD-{uuid4().hex[:8].upper()}",
                event_type=event_type,
                summary=summary,
                context_version=self.state_service.snapshot().context_version,
                occurred_at=_now(),
                actor=actor,
            )
        )

    def _analyse_impact(self, asset_id: str) -> ImpactAnalysis:
        asset = next(asset for asset in self.venue.assets if asset.id == asset_id)
        state = self.state_service.snapshot()
        route = self.routing_service.find_route(
            RouteQuery(
                start_node_id="N_L0_W_ACC_ENT",
                destination_node_id="N_L2_SEC_209_218",
                constraints=RouteConstraints(step_free=True),
            ),
            state,
        )
        served_nodes = set(asset.served_node_ids)
        served_edges = set(asset.served_edge_ids)
        dependent_edges = {
            edge.id for edge in self.venue.edges if asset_id in edge.dependent_asset_ids
        }
        zones = sorted(
            {
                node.zone_id
                for node in self.venue.nodes
                if node.id in served_nodes and node.zone_id
            }
        )
        inaccessible = [] if route.found else ["N_L2_SEC_209_218"]
        consequences = ["Normal step-free access to Sections 209–218 is invalidated"]
        consequences.append(
            "A longer verified Corridor W3 fallback remains available"
            if route.found and "E_W3_FALLBACK_RAMP" in route.edge_ids
            else "No verified safe step-free route remains"
            if not route.found
            else "The normal step-free route remains available"
        )
        crowd_concerns = [
            f"{edge.id} is at {state.edge_crowd_overrides.get(edge.id, edge.current_crowd_percent):.0f}% synthetic crowd"
            for edge in self.venue.edges
            if state.edge_crowd_overrides.get(edge.id, edge.current_crowd_percent) >= 80
        ]
        return ImpactAnalysis(
            affected_node_ids=sorted(served_nodes),
            affected_edge_ids=sorted(served_edges | dependent_edges),
            affected_zone_ids=zones,
            inaccessible_destination_ids=inaccessible,
            accessibility_consequences=consequences,
            route_result=route,
            rejected_route_reasons=route.rejected_reasons,
            crowd_capacity_concerns=crowd_concerns,
            required_capabilities=["ACCESSIBILITY_TEAM", "VENUE_OPERATIONS", "MAINTENANCE"],
            context_version=state.context_version,
        )

    @staticmethod
    def _contradictions(reports: list[Report]) -> list[str]:
        combined = " ".join(report.raw_text.lower() for report in reports)
        contradictions = []
        if "open" in combined and "closed" in combined:
            contradictions.append("Selected reports disagree about whether the affected access path is open.")
        if "operational" in combined and any(term in combined for term in ("stuck", "failed", "out of service")):
            contradictions.append("Selected reports disagree about whether the facility is operational.")
        return contradictions

    def create_incident(self, request: IncidentCreate, actor: str = "CONTROLLER") -> Incident:
        with self._lock:
            if len(set(request.report_ids)) != len(request.report_ids):
                raise ValueError("Duplicate report identifiers are not allowed")
            reports = []
            for report_id in request.report_ids:
                report = self.repository.get_report(report_id)
                if report is None:
                    raise KeyError(f"Unknown report: {report_id}")
                reports.append(report)
            if request.confirmed_asset_id not in {asset.id for asset in self.venue.assets}:
                raise KeyError(f"Unknown asset: {request.confirmed_asset_id}")
            status = AssetStatus(request.confirmed_status)
            state = self.state_service.set_asset_status(request.confirmed_asset_id, status, "CONTROLLER_CONFIRMATION")
            impact = self._analyse_impact(request.confirmed_asset_id)
            verified_facts = [
                f"Controller confirmed {request.confirmed_asset_id} status as {status.value} at context v{state.context_version}."
            ]
            unverified_claims = [claim for report in reports for claim in report.extraction.unverified_claims]
            plan, recovery = self._generate_reviewable_plan(
                verified_facts,
                unverified_claims,
                impact,
                allow_guided_fallback=any(report.source == "GUIDED_DEMO" for report in reports),
            )
            plan_actor = (
                self.guided_demo_fallback_provider.name
                if self.guided_demo_fallback_provider is not None
                and plan.plan_source == PlanSource.LOCAL_DETERMINISTIC
                and any(
                    report.provenance == "GUIDED_DEMO_QUOTA_FALLBACK"
                    for report in reports
                )
                else self.ai_provider.name
            )
            now = _now()
            incident = Incident(
                id=f"INC-{uuid4().hex[:8].upper()}",
                report_ids=request.report_ids,
                status=IncidentStatus.PLAN_PROPOSED,
                verified_asset_ids=[request.confirmed_asset_id],
                verified_facts=verified_facts,
                unverified_claims=unverified_claims,
                contradictions=self._contradictions(reports),
                impact=impact,
                current_plan=plan,
                plan_recovery_records=[recovery] if recovery else [],
                created_at=now,
                updated_at=now,
            )
            self._audit(incident, "REPORTS_LINKED_AND_ASSET_CONFIRMED", f"Human linked {len(reports)} reports and confirmed {request.confirmed_asset_id}.", actor)
            if recovery:
                self._audit(
                    incident,
                    "PLAN_RECOVERED",
                    f"Unavailable or invalid model output was contained; source {plan.plan_source.value} is ready for human review.",
                    plan_actor,
                )
            self._audit(incident, "PLAN_PROPOSED", f"{plan.plan_source.value} proposed a deterministically valid plan; approval required.", plan_actor)
            self.repository.save_incident(incident)
            return incident.model_copy(deep=True)

    def _plan_validation_errors(
        self, plan: ResponsePlan, impact: ImpactAnalysis
    ) -> list[PlanValidationError]:
        errors: list[PlanValidationError] = []
        state = self.state_service.snapshot()
        if plan.context_version != state.context_version:
            errors.append(
                PlanValidationError(
                    code="STALE_CONTEXT_VERSION",
                    message=f"Plan context v{plan.context_version} is stale; current context is v{state.context_version}",
                )
            )
        if plan.approved_at is not None or plan.approved_by is not None:
            errors.append(
                PlanValidationError(
                    code="MODEL_SELF_APPROVAL",
                    message="AI proposals cannot mark themselves approved",
                )
            )
        if not plan.actions:
            errors.append(
                PlanValidationError(code="EMPTY_PLAN", message="A response plan must contain at least one action")
            )
        known_locations = {
            item.id
            for collection in (self.venue.assets, self.venue.nodes, self.venue.zones)
            for item in collection
        }
        for index, action in enumerate(plan.actions):
            if action.action_type not in ALLOWED_ACTION_TYPES:
                errors.append(PlanValidationError(code="DISALLOWED_ACTION_TYPE", message=f"Disallowed action type: {action.action_type}", action_index=index))
            if action.assigned_team not in KNOWN_TEAMS:
                errors.append(PlanValidationError(code="UNKNOWN_TEAM", message=f"Unknown team: {action.assigned_team}", action_index=index))
            if action.location_id not in known_locations:
                errors.append(PlanValidationError(code="UNKNOWN_LOCATION", message=f"Unknown action location: {action.location_id}", action_index=index))
            if any(dependency < 0 or dependency >= index for dependency in action.depends_on_action_indexes):
                errors.append(PlanValidationError(code="INVALID_ACTION_DEPENDENCY", message="Action dependencies must reference an earlier action index", action_index=index))
            if action.action_type == "STAFF_VERIFIED_ROUTE" and not impact.route_result.found:
                errors.append(PlanValidationError(code="NO_VERIFIED_ROUTE", message="A route action cannot be approved when no verified route exists", action_index=index))
        if not impact.route_result.found and plan.validity != PlanValidity.AWAITING_VERIFICATION:
            errors.append(
                PlanValidationError(
                    code="INVALID_NO_ROUTE_VALIDITY",
                    message="A no-route plan must remain AWAITING_VERIFICATION",
                )
            )
        return errors

    def _deterministic_containment_plan(self, impact: ImpactAnalysis) -> ResponsePlan:
        no_route = not impact.route_result.found
        return ResponsePlan(
            id=f"PLAN-{uuid4().hex[:8].upper()}",
            situation_assessment=(
                "Deterministic routing found no verified safe step-free route in the current operational context."
                if no_route
                else "The AI proposal remained invalid; deterministic containment is required before any route guidance."
            ),
            operational_objective="Contain affected spectators safely until authoritative route state is verified.",
            actions=[
                PlanAction(
                    action_type="ESTABLISH_WAITING_POINT",
                    title="Keep affected spectators at the staffed accessible waiting point",
                    assigned_team="ACCESSIBILITY_TEAM",
                    location_id="N_L2_WAIT_2",
                    rationale="Do not publish route guidance while the response remains in containment.",
                ),
                PlanAction(
                    action_type="DISPATCH_ACCESSIBILITY_TEAM",
                    title="Dispatch accessibility assistance to the waiting point",
                    assigned_team="ACCESSIBILITY_TEAM",
                    location_id="N_L2_WAIT_2",
                    rationale="Affected spectators require human assistance while movement is contained.",
                    depends_on_action_indexes=[0],
                ),
                PlanAction(
                    action_type="INSPECT_ASSET",
                    title="Verify Lift L2 status",
                    assigned_team="MAINTENANCE",
                    location_id="A_LIFT_2",
                    rationale="Only an authoritative asset-state change can enable route reassessment.",
                ),
                PlanAction(
                    action_type="VERIFY_ROUTE_STATUS",
                    title="Verify Corridor W3 status and reassess",
                    assigned_team="VENUE_OPERATIONS",
                    location_id="A_CORRIDOR_W3",
                    rationale="Reassess only after authoritative corridor state changes; do not issue positive route guidance.",
                ),
            ],
            risks=["Affected spectators may wait longer while no verified route exists"],
            assumptions=["The designated waiting point remains available and staffed"],
            missing_information=["Estimated restoration time for Lift L2 and Corridor W3"],
            confidence=1.0,
            reassessment_triggers=["Lift L2 status changes", "Corridor W3 status changes"],
            context_version=impact.context_version,
            validity=PlanValidity.AWAITING_VERIFICATION,
            plan_source=PlanSource.DETERMINISTIC_CONTAINMENT,
        )

    def _recover_invalid_plan(
        self,
        proposed_plan: ResponsePlan,
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        provider: AIProvider | None = None,
    ) -> tuple[ResponsePlan, PlanRecoveryRecord | None]:
        active_provider = provider or self.ai_provider
        if active_provider.name == "GEMINI":
            proposed_plan.plan_source = PlanSource.GEMINI
        errors = self._plan_validation_errors(proposed_plan, impact)
        if not errors:
            return proposed_plan, None

        record = PlanRecoveryRecord(
            original_plan=proposed_plan.model_copy(deep=True),
            validation_errors=errors,
            occurred_at=_now(),
        )
        try:
            repaired = active_provider.repair_plan(
                proposed_plan,
                errors,
                verified_facts,
                unverified_claims,
                impact,
                self.venue,
            )
            repaired.plan_source = (
                PlanSource.GEMINI_REPAIRED
                if active_provider.name == "GEMINI"
                else repaired.plan_source
            )
            record.repaired_plan = repaired.model_copy(deep=True)
            repair_errors = self._plan_validation_errors(repaired, impact)
            record.repair_validation_errors = repair_errors
            if not repair_errors:
                return repaired, record
        except Exception as error:
            record.repair_error_category = type(error).__name__

        fallback = self._deterministic_containment_plan(impact)
        fallback_errors = self._plan_validation_errors(fallback, impact)
        if fallback_errors:
            raise RuntimeError("Deterministic containment plan failed internal validation")
        record.fallback_used = True
        return fallback, record

    def _generate_reviewable_plan(
        self,
        verified_facts: list[str],
        unverified_claims: list[str],
        impact: ImpactAnalysis,
        allow_guided_fallback: bool = False,
    ) -> tuple[ResponsePlan, PlanRecoveryRecord | None]:
        provider = self.ai_provider
        try:
            proposed = provider.propose_plan(
                verified_facts, unverified_claims, impact, self.venue
            )
        except AIProviderQuotaError as error:
            if (
                allow_guided_fallback
                and impact.route_result.found
                and self.guided_demo_fallback_provider is not None
            ):
                provider = self.guided_demo_fallback_provider
                proposed = provider.propose_plan(
                    verified_facts, unverified_claims, impact, self.venue
                )
            else:
                fallback = self._deterministic_containment_plan(impact)
                return fallback, PlanRecoveryRecord(
                    repair_error_category=type(error).__name__,
                    fallback_used=True,
                    occurred_at=_now(),
                )
        except Exception as error:
            fallback = self._deterministic_containment_plan(impact)
            return fallback, PlanRecoveryRecord(
                repair_error_category=type(error).__name__,
                fallback_used=True,
                occurred_at=_now(),
            )
        return self._recover_invalid_plan(
            proposed, verified_facts, unverified_claims, impact, provider
        )

    def _validate_plan(self, incident: Incident, approve_revision: bool) -> None:
        plan = incident.proposed_revision if approve_revision else incident.current_plan
        if plan is None:
            raise ValueError("No proposed revision is available for approval")
        errors = self._plan_validation_errors(plan, incident.impact)
        if errors:
            raise ValueError(errors[0].message)

    def approve_plan(self, incident_id: str, request: ApprovalRequest) -> Incident:
        with self._lock:
            incident = self.get_incident(incident_id)
            if incident.current_plan.approved_at is not None and (
                not request.approve_revision or incident.proposed_revision is None
            ):
                return incident
            self._validate_plan(incident, request.approve_revision)
            if request.approve_revision:
                assert incident.proposed_revision is not None
                incident.current_plan.validity = PlanValidity.SUPERSEDED
                incident.current_plan = incident.proposed_revision
                incident.proposed_revision = None
                incident.reassessment = None
            plan = incident.current_plan
            if plan.validity == PlanValidity.UNSAFE:
                raise ValueError("Unsafe plans cannot be approved")
            plan.approved_at = _now()
            plan.approved_by = request.approved_by
            incident.status = IncidentStatus.MONITORING if plan.validity == PlanValidity.AWAITING_VERIFICATION else IncidentStatus.IN_PROGRESS
            if plan.id not in {task.source_plan_id for task in incident.tasks}:
                task_ids: list[str] = []
                for action in plan.actions:
                    dependency_ids = [task_ids[index] for index in action.depends_on_action_indexes if index < len(task_ids)]
                    task = Task(
                        id=f"TSK-{uuid4().hex[:8].upper()}",
                        title=action.title,
                        status=TaskStatus.CREATED,
                        priority="HIGH",
                        location_id=action.location_id,
                        assigned_team=action.assigned_team,
                        source_plan_id=plan.id,
                        dependency_task_ids=dependency_ids,
                        created_at=_now(),
                        updated_at=_now(),
                    )
                    incident.tasks.append(task)
                    task_ids.append(task.id)
                incident.communications.extend(self._communications(plan, incident.impact))
            self._audit(incident, "PLAN_APPROVED", f"Plan {plan.id} approved by {request.approved_by}; tasks and drafts created.", request.approved_by)
            incident.updated_at = _now()
            self.repository.save_incident(incident)
            return incident.model_copy(deep=True)

    @staticmethod
    def _communications(plan: ResponsePlan, impact: ImpactAnalysis) -> list[Communication]:
        if not impact.route_result.found or not any(
            action.action_type == "STAFF_VERIFIED_ROUTE" for action in plan.actions
        ):
            return []
        messages = {
            "en": "Lift L2 is unavailable. Follow instructions from accessibility staff; use only the verified route shown by venue personnel.",
            "es": "El ascensor L2 no está disponible. Siga las indicaciones del personal de accesibilidad y utilice solo la ruta verificada.",
            "fr": "L’ascenseur L2 est indisponible. Suivez les instructions de l’équipe d’accessibilité et utilisez uniquement l’itinéraire vérifié.",
        }
        now = _now()
        return [
            Communication(
                id=f"COM-{uuid4().hex[:8].upper()}",
                audience="AFFECTED_FANS",
                language=language,
                content=content,
                status=CommunicationStatus.DRAFT,
                source_plan_id=plan.id,
                created_at=now,
                updated_at=now,
            )
            for language, content in messages.items()
        ]

    def reassess(self, incident_id: str) -> Incident:
        with self._lock:
            incident = self.get_incident(incident_id)
            current_version = self.state_service.snapshot().context_version
            if incident.reassessment and incident.reassessment.new_context_version == current_version:
                return incident
            old_version = incident.current_plan.context_version
            impact = self._analyse_impact(incident.verified_asset_ids[0])
            if impact.context_version == old_version:
                if incident.reassessment:
                    return incident
                raise ValueError("Operational context has not changed; reassessment is unnecessary")
            validity = PlanValidity.VALID if impact.route_result.found else PlanValidity.UNSAFE
            try:
                explanation = self.ai_provider.explain_reassessment(old_version, impact)
            except Exception:
                explanation = (
                    f"Context changed from v{old_version} to v{impact.context_version}. "
                    "Deterministic route validation found no verified safe step-free route; "
                    "the approved plan is unsafe and human review is required."
                )
            state = self.state_service.snapshot()
            changed_facts = [
                f"{event.entity_id or 'operational state'} changed to {event.new_value} at v{event.context_version}"
                for event in state.event_history
                if event.context_version > old_version
            ]
            incident.current_plan.validity = validity
            incident.impact = impact
            incident.reassessment = Reassessment(
                old_context_version=old_version,
                new_context_version=impact.context_version,
                changed_facts=changed_facts,
                invalidated_assumptions=["Corridor W3 remains available for the approved fallback"] if not impact.route_result.found else [],
                affected_action_indexes=list(range(len(incident.current_plan.actions))) if not impact.route_result.found else [],
                route_difference="Previously verified route is no longer feasible" if not impact.route_result.found else "Verified route remains feasible",
                validity=validity,
                explanation=explanation,
            )
            if validity == PlanValidity.UNSAFE:
                current_plan_tasks = [
                    task
                    for task in incident.tasks
                    if task.source_plan_id == incident.current_plan.id
                ]
                for index, action in enumerate(incident.current_plan.actions):
                    if (
                        action.action_type == "STAFF_VERIFIED_ROUTE"
                        and index < len(current_plan_tasks)
                        and current_plan_tasks[index].status
                        not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED}
                    ):
                        current_plan_tasks[index].status = TaskStatus.CANCELLED
                        current_plan_tasks[index].updated_at = _now()
                for communication in incident.communications:
                    if communication.status not in {
                        CommunicationStatus.SUPERSEDED,
                        CommunicationStatus.REJECTED,
                    }:
                        communication.status = CommunicationStatus.SUPERSEDED
                        communication.updated_at = _now()
                incident.proposed_revision, recovery = self._generate_reviewable_plan(
                    incident.verified_facts,
                    incident.unverified_claims,
                    impact,
                    allow_guided_fallback=any(
                        (report := self.repository.get_report(report_id)) is not None
                        and report.source == "GUIDED_DEMO"
                        for report_id in incident.report_ids
                    ),
                )
                if recovery:
                    incident.plan_recovery_records.append(recovery)
                incident.status = IncidentStatus.PLAN_PROPOSED
            else:
                incident.status = IncidentStatus.MONITORING
            self._audit(incident, "PLAN_REASSESSED", f"Plan validity changed to {validity.value}; human review required.", self.ai_provider.name)
            incident.updated_at = _now()
            self.repository.save_incident(incident)
            return incident.model_copy(deep=True)

    def reassess_changed_incidents(self) -> list[Incident]:
        changed = []
        for incident in self.repository.list_incidents():
            if incident.current_plan.approved_at and incident.current_plan.context_version != self.state_service.snapshot().context_version:
                changed.append(self.reassess(incident.id))
        return changed

    def list_tasks(self) -> list[Task]:
        return [task for incident in self.repository.list_incidents() for task in incident.tasks]

    def update_task(self, task_id: str, update: TaskUpdate, actor: str) -> Task:
        with self._lock:
            for incident in self.repository.list_incidents():
                task = next((item for item in incident.tasks if item.id == task_id), None)
                if task is None:
                    continue
                if update.status not in TASK_TRANSITIONS[task.status]:
                    raise ValueError(f"Invalid task transition: {task.status.value} -> {update.status.value}")
                dependencies = {item.id: item for item in incident.tasks}
                if update.status in {TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED} and any(
                    dependencies[item_id].status != TaskStatus.COMPLETED for item_id in task.dependency_task_ids
                ):
                    raise ValueError("Task dependencies must be completed first")
                if update.status == TaskStatus.COMPLETED and not update.completion_evidence:
                    raise ValueError("Completion evidence is required")
                if update.status == TaskStatus.BLOCKED and not update.blocked_reason:
                    raise ValueError("A blocked reason is required")
                task.status = update.status
                task.updated_at = _now()
                task.completion_evidence = update.completion_evidence
                task.blocked_reason = update.blocked_reason
                task.completed_at = _now() if update.status == TaskStatus.COMPLETED else None
                if update.status == TaskStatus.BLOCKED:
                    incident.current_plan.validity = PlanValidity.REQUIRES_MODIFICATION
                    incident.status = IncidentStatus.MONITORING
                self._audit(incident, "TASK_STATUS_CHANGED", f"Task {task.id} changed to {task.status.value}.", actor)
                incident.updated_at = _now()
                self.repository.save_incident(incident)
                return task.model_copy(deep=True)
        raise KeyError(f"Unknown task: {task_id}")

    def list_communications(self) -> list[Communication]:
        return [item for incident in self.repository.list_incidents() for item in incident.communications]

    def update_communication(self, communication_id: str, update: CommunicationUpdate, actor: str) -> Communication:
        with self._lock:
            for incident in self.repository.list_incidents():
                communication = next((item for item in incident.communications if item.id == communication_id), None)
                if communication is None:
                    continue
                if update.status not in COMMUNICATION_TRANSITIONS[communication.status]:
                    raise ValueError(f"Invalid communication transition: {communication.status.value} -> {update.status.value}")
                communication.status = update.status
                communication.reviewed_by = actor
                communication.updated_at = _now()
                self._audit(incident, "COMMUNICATION_STATUS_CHANGED", f"Communication {communication.id} changed to {communication.status.value}.", actor)
                incident.updated_at = _now()
                self.repository.save_incident(incident)
                return communication.model_copy(deep=True)
        raise KeyError(f"Unknown communication: {communication_id}")

    def update_incident_status(self, incident_id: str, update: IncidentStatusUpdate, actor: str) -> Incident:
        with self._lock:
            incident = self.get_incident(incident_id)
            if update.status == IncidentStatus.RESOLVED:
                if incident.status not in {IncidentStatus.IN_PROGRESS, IncidentStatus.MONITORING}:
                    raise ValueError("Only active incidents can be resolved")
                if any(task.status not in {TaskStatus.COMPLETED, TaskStatus.CANCELLED} for task in incident.tasks):
                    raise ValueError("All tasks must be completed or cancelled before resolution")
                incident.current_plan.validity = PlanValidity.RESOLVED
            elif update.status == IncidentStatus.REJECTED:
                if incident.current_plan.approved_at:
                    raise ValueError("Approved incidents cannot be rejected")
            else:
                raise ValueError("Only RESOLVED or REJECTED terminal transitions are accepted here")
            incident.status = update.status
            incident.updated_at = _now()
            self._audit(incident, "INCIDENT_STATUS_CHANGED", f"Incident changed to {update.status.value}: {update.reason}", actor)
            self.repository.save_incident(incident)
            return incident.model_copy(deep=True)

    def audit_events(self) -> list[AuditEvent]:
        events = [event for incident in self.repository.list_incidents() for event in incident.audit_events]
        return sorted(events, key=lambda item: item.occurred_at, reverse=True)

    def reset(self) -> None:
        self.repository.clear()
