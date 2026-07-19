import { requestJson } from "./client";
import {
  AuditEvent,
  Communication,
  CommunicationStatus,
  ImportPreview,
  Incident,
  TaskStatus,
  VenueReport,
  WorkflowTask,
} from "./types";


export function createReport(rawText: string, guidedDemo = false): Promise<VenueReport> {
  return requestJson("/workflow/reports", {
    method: "POST",
    body: JSON.stringify({
      rawText,
      language: "en",
      source: guidedDemo ? "GUIDED_DEMO" : "EVALUATOR_UI",
      synthetic: true,
    }),
  });
}

export function createIncident(reportIds: string[]): Promise<Incident> {
  return requestJson("/workflow/incidents", {
    method: "POST",
    body: JSON.stringify({
      reportIds,
      confirmedAssetId: "A_LIFT_2",
      confirmedStatus: "OUT_OF_SERVICE",
    }),
  });
}

export function approveIncident(
  incidentId: string,
  approveRevision = false,
): Promise<Incident> {
  return requestJson(`/workflow/incidents/${incidentId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approvedBy: "Evaluator Controller", approveRevision }),
  });
}

export function reassessIncident(incidentId: string): Promise<Incident> {
  return requestJson(`/workflow/incidents/${incidentId}/reassess`, { method: "POST" });
}

export function updateIncidentStatus(
  incidentId: string,
  status: "RESOLVED" | "REJECTED",
  reason: string,
): Promise<Incident> {
  return requestJson(`/workflow/incidents/${incidentId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, reason }),
  });
}

export function fetchReports(): Promise<VenueReport[]> {
  return requestJson("/workflow/reports");
}

export function fetchIncidents(): Promise<Incident[]> {
  return requestJson("/workflow/incidents");
}

export function fetchTasks(): Promise<WorkflowTask[]> {
  return requestJson("/workflow/tasks");
}

export function fetchCommunications(): Promise<Communication[]> {
  return requestJson("/workflow/communications");
}

export function fetchAudit(): Promise<AuditEvent[]> {
  return requestJson("/workflow/audit");
}

export function updateTask(
  taskId: string,
  status: TaskStatus,
  completionEvidence?: string,
  blockedReason?: string,
): Promise<WorkflowTask> {
  return requestJson(`/workflow/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ status, completionEvidence, blockedReason }),
  });
}

export function updateCommunication(
  communicationId: string,
  status: CommunicationStatus,
): Promise<Communication> {
  return requestJson(`/workflow/communications/${communicationId}/transition`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
}

export function importReports(file: File, commit = false): Promise<ImportPreview> {
  const form = new FormData();
  form.append("file", file);
  return requestJson(`/workflow/reports/import?commit=${commit}`, {
    method: "POST",
    body: form,
  });
}
