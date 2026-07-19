import { getAuthToken } from "@/lib/auth";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api"
).replace(/\/$/, "");

export type NodeStatus = "OPEN" | "RESTRICTED" | "CLOSED";
export type EdgeStatus = NodeStatus;
export type AssetStatus = "OPERATIONAL" | "DEGRADED" | "OUT_OF_SERVICE" | "UNKNOWN";
export type ZoneStatus = "NORMAL" | "BUSY" | "RESTRICTED" | "CLOSED";

export interface VenueMetadata {
  id: string;
  name: string;
  description: string;
  synthetic: boolean;
  schemaVersion: string;
  venueVersion: string;
  status: string;
  statistics: GraphStatistics;
}

export interface GraphStatistics {
  levels: number;
  zones: number;
  nodes: number;
  edges: number;
  assets: number;
  connectedComponents: number;
  isolatedNodes: number;
  accessibleDestinations: number;
  stepFreeEdges: number;
  staffOnlyEdges: number;
  verticalTransitions: number;
  criticalAssets: number;
  reachableNodesPerEntrance: Record<string, number>;
  stepFreeReachableNodesFromWestAccessibleEntrance: number;
}

export interface ValidationIssue {
  code: string;
  message: string;
  severity: "ERROR" | "WARNING";
  entityType?: string;
  entityId?: string;
  relatedIds: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  statistics: GraphStatistics;
}

export interface Level {
  id: string;
  venueId: string;
  label: string;
  index: number;
  description: string;
}

export interface Node {
  id: string;
  venueId: string;
  levelId: string;
  zoneId?: string;
  label: string;
  type: string;
  x: number;
  y: number;
  accessible: boolean;
  staffOnly: boolean;
  capacity: number;
  status: NodeStatus;
  assetId?: string;
  textDescription: string;
}

export interface Edge {
  id: string;
  fromNodeId: string;
  toNodeId: string;
  distanceMeters: number;
  estimatedSeconds: number;
  stepFree: boolean;
  containsStairs: boolean;
  slopeCategory: string;
  widthClass: string;
  maximumCapacity: number;
  currentCrowdPercent: number;
  staffOnly: boolean;
  status: EdgeStatus;
  dependentAssetIds: string[];
  noiseLevel: string;
  hasRestPoint: boolean;
  textDescription: string;
}

export interface Zone {
  id: string;
  venueId: string;
  levelId: string;
  label: string;
  type: string;
  capacity: number;
  occupancyPercent: number;
  status: ZoneStatus;
  nodeIds: string[];
  assetIds: string[];
}

export interface Asset {
  id: string;
  venueId: string;
  levelId: string;
  zoneId?: string;
  type: string;
  label: string;
  status: AssetStatus;
  accessibilityCritical: boolean;
  servedNodeIds: string[];
  servedEdgeIds: string[];
  textDescription: string;
}

export interface LevelData {
  level: Level;
  nodes: Node[];
  edges: Edge[];
  zones: Zone[];
  assets: Asset[];
}

export interface AccessibilityCheck {
  destinationNodeId: string;
  destinationLabel: string;
  reachableStepFree: boolean;
}

export interface AccessibilitySummary {
  entranceNodeIds: string[];
  checks: AccessibilityCheck[];
  allDesignatedDestinationsReachable: boolean;
}

export interface OperationalEvent {
  id: string;
  eventType: string;
  entityId?: string;
  previousValue?: string | number;
  newValue?: string | number;
  contextVersion: number;
  occurredAt: string;
  source: string;
  synthetic: boolean;
}

export interface OperationalState {
  contextVersion: number;
  assetStatusOverrides: Record<string, AssetStatus>;
  edgeStatusOverrides: Record<string, EdgeStatus>;
  zoneStatusOverrides: Record<string, ZoneStatus>;
  edgeCrowdOverrides: Record<string, number>;
  eventHistory: OperationalEvent[];
  lastUpdatedAt: string;
}

export interface RouteResult {
  found: boolean;
  nodeIds: string[];
  edgeIds: string[];
  distanceMeters: number;
  estimatedSeconds: number;
  constraintsSatisfied: string[];
  rejectedReasons: string[];
  message: string;
  operationalContextVersion: number;
}

export interface ReportExtraction {
  category: string;
  summary: string;
  candidateZoneIds: string[];
  candidateAssetIds: string[];
  affectedGroups: string[];
  observedSymptoms: string[];
  urgencySuggestion: string;
  confidence: number;
  unverifiedClaims: string[];
  missingInformation: string[];
  clarificationQuestions: string[];
  untrustedInstructionDetected: boolean;
  provider: string;
}

export interface VenueReport {
  id: string;
  rawText: string;
  language: string;
  source: string;
  synthetic: boolean;
  extraction: ReportExtraction;
  relatedReportIds: string[];
  matchCandidates: Array<{
    reportId: string;
    score: number;
    recommendation: "LINK" | "CREATE_NEW" | "HUMAN_REVIEW_REQUIRED";
    reasons: string[];
  }>;
  provenance?: string;
  createdAt: string;
}

