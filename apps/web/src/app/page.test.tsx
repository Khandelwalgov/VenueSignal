import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import Home from "./page";
import * as api from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchVenue: vi.fn(),
    fetchLevel: vi.fn(),
    fetchValidation: vi.fn(),
    fetchAccessibilitySummary: vi.fn(),
    fetchOperationalState: vi.fn(),
    fetchGoldenStepFreeRoute: vi.fn(),
    setAssetStatus: vi.fn(),
    resetOperationalState: vi.fn(),
    createReport: vi.fn(),
    createIncident: vi.fn(),
    approveIncident: vi.fn(),
    reassessIncident: vi.fn(),
    updateIncidentStatus: vi.fn(),
    fetchPrincipal: vi.fn(),
    fetchReports: vi.fn(),
    fetchIncidents: vi.fn(),
    fetchTasks: vi.fn(),
    fetchCommunications: vi.fn(),
    fetchAudit: vi.fn(),
    importReports: vi.fn(),
    updateTask: vi.fn(),
    updateCommunication: vi.fn(),
  };
});

const venue = {
  id: "unity-stadium",
  name: "Unity Stadium",
  description: "Synthetic venue",
  synthetic: true,
  schemaVersion: "1.0",
  venueVersion: "1.0",
  status: "OPERATIONAL",
  statistics: {
    levels: 3, zones: 2, nodes: 3, edges: 2, assets: 2,
    connectedComponents: 1, isolatedNodes: 0, accessibleDestinations: 1,
    stepFreeEdges: 2, staffOnlyEdges: 0, verticalTransitions: 1,
    criticalAssets: 1, reachableNodesPerEntrance: { N_L0_W_ACC_ENT: 3 },
    stepFreeReachableNodesFromWestAccessibleEntrance: 3,
  },
} satisfies api.VenueMetadata;

const level = {
  level: { id: "L2", venueId: "unity-stadium", label: "Level 2 - Upper seating concourse", index: 2, description: "Upper" },
  zones: [{ id: "Z_L2_W", venueId: "unity-stadium", levelId: "L2", label: "Upper West Concourse", type: "CONCOURSE", capacity: 5000, occupancyPercent: 12, status: "NORMAL", nodeIds: ["N_L2_LIFT_2", "N_L2_SEC"], assetIds: ["A_LIFT_2"] }],
  nodes: [
    { id: "N_L2_LIFT_2", venueId: "unity-stadium", levelId: "L2", zoneId: "Z_L2_W", label: "Lift L2 (L2)", type: "LIFT", x: 300, y: 500, accessible: true, staffOnly: false, capacity: 20, status: "OPEN", assetId: "A_LIFT_2", textDescription: "Lift access" },
    { id: "N_L2_SEC", venueId: "unity-stadium", levelId: "L2", zoneId: "Z_L2_W", label: "Sections 209-218", type: "SEATING", x: 250, y: 100, accessible: true, staffOnly: false, capacity: 12000, status: "OPEN", textDescription: "Upper seating" },
  ],
  edges: [{ id: "E_TEST", fromNodeId: "N_L2_LIFT_2", toNodeId: "N_L2_SEC", distanceMeters: 40, estimatedSeconds: 35, stepFree: true, containsStairs: false, slopeCategory: "FLAT", widthClass: "WIDE", maximumCapacity: 1000, currentCrowdPercent: 20, staffOnly: false, status: "OPEN", dependentAssetIds: [], noiseLevel: "MEDIUM", hasRestPoint: false, textDescription: "Test edge" }],
  assets: [
    { id: "A_LIFT_2", venueId: "unity-stadium", levelId: "L0", zoneId: "Z_L0", type: "LIFT", label: "Lift L2", status: "OPERATIONAL", accessibilityCritical: true, servedNodeIds: ["N_L2_LIFT_2"], servedEdgeIds: ["E_TEST"], textDescription: "Critical multi-level lift" },
    { id: "A_STAIR_2", venueId: "unity-stadium", levelId: "L0", zoneId: "Z_L0", type: "STAIRS", label: "Staircase S2", status: "OPERATIONAL", accessibilityCritical: false, servedNodeIds: [], servedEdgeIds: [], textDescription: "Stairs" },
  ],
} satisfies api.LevelData;

