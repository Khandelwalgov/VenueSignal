from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

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
    ImpactAnalysis,
    Incident,
    IncidentCreate,
    IncidentStatus,
    PlanValidity,
    Reassessment,
    Report,
    ReportCreate,
    Task,
    TaskStatus,
)


ALLOWED_ACTION_TYPES = {
    "INSPECT_ASSET",
    "DISPATCH_ACCESSIBILITY_TEAM",
    "STAFF_VERIFIED_ROUTE",
    "ESTABLISH_WAITING_POINT",
    "VERIFY_ROUTE_STATUS",
}
KNOWN_TEAMS = {"MAINTENANCE", "ACCESSIBILITY_TEAM", "VENUE_OPERATIONS"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowService:
    def __init__(
        self,
        venue: Venue,
        state_service: OperationalStateService,
        routing_service: RoutingService,
        ai_provider: AIProvider,
    ) -> None:
        self.venue = venue
        self.state_service = state_service
        self.routing_service = routing_service
        self.ai_provider = ai_provider
        self._reports: dict[str, Report] = {}
        self._incidents: dict[str, Incident] = {}
        self._lock = RLock()

    def list_reports(self) -> list[Report]:
        with self._lock:
            return list(self._reports.values())

    def create_report(self, request: ReportCreate) -> Report:
        extraction = self.ai_provider.extract_report(
            request.raw_text, request.language, self.venue
        )
        related = []
        asset_ids = set(extraction.candidate_asset_ids)
        zone_ids = set(extraction.candidate_zone_ids)
        with self._lock:
            for report in self._reports.values():
                previous_assets = set(report.extraction.candidate_asset_ids)
                previous_zones = set(report.extraction.candidate_zone_ids)
                if asset_ids.intersection(previous_assets) or zone_ids.intersection(
                    previous_zones
                ):
                    related.append(report.id)
            report = Report(
                id=f"RPT-{uuid4().hex[:8].upper()}",
                raw_text=request.raw_text,
                language=request.language,
                source=request.source,
                synthetic=request.synthetic,
                extraction=extraction,
                related_report_ids=related,
                created_at=_now(),
            )
            self._reports[report.id] = report
            return report.model_copy(deep=True)

    def list_incidents(self) -> list[Incident]:
        with self._lock:
            return [incident.model_copy(deep=True) for incident in self._incidents.values()]

    def get_incident(self, incident_id: str) -> Incident:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None:
                raise KeyError(f"Unknown incident: {incident_id}")
            return incident.model_copy(deep=True)

    def _audit(
        self, incident: Incident, event_type: str, summary: str, actor: str
    ) -> None:
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
            edge.id
            for edge in self.venue.edges
            if asset_id in edge.dependent_asset_ids
        }
        zones = sorted(
            {
                node.zone_id
                for node in self.venue.nodes
                if node.id in served_nodes and node.zone_id
            }
        )
        inaccessible = [] if route.found else ["N_L2_SEC_209_218"]
        consequences = [
            "Normal step-free access to Sections 209–218 is invalidated"
        ]
        consequences.append(
            "A longer verified Corridor W3 fallback remains available"
            if route.found and "E_W3_FALLBACK_RAMP" in route.edge_ids
            else "No verified safe step-free route remains"
            if not route.found
            else "The normal step-free route remains available"
        )
        return ImpactAnalysis(
            affected_node_ids=sorted(served_nodes),
            affected_edge_ids=sorted(served_edges | dependent_edges),
            affected_zone_ids=zones,
            inaccessible_destination_ids=inaccessible,
            accessibility_consequences=consequences,
            route_result=route,
            context_version=state.context_version,
        )

    def _contradictions(self, reports: list[Report]) -> list[str]:
        combined = " ".join(report.raw_text.lower() for report in reports)
        if "open" in combined and "closed" in combined:
            return [
                "Selected reports disagree about whether the affected access path is open."
            ]
        return []

    def create_incident(self, request: IncidentCreate) -> Incident:
        with self._lock:
            missing = [report_id for report_id in request.report_ids if report_id not in self._reports]
            if missing:
                raise KeyError(f"Unknown reports: {', '.join(missing)}")
            if request.confirmed_asset_id not in {asset.id for asset in self.venue.assets}:
                raise KeyError(f"Unknown asset: {request.confirmed_asset_id}")
            reports = [self._reports[report_id] for report_id in request.report_ids]

            status = AssetStatus(request.confirmed_status)
            state = self.state_service.set_asset_status(
                request.confirmed_asset_id, status, "CONTROLLER_CONFIRMATION"
            )
            impact = self._analyse_impact(request.confirmed_asset_id)
            verified_facts = [
                f"Controller confirmed {request.confirmed_asset_id} status as {status.value} at context v{state.context_version}."
            ]
            unverified_claims = [
                claim
                for report in reports
                for claim in report.extraction.unverified_claims
            ]
            plan = self.ai_provider.propose_plan(
                verified_facts, unverified_claims, impact, self.venue
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
                created_at=now,
                updated_at=now,
            )
            self._audit(
                incident,
                "REPORTS_LINKED_AND_ASSET_CONFIRMED",
                f"Human linked {len(reports)} reports and confirmed {request.confirmed_asset_id}.",
                "CONTROLLER",
            )
            self._audit(
                incident,
                "PLAN_PROPOSED",
                f"{self.ai_provider.name} proposed a schema-valid plan; approval required.",
                self.ai_provider.name,
            )
            self._incidents[incident.id] = incident
            return incident.model_copy(deep=True)

    def _validate_plan(self, incident: Incident, approve_revision: bool) -> None:
        plan = incident.proposed_revision if approve_revision else incident.current_plan
        if plan is None:
            raise ValueError("No proposed revision is available for approval")
        state = self.state_service.snapshot()
        if plan.context_version != state.context_version:
            raise ValueError(
                f"Plan context v{plan.context_version} is stale; current context is v{state.context_version}"
            )
        known_locations = {
            item.id
            for collection in (
                self.venue.assets,
                self.venue.nodes,
                self.venue.zones,
            )
            for item in collection
        }
        for action in plan.actions:
            if action.action_type not in ALLOWED_ACTION_TYPES:
                raise ValueError(f"Disallowed action type: {action.action_type}")
            if action.assigned_team not in KNOWN_TEAMS:
                raise ValueError(f"Unknown team: {action.assigned_team}")
            if action.location_id not in known_locations:
                raise ValueError(f"Unknown action location: {action.location_id}")

    def approve_plan(self, incident_id: str, request: ApprovalRequest) -> Incident:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None:
                raise KeyError(f"Unknown incident: {incident_id}")
            self._validate_plan(incident, request.approve_revision)
            if request.approve_revision:
                assert incident.proposed_revision is not None
                incident.current_plan = incident.proposed_revision
                incident.proposed_revision = None
                incident.reassessment = None
            plan = incident.current_plan
            plan.approved_at = _now()
            plan.approved_by = request.approved_by
            if plan.validity == PlanValidity.UNSAFE:
                raise ValueError("Unsafe plans cannot be approved")
            incident.status = (
                IncidentStatus.MONITORING
                if plan.validity == PlanValidity.AWAITING_VERIFICATION
                else IncidentStatus.IN_PROGRESS
            )
            existing_plan_task_ids = {
                task.source_plan_id for task in incident.tasks
            }
            if plan.id not in existing_plan_task_ids:
                task_ids: list[str] = []
                for index, action in enumerate(plan.actions):
                    dependency_ids = [
                        task_ids[dependency_index]
                        for dependency_index in action.depends_on_action_indexes
                        if dependency_index < len(task_ids)
                    ]
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
                    )
                    incident.tasks.append(task)
                    task_ids.append(task.id)
                incident.communications.extend(self._communications(plan.id, plan))
            self._audit(
                incident,
                "PLAN_APPROVED",
                f"Plan {plan.id} approved by {request.approved_by}; tasks and drafts created.",
                request.approved_by,
            )
            incident.updated_at = _now()
            return incident.model_copy(deep=True)

    def _communications(self, plan_id: str, plan) -> list[Communication]:
        messages = {
            "en": "Lift L2 is unavailable. Follow instructions from accessibility staff; use only the verified route shown by venue personnel.",
            "es": "El ascensor L2 no está disponible. Siga las indicaciones del personal de accesibilidad y utilice solo la ruta verificada.",
            "fr": "L’ascenseur L2 est indisponible. Suivez les instructions de l’équipe d’accessibilité et utilisez uniquement l’itinéraire vérifié.",
        }
        return [
            Communication(
                id=f"COM-{uuid4().hex[:8].upper()}",
                audience="AFFECTED_FANS",
                language=language,
                content=content,
                status=CommunicationStatus.DRAFT,
                source_plan_id=plan_id,
                created_at=_now(),
            )
            for language, content in messages.items()
        ]

    def reassess(self, incident_id: str) -> Incident:
        with self._lock:
            incident = self._incidents.get(incident_id)
            if incident is None:
                raise KeyError(f"Unknown incident: {incident_id}")
            old_version = incident.current_plan.context_version
            impact = self._analyse_impact(incident.verified_asset_ids[0])
            if impact.context_version == old_version:
                raise ValueError("Operational context has not changed; reassessment is unnecessary")
            validity = (
                PlanValidity.VALID if impact.route_result.found else PlanValidity.UNSAFE
            )
            explanation = self.ai_provider.explain_reassessment(old_version, impact)
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
                invalidated_assumptions=(
                    ["Corridor W3 remains available for the approved fallback"]
                    if not impact.route_result.found
                    else []
                ),
                affected_action_indexes=(
                    list(range(len(incident.current_plan.actions)))
                    if not impact.route_result.found
                    else []
                ),
                route_difference=(
                    "Previously verified route is no longer feasible"
                    if not impact.route_result.found
                    else "Verified route remains feasible"
                ),
                validity=validity,
                explanation=explanation,
            )
            if validity == PlanValidity.UNSAFE:
                incident.proposed_revision = self.ai_provider.propose_plan(
                    incident.verified_facts,
                    incident.unverified_claims,
                    impact,
                    self.venue,
                )
                incident.status = IncidentStatus.PLAN_PROPOSED
            else:
                incident.status = IncidentStatus.MONITORING
            self._audit(
                incident,
                "PLAN_REASSESSED",
                f"Plan validity changed to {validity.value}; human review required.",
                self.ai_provider.name,
            )
            incident.updated_at = _now()
            return incident.model_copy(deep=True)

    def reset(self) -> None:
        with self._lock:
            self._reports.clear()
            self._incidents.clear()
