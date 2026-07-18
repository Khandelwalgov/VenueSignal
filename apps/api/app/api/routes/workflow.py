from __future__ import annotations

import csv
import hashlib
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import ValidationError

from app.domain.workflow.models import (
    ApprovalRequest,
    AuditEvent,
    Communication,
    CommunicationUpdate,
    ImportPreview,
    Incident,
    IncidentCreate,
    IncidentStatusUpdate,
    Report,
    ReportCreate,
    Task,
    TaskUpdate,
)
from app.domain.workflow.service import WorkflowService
from app.security.auth import Principal, current_principal, require_controller


router = APIRouter()
MAX_UPLOAD_BYTES = 200_000
MAX_IMPORT_ROWS = 50


def _service(request: Request) -> WorkflowService:
    return request.app.state.workflow_service


@router.get("/reports", response_model=list[Report], summary="List evaluator reports")
def list_reports(request: Request, _principal: Principal = Depends(current_principal)) -> list[Report]:
    return _service(request).list_reports()


@router.post(
    "/reports",
    response_model=Report,
    summary="Submit an untrusted operational report for structured extraction",
)
def create_report(
    request: Request,
    report: ReportCreate,
    _principal: Principal = Depends(require_controller),
) -> Report:
    return _service(request).create_report(report)


@router.post(
    "/reports/import",
    response_model=ImportPreview,
    summary="Preview or import bounded CSV/JSON evaluator reports",
)
async def import_reports(
    request: Request,
    file: UploadFile = File(...),
    commit: bool = Query(default=False),
    idempotency_key: str | None = Query(default=None, min_length=8, max_length=120),
    _principal: Principal = Depends(require_controller),
) -> ImportPreview:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 200 KB limit")
    filename = (file.filename or "").lower()
    rows: list[dict] = []
    format_name: str
    try:
        if filename.endswith(".json") and file.content_type in {
            "application/json",
            "text/json",
            "application/octet-stream",
        }:
            format_name = "JSON"
            payload = json.loads(content.decode("utf-8"))
            rows = payload if isinstance(payload, list) else payload.get("reports", []) if isinstance(payload, dict) else []
        elif filename.endswith(".csv") and file.content_type in {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "application/octet-stream",
        }:
            format_name = "CSV"
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        else:
            raise HTTPException(
                status_code=415,
                detail="Only .csv and .json report files are accepted",
            )
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error) as error:
        raise HTTPException(status_code=422, detail=f"Malformed import file: {error}") from error

    if not isinstance(rows, list):
        raise HTTPException(status_code=422, detail="Import reports must be a list")
    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=413, detail="Import exceeds 50 row limit")
    reports: list[Report] = []
    errors: list[str] = []
    valid_requests: list[ReportCreate] = []
    duplicate_report_ids: list[str] = []
    import_fingerprint = hashlib.sha256(content).hexdigest()
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, dict):
                raise ValueError("row must be an object")
            raw_text = str(row.get("rawText") or row.get("raw_text") or "")
            if raw_text.lstrip().startswith(("=", "+", "-", "@")):
                raise ValueError("formula-like report text is rejected")
            item = ReportCreate(
                    raw_text=raw_text,
                    language=str(row.get("language") or "en"),
                    source=str(row.get("source") or "EVALUATOR_UPLOAD"),
                    synthetic=bool(row.get("synthetic", True)),
                    idempotency_key=(
                        f"{idempotency_key}:{index}"
                        if idempotency_key
                        else f"upload:{import_fingerprint}:{index}"
                    ),
                )
            duplicate = _service(request).repository.find_report_by_fingerprint(
                _service(request).report_fingerprint(item)
            )
            if duplicate:
                duplicate_report_ids.append(duplicate.id)
            valid_requests.append(item)
        except (ValidationError, ValueError) as error:
            errors.append(f"Row {index}: {error}")
    if commit and not errors:
        reports = [_service(request).create_report(item) for item in valid_requests]
    return ImportPreview(
        format=format_name,
        rows_detected=len(rows),
        valid_rows=len(valid_requests),
        errors=errors,
        reports=reports,
        duplicate_report_ids=duplicate_report_ids,
        import_fingerprint=import_fingerprint,
    )


