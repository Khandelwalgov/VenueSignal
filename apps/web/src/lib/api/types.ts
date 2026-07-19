export type NodeStatus = "OPEN" | "RESTRICTED" | "CLOSED";
export type EdgeStatus = NodeStatus;
export type AssetStatus = "OPERATIONAL" | "DEGRADED" | "OUT_OF_SERVICE" | "UNKNOWN";
export type ZoneStatus = "NORMAL" | "BUSY" | "RESTRICTED" | "CLOSED";
export type OperationalTeam = "MAINTENANCE" | "ACCESSIBILITY_TEAM" | "VENUE_OPERATIONS";
export type ActionType =
  | "INSPECT_ASSET"
  | "DISPATCH_ACCESSIBILITY_TEAM"
  | "STAFF_VERIFIED_ROUTE"
  | "ESTABLISH_WAITING_POINT"
  | "VERIFY_ROUTE_STATUS";
export type TaskStatus =
  | "CREATED"
  | "ASSIGNED"
  | "ACKNOWLEDGED"
  | "IN_PROGRESS"
  | "BLOCKED"
  | "COMPLETED"
  | "CANCELLED";
export type CommunicationStatus =
  | "DRAFT"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "PUBLISHED_SIMULATED"
  | "SUPERSEDED"
  | "REJECTED";
export type IncidentStatus =
  | "NEW"
  | "UNDER_REVIEW"
  | "NEEDS_CLARIFICATION"
  | "CONFIRMED"
  | "IMPACT_ANALYSED"
  | "PLAN_PROPOSED"
  | "PLAN_APPROVED"
  | "IN_PROGRESS"
  | "MONITORING"
  | "RESOLVED"
  | "REJECTED";
export type PlanValidity =
  | "VALID"
  | "PARTIALLY_VALID"
  | "REQUIRES_MODIFICATION"
  | "SUPERSEDED"
  | "UNSAFE"
  | "AWAITING_VERIFICATION"
  | "RESOLVED";
export type PlanSource =
  | "GEMINI"
  | "GEMINI_REPAIRED"
  | "DETERMINISTIC_CONTAINMENT"
  | "LOCAL_DETERMINISTIC";

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
  actionType: ActionType;
  title: string;
  assignedTeam: OperationalTeam;
  locationId: string;
  rationale: string;
}

export interface ResponsePlan {
  id: string;
  operationalObjective: string;
  actions: PlanAction[];
  confidence: number;
  contextVersion: number;
  validity: PlanValidity;
  planSource: PlanSource;
  approvedAt?: string;
  approvedBy?: string;
}

export interface WorkflowTask {
  id: string;
  title: string;
  status: TaskStatus;
  assignedTeam: OperationalTeam;
  dependencyTaskIds?: string[];
  completionEvidence?: string;
  blockedReason?: string;
}

export interface Communication {
  id: string;
  language: string;
  content: string;
  status: CommunicationStatus;
}

export interface Incident {
  id: string;
  reportIds: string[];
  status: IncidentStatus;
  verifiedFacts: string[];
  unverifiedClaims: string[];
  impact: {
    routeResult: RouteResult;
    accessibilityConsequences: string[];
    contextVersion: number;
  };
  currentPlan: ResponsePlan;
  proposedRevision?: ResponsePlan;
  reassessment?: {
    explanation: string;
    validity: PlanValidity;
    requiresHumanReview: boolean;
  };
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