const validation = { valid: true, errors: [], warnings: [], statistics: venue.statistics } satisfies api.ValidationResult;
const accessibility = { entranceNodeIds: ["N_L0_W_ACC_ENT"], allDesignatedDestinationsReachable: true, checks: [{ destinationNodeId: "N_L2_SEC", destinationLabel: "Sections 209-218", reachableStepFree: true }] } satisfies api.AccessibilitySummary;
const operationalState = { contextVersion: 1, assetStatusOverrides: {}, edgeStatusOverrides: {}, zoneStatusOverrides: {}, edgeCrowdOverrides: {}, eventHistory: [], lastUpdatedAt: "2026-07-15T00:00:00Z" } satisfies api.OperationalState;
const normalRoute = { found: true, nodeIds: ["N_L0_W_ACC_ENT", "N_L2_SEC"], edgeIds: ["E_TEST"], distanceMeters: 215, estimatedSeconds: 240, constraintsSatisfied: ["STEP_FREE", "PUBLIC_ONLY"], rejectedReasons: [], message: "Verified route found using deterministic graph constraints.", operationalContextVersion: 1 } satisfies api.RouteResult;

function mockSuccess() {
  vi.mocked(api.fetchVenue).mockResolvedValue(venue);
  vi.mocked(api.fetchLevel).mockResolvedValue(level);
  vi.mocked(api.fetchValidation).mockResolvedValue(validation);
  vi.mocked(api.fetchAccessibilitySummary).mockResolvedValue(accessibility);
  vi.mocked(api.fetchOperationalState).mockResolvedValue(operationalState);
  vi.mocked(api.fetchGoldenStepFreeRoute).mockResolvedValue(normalRoute);
  vi.mocked(api.setAssetStatus).mockResolvedValue(operationalState);
  vi.mocked(api.resetOperationalState).mockResolvedValue(operationalState);
  vi.mocked(api.fetchPrincipal).mockResolvedValue({ uid: "local-controller", displayName: "Local Demo Controller", role: "CONTROLLER", authMode: "disabled" });
  vi.mocked(api.fetchReports).mockResolvedValue([]);
  vi.mocked(api.fetchIncidents).mockResolvedValue([]);
  vi.mocked(api.fetchTasks).mockResolvedValue([]);
  vi.mocked(api.fetchCommunications).mockResolvedValue([]);
  vi.mocked(api.fetchAudit).mockResolvedValue([]);
}

