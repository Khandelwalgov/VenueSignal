from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.domain.operations.models import RouteResult
from app.domain.venue.models import CamelModel


class IncidentStatus(str, Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFIRMED = "CONFIRMED"
    IMPACT_ANALYSED = "IMPACT_ANALYSED"
    PLAN_PROPOSED = "PLAN_PROPOSED"
    PLAN_APPROVED = "PLAN_APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class PlanValidity(str, Enum):
    VALID = "VALID"
    PARTIALLY_VALID = "PARTIALLY_VALID"
    REQUIRES_MODIFICATION = "REQUIRES_MODIFICATION"
    SUPERSEDED = "SUPERSEDED"
    UNSAFE = "UNSAFE"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    RESOLVED = "RESOLVED"


class PlanSource(str, Enum):
    GEMINI = "GEMINI"
    GEMINI_REPAIRED = "GEMINI_REPAIRED"
    DETERMINISTIC_CONTAINMENT = "DETERMINISTIC_CONTAINMENT"
    LOCAL_DETERMINISTIC = "LOCAL_DETERMINISTIC"


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CommunicationStatus(str, Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED_SIMULATED = "PUBLISHED_SIMULATED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ReportExtraction(CamelModel):
    category: str
    summary: str
    candidate_zone_ids: list[str] = Field(default_factory=list)
    candidate_asset_ids: list[str] = Field(default_factory=list)
    affected_groups: list[str] = Field(default_factory=list)
    observed_symptoms: list[str] = Field(default_factory=list)
    urgency_suggestion: str
    confidence: float = Field(ge=0, le=1)
    unverified_claims: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    untrusted_instruction_detected: bool = False
    provider: str


class ReportCreate(CamelModel):
    raw_text: str = Field(min_length=3, max_length=4000)
    language: str = Field(default="en", pattern="^(en|es|fr)$")
    source: str = Field(default="EVALUATOR", max_length=80)
    synthetic: bool = True
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=120)


class IncidentMatchCandidate(CamelModel):
    report_id: str
    score: float = Field(ge=0, le=1)
    recommendation: str = Field(pattern="^(LINK|CREATE_NEW|HUMAN_REVIEW_REQUIRED)$")
    reasons: list[str]
    meaningful_differences: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class Report(CamelModel):
    id: str
    raw_text: str
    language: str
    source: str
    synthetic: bool
    extraction: ReportExtraction
    related_report_ids: list[str] = Field(default_factory=list)
    match_candidates: list[IncidentMatchCandidate] = Field(default_factory=list)
    fingerprint: str
    duplicate_of_report_id: str | None = None
    provenance: str = "USER_SUBMITTED"
    created_at: datetime


class IncidentCreate(CamelModel):
    report_ids: list[str] = Field(min_length=1, max_length=20)
    confirmed_asset_id: str
    confirmed_status: str = "OUT_OF_SERVICE"


class ImpactAnalysis(CamelModel):
    affected_node_ids: list[str]
    affected_edge_ids: list[str]
    affected_zone_ids: list[str]
    inaccessible_destination_ids: list[str]
    accessibility_consequences: list[str]
    route_result: RouteResult
    rejected_route_reasons: list[str] = Field(default_factory=list)
    crowd_capacity_concerns: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    context_version: int


class PlanAction(CamelModel):
    action_type: str
    title: str
    assigned_team: str
    location_id: str
    rationale: str
    depends_on_action_indexes: list[int] = Field(default_factory=list)


class ResponsePlan(CamelModel):
    id: str
    situation_assessment: str
    operational_objective: str
    actions: list[PlanAction]
    risks: list[str]
    assumptions: list[str]
    missing_information: list[str]
    confidence: float = Field(ge=0, le=1)
    reassessment_triggers: list[str]
    context_version: int
    validity: PlanValidity
    plan_source: PlanSource = PlanSource.LOCAL_DETERMINISTIC
    approved_at: datetime | None = None
    approved_by: str | None = None


class PlanValidationError(CamelModel):
    code: str
    message: str
    action_index: int | None = None


class PlanRecoveryRecord(CamelModel):
    original_plan: ResponsePlan | None = None
    validation_errors: list[PlanValidationError] = Field(default_factory=list)
    repaired_plan: ResponsePlan | None = None
    repair_validation_errors: list[PlanValidationError] = Field(default_factory=list)
    repair_error_category: str | None = None
    fallback_used: bool = False
    occurred_at: datetime


class Task(CamelModel):
    id: str
    title: str
    status: TaskStatus
    priority: str
    location_id: str
    assigned_team: str
    source_plan_id: str
    dependency_task_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    completion_evidence: str | None = None
    blocked_reason: str | None = None


class Communication(CamelModel):
    id: str
    audience: str
    language: str
    content: str
    status: CommunicationStatus
    source_plan_id: str
    created_at: datetime
    updated_at: datetime | None = None
    reviewed_by: str | None = None


class AuditEvent(CamelModel):
    id: str
    event_type: str
    summary: str
    context_version: int
    occurred_at: datetime
    actor: str


class Reassessment(CamelModel):
    old_context_version: int
    new_context_version: int
    changed_facts: list[str]
    invalidated_assumptions: list[str]
    affected_action_indexes: list[int]
    route_difference: str
    validity: PlanValidity
    explanation: str
    requires_human_review: bool = True


class Incident(CamelModel):
    id: str
    report_ids: list[str]
    status: IncidentStatus
    verified_asset_ids: list[str]
    verified_facts: list[str]
    unverified_claims: list[str]
    contradictions: list[str]
    impact: ImpactAnalysis
    current_plan: ResponsePlan
    proposed_revision: ResponsePlan | None = None
    reassessment: Reassessment | None = None
    plan_recovery_records: list[PlanRecoveryRecord] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    communications: list[Communication] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApprovalRequest(CamelModel):
    approved_by: str = Field(min_length=2, max_length=80)
    approve_revision: bool = False


class TaskUpdate(CamelModel):
    status: TaskStatus
    completion_evidence: str | None = Field(default=None, max_length=1000)
    blocked_reason: str | None = Field(default=None, max_length=500)


class CommunicationUpdate(CamelModel):
    status: CommunicationStatus


class IncidentStatusUpdate(CamelModel):
    status: IncidentStatus
    reason: str = Field(min_length=3, max_length=500)


class ImportPreview(CamelModel):
    format: str
    rows_detected: int
    valid_rows: int
    errors: list[str]
    reports: list[Report] = Field(default_factory=list)
    duplicate_report_ids: list[str] = Field(default_factory=list)
    import_fingerprint: str