export interface PlanAction {
  actionType: string;
  title: string;
  assignedTeam: string;
  locationId: string;
  rationale: string;
}

export interface ResponsePlan {
  id: string;
  operationalObjective: string;
  actions: PlanAction[];
  confidence: number;
  contextVersion: number;
  validity: string;
  planSource: "GEMINI" | "GEMINI_REPAIRED" | "DETERMINISTIC_CONTAINMENT" | "LOCAL_DETERMINISTIC";
  approvedAt?: string;
  approvedBy?: string;
}

export interface WorkflowTask {
  id: string;
  title: string;
  status: string;
  assignedTeam: string;
  dependencyTaskIds?: string[];
  completionEvidence?: string;
  blockedReason?: string;
}

export interface Communication {
  id: string;
  language: string;
  content: string;
  status: string;
}

export interface Incident {
  id: string;
  reportIds: string[];
  status: string;
  verifiedFacts: string[];
  unverifiedClaims: string[];
  impact: { routeResult: RouteResult; accessibilityConsequences: string[]; contextVersion: number };
  currentPlan: ResponsePlan;
  proposedRevision?: ResponsePlan;
  reassessment?: { explanation: string; validity: string; requiresHumanReview: boolean };
  planRecoveryRecords?: Array<{
    validationErrors: Array<{ code: string; message: string; actionIndex?: number }>;
    repairValidationErrors: Array<{ code: string; message: string; actionIndex?: number }>;
    repairErrorCategory?: string;
    fallbackUsed: boolean;
  }>;
  tasks: WorkflowTask[];
  communications: Communication[];
}

export interface Principal {
  uid: string;
  displayName: string;
  role: "CONTROLLER" | "VIEWER";
  authMode: string;
}

export interface AuditEvent {
  id: string;
  eventType: string;
  summary: string;
  contextVersion: number;
  occurredAt: string;
  actor: string;
}

export interface ImportPreview {
  format: string;
  rowsDetected: number;
  validRows: number;
  errors: string[];
  reports: VenueReport[];
  duplicateReportIds: string[];
  importFingerprint: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const hasFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(hasFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail = `VenueSignal API request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch { /* Preserve the safe status message. */ }
    throw new Error(detail);
  }
  const data: unknown = await response.json();
  if (data === null || typeof data !== "object") {
    throw new Error("VenueSignal API returned an invalid response");
  }
  return data as T;
}

export function fetchVenue(venueId: string): Promise<VenueMetadata> {
  return requestJson(`/venues/${venueId}`);
}

export function fetchLevel(venueId: string, levelId: string): Promise<LevelData> {
  return requestJson(`/venues/${venueId}/levels/${levelId}`);
}

export function fetchValidation(venueId: string): Promise<ValidationResult> {
  return requestJson(`/venues/${venueId}/validation`);
}

export function fetchAccessibilitySummary(
  venueId: string,
): Promise<AccessibilitySummary> {
  return requestJson(`/venues/${venueId}/accessibility-summary`);
}

export function fetchOperationalState(): Promise<OperationalState> {
  return requestJson("/operations/state");
}

export function setAssetStatus(
  assetId: string,
  status: AssetStatus,
  source = "EVALUATOR_UI",
): Promise<OperationalState> {
  return requestJson(`/operations/assets/${assetId}/status`, {
    method: "POST",
    body: JSON.stringify({ status, source }),
  });
}

export function resetOperationalState(): Promise<OperationalState> {
  return requestJson("/operations/reset", { method: "POST" });
}

export function fetchGoldenStepFreeRoute(): Promise<RouteResult> {
  return requestJson("/operations/routes/query", {
    method: "POST",
    body: JSON.stringify({
      startNodeId: "N_L0_W_ACC_ENT",
      destinationNodeId: "N_L2_SEC_209_218",
      constraints: { stepFree: true, includeStaffOnly: false },
    }),
  });
}

export function createReport(rawText: string, guidedDemo = false): Promise<VenueReport> {
  return requestJson("/workflow/reports", {
    method: "POST",
    body: JSON.stringify({ rawText, language: "en", source: guidedDemo ? "GUIDED_DEMO" : "EVALUATOR_UI", synthetic: true }),
  });
}

export function createIncident(reportIds: string[]): Promise<Incident> {
  return requestJson("/workflow/incidents", {
    method: "POST",
    body: JSON.stringify({ reportIds, confirmedAssetId: "A_LIFT_2", confirmedStatus: "OUT_OF_SERVICE" }),
  });
}

export function approveIncident(incidentId: string, approveRevision = false): Promise<Incident> {
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

export function fetchPrincipal(): Promise<Principal> {
  return requestJson("/auth/me");
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
  status: string,
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
  status: string,
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