@router.get(
    "/incidents", response_model=list[Incident], summary="List current incidents"
)
def list_incidents(request: Request, _principal: Principal = Depends(current_principal)) -> list[Incident]:
    return _service(request).list_incidents()


@router.get(
    "/incidents/{incident_id}",
    response_model=Incident,
    summary="Get complete incident intelligence and audit state",
)
def get_incident(
    request: Request,
    incident_id: str,
    _principal: Principal = Depends(current_principal),
) -> Incident:
    try:
        return _service(request).get_incident(incident_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/incidents",
    response_model=Incident,
    summary="Human-link reports and confirm an operational asset state",
)
def create_incident(
    request: Request,
    incident: IncidentCreate,
    principal: Principal = Depends(require_controller),
) -> Incident:
    try:
        return _service(request).create_incident(incident, principal.display_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post(
    "/incidents/{incident_id}/approve",
    response_model=Incident,
    summary="Human-approve a current-context response plan",
)
def approve_plan(
    request: Request,
    incident_id: str,
    approval: ApprovalRequest,
    principal: Principal = Depends(require_controller),
) -> Incident:
    try:
        if principal.auth_mode != "disabled":
            approval.approved_by = principal.display_name
        return _service(request).approve_plan(incident_id, approval)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/incidents/{incident_id}/reassess",
    response_model=Incident,
    summary="Revalidate an approved plan against changed operational context",
)
def reassess(
    request: Request,
    incident_id: str,
    _principal: Principal = Depends(require_controller),
) -> Incident:
    try:
        return _service(request).reassess(incident_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/tasks", response_model=list[Task], summary="List operational tasks")
def list_tasks(request: Request, _principal: Principal = Depends(current_principal)) -> list[Task]:
    return _service(request).list_tasks()


@router.patch("/tasks/{task_id}", response_model=Task, summary="Advance a task through validated lifecycle states")
def update_task(
    request: Request,
    task_id: str,
    update: TaskUpdate,
    principal: Principal = Depends(require_controller),
) -> Task:
    try:
        return _service(request).update_task(task_id, update, principal.display_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/communications", response_model=list[Communication], summary="List generated communication drafts")
def list_communications(
    request: Request, _principal: Principal = Depends(current_principal)
) -> list[Communication]:
    return _service(request).list_communications()


@router.post(
    "/communications/{communication_id}/transition",
    response_model=Communication,
    summary="Review, approve, reject, or simulate publication of a communication",
)
def update_communication(
    request: Request,
    communication_id: str,
    update: CommunicationUpdate,
    principal: Principal = Depends(require_controller),
) -> Communication:
    try:
        return _service(request).update_communication(communication_id, update, principal.display_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/incidents/{incident_id}/status", response_model=Incident, summary="Apply a validated terminal incident transition")
def update_incident_status(
    request: Request,
    incident_id: str,
    update: IncidentStatusUpdate,
    principal: Principal = Depends(require_controller),
) -> Incident:
    try:
        return _service(request).update_incident_status(incident_id, update, principal.display_name)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/audit", response_model=list[AuditEvent], summary="List immutable incident audit events")
def list_audit(request: Request, _principal: Principal = Depends(current_principal)) -> list[AuditEvent]:
    return _service(request).audit_events()


@router.post("/reset", summary="Reset local workflow and operational demo state")
def reset_workflow(
    request: Request, principal: Principal = Depends(require_controller)
):
    if not request.app.state.settings.demo_reset_enabled:
        raise HTTPException(status_code=403, detail="Demo reset is disabled in this environment")
    _service(request).reset()
    state = request.app.state.operational_state_service.reset(f"{principal.uid}:WORKFLOW_RESET")
    return {"status": "reset", "contextVersion": state.context_version}
