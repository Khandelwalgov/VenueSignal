from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from pydantic import ValidationError

from app.domain.workflow.models import (
    ApprovalRequest,
    ImportPreview,
    Incident,
    IncidentCreate,
    Report,
    ReportCreate,
)
from app.domain.workflow.service import WorkflowService


router = APIRouter()
MAX_UPLOAD_BYTES = 200_000
MAX_IMPORT_ROWS = 50


def _service(request: Request) -> WorkflowService:
    return request.app.state.workflow_service


@router.get("/reports", response_model=list[Report], summary="List evaluator reports")
def list_reports(request: Request) -> list[Report]:
    return _service(request).list_reports()


@router.post(
    "/reports",
    response_model=Report,
    summary="Submit an untrusted operational report for structured extraction",
)
def create_report(request: Request, report: ReportCreate) -> Report:
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
            rows = payload if isinstance(payload, list) else payload.get("reports", [])
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

    if len(rows) > MAX_IMPORT_ROWS:
        raise HTTPException(status_code=413, detail="Import exceeds 50 row limit")
    reports: list[Report] = []
    errors: list[str] = []
    valid_requests: list[ReportCreate] = []
    for index, row in enumerate(rows, start=1):
        try:
            if not isinstance(row, dict):
                raise ValueError("row must be an object")
            raw_text = str(row.get("rawText") or row.get("raw_text") or "")
            if raw_text.startswith(("=", "+", "-", "@")):
                raise ValueError("formula-like report text is rejected")
            valid_requests.append(
                ReportCreate(
                    raw_text=raw_text,
                    language=str(row.get("language") or "en"),
                    source=str(row.get("source") or "EVALUATOR_UPLOAD"),
                    synthetic=bool(row.get("synthetic", True)),
                )
            )
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
    )


@router.get(
    "/incidents", response_model=list[Incident], summary="List current incidents"
)
def list_incidents(request: Request) -> list[Incident]:
    return _service(request).list_incidents()


@router.get(
    "/incidents/{incident_id}",
    response_model=Incident,
    summary="Get complete incident intelligence and audit state",
)
def get_incident(request: Request, incident_id: str) -> Incident:
    try:
        return _service(request).get_incident(incident_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/incidents",
    response_model=Incident,
    summary="Human-link reports and confirm an operational asset state",
)
def create_incident(request: Request, incident: IncidentCreate) -> Incident:
    try:
        return _service(request).create_incident(incident)
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
    request: Request, incident_id: str, approval: ApprovalRequest
) -> Incident:
    try:
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
def reassess(request: Request, incident_id: str) -> Incident:
    try:
        return _service(request).reassess(incident_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/reset", summary="Reset local workflow and operational demo state")
def reset_workflow(request: Request):
    _service(request).reset()
    state = request.app.state.operational_state_service.reset("WORKFLOW_RESET")
    return {"status": "reset", "contextVersion": state.context_version}
