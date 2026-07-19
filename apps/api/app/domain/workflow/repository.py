from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Protocol

from app.domain.workflow.models import Incident, Report


class WorkflowRepository(Protocol):
    def list_reports(self) -> list[Report]: ...
    def get_report(self, report_id: str) -> Report | None: ...
    def save_report(self, report: Report) -> None: ...
    def find_report_by_fingerprint(self, fingerprint: str) -> Report | None: ...
    def list_incidents(self) -> list[Incident]: ...
    def get_incident(self, incident_id: str) -> Incident | None: ...
    def save_incident(self, incident: Incident) -> None: ...
    def clear(self) -> None: ...


class InMemoryWorkflowRepository:
    def __init__(self) -> None:
        self._reports: dict[str, Report] = {}
        self._incidents: dict[str, Incident] = {}
        self._lock = RLock()

    def list_reports(self) -> list[Report]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._reports.values()]

    def get_report(self, report_id: str) -> Report | None:
        with self._lock:
            item = self._reports.get(report_id)
            return item.model_copy(deep=True) if item else None

    def save_report(self, report: Report) -> None:
        with self._lock:
            self._reports[report.id] = report.model_copy(deep=True)

    def find_report_by_fingerprint(self, fingerprint: str) -> Report | None:
        with self._lock:
            item = next((report for report in self._reports.values() if report.fingerprint == fingerprint), None)
            return item.model_copy(deep=True) if item else None

    def list_incidents(self) -> list[Incident]:
        with self._lock:
            return [item.model_copy(deep=True) for item in self._incidents.values()]

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._lock:
            item = self._incidents.get(incident_id)
            return item.model_copy(deep=True) if item else None

    def save_incident(self, incident: Incident) -> None:
        with self._lock:
            self._incidents[incident.id] = incident.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._reports.clear()
            self._incidents.clear()


class SQLiteWorkflowRepository:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        with self._connection:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS workflow_reports (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)"
            )
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS workflow_incidents (id TEXT PRIMARY KEY, updated_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def list_reports(self) -> list[Report]:
        with self._lock:
            rows = self._connection.execute("SELECT payload FROM workflow_reports ORDER BY rowid").fetchall()
        return [Report.model_validate_json(row["payload"]) for row in rows]

    def get_report(self, report_id: str) -> Report | None:
        with self._lock:
            row = self._connection.execute("SELECT payload FROM workflow_reports WHERE id = ?", (report_id,)).fetchone()
        return Report.model_validate_json(row["payload"]) if row else None

    def save_report(self, report: Report) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO workflow_reports(id, fingerprint, payload) VALUES (?, ?, ?)",
                (report.id, report.fingerprint, report.model_dump_json()),
            )

    def find_report_by_fingerprint(self, fingerprint: str) -> Report | None:
        with self._lock:
            row = self._connection.execute("SELECT payload FROM workflow_reports WHERE fingerprint = ?", (fingerprint,)).fetchone()
        return Report.model_validate_json(row["payload"]) if row else None

    def list_incidents(self) -> list[Incident]:
        with self._lock:
            rows = self._connection.execute("SELECT payload FROM workflow_incidents ORDER BY updated_at DESC").fetchall()
        return [Incident.model_validate_json(row["payload"]) for row in rows]

    def get_incident(self, incident_id: str) -> Incident | None:
        with self._lock:
            row = self._connection.execute("SELECT payload FROM workflow_incidents WHERE id = ?", (incident_id,)).fetchone()
        return Incident.model_validate_json(row["payload"]) if row else None

    def save_incident(self, incident: Incident) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO workflow_incidents(id, updated_at, payload) VALUES (?, ?, ?)",
                (incident.id, incident.updated_at.isoformat(), incident.model_dump_json()),
            )

    def clear(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM workflow_reports")
            self._connection.execute("DELETE FROM workflow_incidents")


class FirestoreWorkflowRepository:
    """Production adapter. Import and credentials are resolved only when selected."""

    def __init__(self, client: Any | None = None, namespace: str = "venuesignal") -> None:
        if client is None:
            from google.cloud import firestore

            client = firestore.Client()
        self.client = client
        self.reports = client.collection(f"{namespace}_reports")
        self.incidents = client.collection(f"{namespace}_incidents")

    @staticmethod
    def _payload(model) -> dict[str, Any]:
        return json.loads(model.model_dump_json())

    def list_reports(self) -> list[Report]:
        return [Report.model_validate(snapshot.to_dict()) for snapshot in self.reports.stream()]

    def get_report(self, report_id: str) -> Report | None:
        snapshot = self.reports.document(report_id).get()
        return Report.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def save_report(self, report: Report) -> None:
        self.reports.document(report.id).set(self._payload(report))

    def find_report_by_fingerprint(self, fingerprint: str) -> Report | None:
        deterministic = self.reports.document(f"RPT-{fingerprint[:12].upper()}").get()
        if deterministic.exists:
            return Report.model_validate(deterministic.to_dict())
        # Legacy fallback for records created before deterministic report identifiers.
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter

            query = self.reports.where(
                filter=FieldFilter("fingerprint", "==", fingerprint)
            )
        except (ImportError, TypeError):
            # Compatibility with lightweight test doubles and older Firestore clients.
            query = self.reports.where("fingerprint", "==", fingerprint)
        snapshots = list(query.limit(1).stream())
        return Report.model_validate(snapshots[0].to_dict()) if snapshots else None

    def list_incidents(self) -> list[Incident]:
        return [Incident.model_validate(snapshot.to_dict()) for snapshot in self.incidents.stream()]

    def get_incident(self, incident_id: str) -> Incident | None:
        snapshot = self.incidents.document(incident_id).get()
        return Incident.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def save_incident(self, incident: Incident) -> None:
        self.incidents.document(incident.id).set(self._payload(incident))

    def clear(self) -> None:
        for collection in (self.reports, self.incidents):
            for snapshot in collection.stream():
                snapshot.reference.delete()