describe("VenueSignal Phase 1 workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSuccess();
  });

  it("renders disclosure, validation, statistics, text alternative, and non-colour legend", async () => {
    render(<Home />);
    expect(await screen.findByText("Validated canonical graph")).toBeVisible();
    expect(screen.getByText(/Unity Stadium is synthetic/)).toBeVisible();
    expect(screen.getByText("Components")).toBeVisible();
    expect(screen.getByRole("group", { name: /operations map/i })).toBeVisible();
    expect(screen.getByText("✓ Open")).toBeVisible();
    expect(screen.getByText("! Restricted")).toBeVisible();
    expect(screen.getByText("× Closed")).toBeVisible();
    expect(screen.getAllByText("Sections 209-218").length).toBeGreaterThan(0);
  });

  it("switches levels and selects a zone through mirrored controls", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Validated canonical graph");
    await user.click(screen.getByRole("button", { name: /Level 1, Lower concourse/i }));
    await waitFor(() => expect(api.fetchLevel).toHaveBeenLastCalledWith("unity-stadium", "L1"));
    const zoneList = screen.getByRole("group", { name: "Zones on current level" });
    await user.click(within(zoneList).getByRole("button", { name: /Upper West Concourse/i }));
    expect(screen.getByRole("heading", { name: "Upper West Concourse" })).toBeVisible();
  });

  it("selects multi-level Lift L2 on Level 2 and shows details", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Validated canonical graph");
    await user.click(screen.getByRole("button", { name: /Level 2, Upper concourse/i }));
    const facilityList = screen.getByRole("group", { name: "Facilities on current level" });
    await user.click(within(facilityList).getByRole("button", { name: /Lift L2/i }));
    expect(screen.getByRole("heading", { name: "Lift L2" })).toBeVisible();
    expect(screen.getByText(/route validation must account/)).toBeVisible();
  });

  it("filters facilities and supports keyboard activation on the map", async () => {
    const user = userEvent.setup();
    render(<Home />);
    await screen.findByText("Validated canonical graph");
    await user.selectOptions(screen.getByLabelText("Facility filter"), "STAIRS");
    const facilityList = screen.getByRole("group", { name: "Facilities on current level" });
    expect(within(facilityList).queryByRole("button", { name: /Lift L2/i })).not.toBeInTheDocument();
    expect(within(facilityList).getByRole("button", { name: /Staircase S2/i })).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Facility filter"), "ALL");
    const mapLift = screen.getByRole("button", { name: /Lift L2, asset status OPERATIONAL/i });
    mapLift.focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("heading", { name: "Lift L2" })).toBeVisible();
  });

  it("shows an understandable network error", async () => {
    vi.mocked(api.fetchVenue).mockRejectedValue(new Error("API offline"));
    render(<Home />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Venue data could not be loaded");
    expect(screen.getByRole("alert")).toHaveTextContent("API offline");
  });

  it("applies real scenario state and presents a no-route containment response", async () => {
    const user = userEvent.setup();
    const failedState = { ...operationalState, contextVersion: 3, assetStatusOverrides: { A_LIFT_2: "OUT_OF_SERVICE", A_CORRIDOR_W3: "OUT_OF_SERVICE" } } satisfies api.OperationalState;
    const noRoute = { ...normalRoute, found: false, edgeIds: [], nodeIds: [], distanceMeters: 0, estimatedSeconds: 0, message: "No verified safe step-free route currently exists.", operationalContextVersion: 3 } satisfies api.RouteResult;
    vi.mocked(api.setAssetStatus).mockResolvedValue(failedState);
    vi.mocked(api.fetchGoldenStepFreeRoute).mockResolvedValueOnce(normalRoute).mockResolvedValue(noRoute);
    render(<Home />);
    await screen.findByText("Normal route verified");
    await user.click(screen.getByRole("button", { name: "2 · Close Corridor W3" }));
    expect(await screen.findByText("No verified route")).toBeVisible();
    expect(screen.getByText("No verified safe step-free route currently exists.")).toBeVisible();
    expect(screen.getByText(/Do not publish route guidance/)).toBeVisible();
  });

  it("announces a loading state while data is pending", async () => {
    vi.mocked(api.fetchVenue).mockReturnValue(new Promise(() => undefined));
    render(<Home />);
    await screen.findByText("Local Demo Controller");
    expect(screen.getByRole("status")).toHaveTextContent("Loading validated stadium graph");
  });

  it("keeps report extraction advisory and requires approval before creating work", async () => {
    const user = userEvent.setup();
    const reports = [1, 2, 3].map((number) => ({
      id: `RPT-${number}`, rawText: `Synthetic report ${number}`, language: "en", source: "EVALUATOR_UI", synthetic: true,
      extraction: { category: "FACILITY_OUTAGE", summary: `Synthetic report ${number}`, candidateZoneIds: ["Z_L2_W"], candidateAssetIds: ["A_LIFT_2"], affectedGroups: [], observedSymptoms: [], urgencySuggestion: "HIGH", confidence: .86, unverifiedClaims: [`Synthetic report ${number}`], missingInformation: ["Controller verification"], clarificationQuestions: [], untrustedInstructionDetected: false, provider: "LOCAL_DEMO_PROVIDER" },
      relatedReportIds: [], matchCandidates: [], createdAt: "2026-07-15T00:00:00Z",
    })) satisfies api.VenueReport[];
    const proposed = {
      id: "INC-1", reportIds: ["RPT-1", "RPT-2"], status: "PLAN_PROPOSED", verifiedFacts: ["Lift L2 is OUT_OF_SERVICE"], unverifiedClaims: reports.map((report) => report.rawText),
      impact: { routeResult: { ...normalRoute, edgeIds: ["E_W3_FALLBACK_RAMP"], operationalContextVersion: 2 }, accessibilityConsequences: [], contextVersion: 2 },
      currentPlan: { id: "PLAN-1", operationalObjective: "Maintain verified step-free access.", actions: [{ actionType: "INSPECT_ASSET", title: "Inspect Lift L2", assignedTeam: "MAINTENANCE", locationId: "A_LIFT_2", rationale: "Verified outage" }], confidence: .86, contextVersion: 2, validity: "VALID", planSource: "LOCAL_DETERMINISTIC" },
      tasks: [], communications: [],
    } satisfies api.Incident;
    const approved = { ...proposed, status: "PLAN_APPROVED", tasks: [{ id: "TASK-1", title: "Inspect Lift L2", status: "CREATED", assignedTeam: "MAINTENANCE" }], communications: [{ id: "COM-1", language: "en", content: "Use the staffed fallback.", status: "DRAFT" }] } satisfies api.Incident;
    const reassessed = {
      ...approved,
      status: "PLAN_PROPOSED",
      impact: { ...approved.impact, routeResult: { ...normalRoute, found: false, nodeIds: [], edgeIds: [], message: "No verified safe step-free route currently exists.", operationalContextVersion: 3 }, contextVersion: 3 },
      currentPlan: { ...approved.currentPlan, validity: "UNSAFE" },
      proposedRevision: { id: "PLAN-2", operationalObjective: "Contain safely.", actions: [{ actionType: "ESTABLISH_WAITING_POINT", title: "Establish waiting point", assignedTeam: "ACCESSIBILITY_TEAM", locationId: "N_L2_WAIT_2", rationale: "No route" }], confidence: .8, contextVersion: 3, validity: "AWAITING_VERIFICATION", planSource: "LOCAL_DETERMINISTIC" },
      reassessment: { explanation: "The verified route is no longer feasible.", validity: "UNSAFE", requiresHumanReview: true },
      communications: [{ ...approved.communications[0], status: "SUPERSEDED" }],
    } satisfies api.Incident;
    vi.mocked(api.createReport).mockResolvedValueOnce(reports[0]).mockResolvedValueOnce(reports[1]).mockResolvedValueOnce(reports[2]);
    vi.mocked(api.createIncident).mockResolvedValue(proposed);
    vi.mocked(api.approveIncident).mockResolvedValue(approved);
    vi.mocked(api.reassessIncident).mockResolvedValue(reassessed);
    render(<Home />);
    await screen.findByText("Validated canonical graph");
    const loadScenario = screen.getByRole("button", { name: "Load 3-report scenario" });
    loadScenario.focus();
    expect(loadScenario).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findAllByText(/unverified claim/i)).toHaveLength(3);
    const confirmIncident = screen.getByRole("button", { name: "Confirm incident and analyse impact" });
    confirmIncident.focus();
    expect(confirmIncident).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("Fallback route verified")).toBeVisible();
    expect(screen.queryByText(/tasks ·/)).not.toBeInTheDocument();
    const approvePlan = screen.getByRole("button", { name: "Approve plan and create work" });
    approvePlan.focus();
    expect(approvePlan).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("✓ 1 tasks · 1 multilingual drafts")).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve plan and create work" })).toBeDisabled();
    const reassess = screen.getByRole("button", { name: "Close W3 and reassess" });
    reassess.focus();
    expect(reassess).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByText("NO VERIFIED STEP-FREE ROUTE")).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve containment revision" })).toBeEnabled();
  });

  it("shows the server-verified identity and complete operating areas", async () => {
    render(<Home />);
    expect(await screen.findByText("Local Demo Controller")).toBeVisible();
    expect(screen.getByText("CONTROLLER · disabled")).toBeVisible();
    const navigation = screen.getByRole("navigation", { name: "VenueSignal areas" });
    for (const area of ["Operations", "Reports", "Incidents", "Venue state", "Tasks", "Communications", "Scenarios", "Audit"]) {
      expect(within(navigation).getByRole("link", { name: area })).toBeVisible();
    }
  });

  it("previews evaluator uploads through the real import API", async () => {
    const user = userEvent.setup();
    vi.mocked(api.importReports).mockResolvedValue({ format: "CSV", rowsDetected: 1, validRows: 1, errors: [], reports: [], duplicateReportIds: [], importFingerprint: "abc" });
    render(<Home />);
    await screen.findByText("Validated canonical graph");
    const file = new File(["rawText,language\nLift L2 is stuck,en"], "reports.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("CSV or JSON evaluator import"), file);
    await user.click(screen.getByRole("button", { name: "Preview import" }));
    expect(await screen.findByText("1/1 valid · 0 duplicates · 0 errors")).toBeVisible();
    expect(api.importReports).toHaveBeenCalledWith(file, false);
  });

  it("exposes validated task, communication, and audit lifecycle controls", async () => {
    const user = userEvent.setup();
    const task = { id: "TSK-1", title: "Inspect Lift L2", status: "CREATED", assignedTeam: "MAINTENANCE" } satisfies api.WorkflowTask;
    const communication = { id: "COM-1", language: "en", content: "Use staffed route.", status: "DRAFT" } satisfies api.Communication;
    vi.mocked(api.fetchTasks).mockResolvedValue([task]);
    vi.mocked(api.fetchCommunications).mockResolvedValue([communication]);
    vi.mocked(api.fetchAudit).mockResolvedValue([{ id: "AUD-1", eventType: "PLAN_APPROVED", summary: "Plan approved by controller.", contextVersion: 2, occurredAt: "2026-07-17T00:00:00Z", actor: "Controller" }]);
    vi.mocked(api.updateTask).mockResolvedValue({ ...task, status: "ASSIGNED" });
    vi.mocked(api.updateCommunication).mockResolvedValue({ ...communication, status: "UNDER_REVIEW" });
    render(<Home />);
    const taskButton = await screen.findByRole("button", { name: "Move to ASSIGNED" });
    expect(screen.getByText("Plan approved by controller.")).toBeVisible();
    await user.click(taskButton);
    expect(api.updateTask).toHaveBeenCalledWith("TSK-1", "ASSIGNED", undefined);
    await user.click(screen.getByRole("button", { name: "Move to UNDER REVIEW" }));
    expect(api.updateCommunication).toHaveBeenCalledWith("COM-1", "UNDER_REVIEW");
  });

  it("shows repaired containment as non-actionable until one human approval", async () => {
    const user = userEvent.setup();
    const noRoute = { ...normalRoute, found: false, nodeIds: [], edgeIds: [], message: "No verified safe step-free route currently exists.", operationalContextVersion: 4 } satisfies api.RouteResult;
    const reassessed = {
      id: "INC-REPAIR", reportIds: ["RPT-1"], status: "PLAN_PROPOSED",
      verifiedFacts: ["Lift L2 is OUT_OF_SERVICE"], unverifiedClaims: ["Corridor W3 is closed"],
      impact: { routeResult: noRoute, accessibilityConsequences: ["No verified safe step-free route remains"], contextVersion: 4 },
      currentPlan: { id: "PLAN-OLD", operationalObjective: "Use W3.", actions: [{ actionType: "STAFF_VERIFIED_ROUTE", title: "Staff W3", assignedTeam: "VENUE_OPERATIONS", locationId: "A_CORRIDOR_W3", rationale: "Previously valid" }], confidence: .8, contextVersion: 2, validity: "UNSAFE", planSource: "GEMINI" },
      proposedRevision: { id: "PLAN-SAFE", operationalObjective: "Contain safely.", actions: [{ actionType: "ESTABLISH_WAITING_POINT", title: "Keep spectators at the staffed waiting point", assignedTeam: "ACCESSIBILITY_TEAM", locationId: "N_L2_WAIT_2", rationale: "No route" }], confidence: 1, contextVersion: 4, validity: "AWAITING_VERIFICATION", planSource: "DETERMINISTIC_CONTAINMENT" },
      reassessment: { explanation: "The old route is no longer feasible.", validity: "UNSAFE", requiresHumanReview: true },
      planRecoveryRecords: [{ validationErrors: [{ code: "NO_VERIFIED_ROUTE", message: "A route action cannot be approved when no verified route exists" }], repairValidationErrors: [], fallbackUsed: true }],
      tasks: [{ id: "TSK-OLD", title: "Old task", status: "CREATED", assignedTeam: "VENUE_OPERATIONS" }],
      communications: [{ id: "COM-OLD", language: "en", content: "Old route guidance", status: "SUPERSEDED" }],
    } satisfies api.Incident;
    const approved = {
      ...reassessed,
      status: "MONITORING",
      currentPlan: reassessed.proposedRevision,
      proposedRevision: undefined,
      reassessment: undefined,
      tasks: [...reassessed.tasks, { id: "TSK-NEW", title: "Contain spectators", status: "CREATED", assignedTeam: "ACCESSIBILITY_TEAM" }],
    } satisfies api.Incident;
    vi.mocked(api.fetchIncidents).mockResolvedValue([reassessed]);
    vi.mocked(api.fetchTasks).mockResolvedValue(reassessed.tasks);
    vi.mocked(api.fetchCommunications).mockResolvedValue(reassessed.communications);
    vi.mocked(api.approveIncident).mockResolvedValue(approved);

    render(<Home />);
    expect(await screen.findByText("DETERMINISTIC CONTAINMENT")).toBeVisible();
    expect(screen.getAllByText("No verified safe step-free route currently exists.").length).toBeGreaterThan(0);
    expect(screen.getByText("No route communication will be generated. Approval creates containment tasks only.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Approve plan and create work" })).toBeDisabled();

    const approval = screen.getByRole("button", { name: "Approve containment revision" });
    await user.dblClick(approval);
    expect(api.approveIncident).toHaveBeenCalledTimes(1);
    expect(api.approveIncident).toHaveBeenCalledWith("INC-REPAIR", true);
  });

  it("makes every consequential control read-only for a verified viewer", async () => {
    vi.mocked(api.fetchPrincipal).mockResolvedValue({ uid: "viewer", displayName: "Venue Observer", role: "VIEWER", authMode: "firebase" });
    render(<Home />);
    expect(await screen.findByText("Venue Observer")).toBeVisible();
    expect(await screen.findByRole("status", { name: "" })).toHaveTextContent("Viewer access is read-only");
    expect(screen.getByRole("button", { name: "1 · Set Lift L2 out of service" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Extract report" })).toBeDisabled();
    expect(screen.getByLabelText("CSV or JSON evaluator import")).toBeDisabled();
  });
});
