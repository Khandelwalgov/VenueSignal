"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AuthPanel from "@/components/AuthPanel";
import DetailsPanel from "@/components/DetailsPanel";
import IncidentWorkflow, { WorkflowSummary } from "@/components/IncidentWorkflow";
import MapDisplay from "@/components/MapDisplay";
import Tutorial, { TUTORIAL_STORAGE_KEY } from "@/components/Tutorial";
import {
  AccessibilitySummary,
  AssetStatus,
  fetchAccessibilitySummary,
  fetchGoldenStepFreeRoute,
  fetchLevel,
  fetchOperationalState,
  fetchValidation,
  fetchVenue,
  LevelData,
  OperationalState,
  Principal,
  resetOperationalState,
  RouteResult,
  setAssetStatus,
  ValidationResult,
  VenueMetadata,
} from "@/lib/api";

const VENUE_ID = "unity-stadium";

export default function Home() {
  const [venue, setVenue] = useState<VenueMetadata | null>(null);
  const [levelData, setLevelData] = useState<LevelData | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [accessibility, setAccessibility] = useState<AccessibilitySummary | null>(null);
  const [operationalState, setOperationalState] = useState<OperationalState | null>(null);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [activeLevelId, setActiveLevelId] = useState("L0");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [assetType, setAssetType] = useState("ALL");
  const [showGraphDetails, setShowGraphDetails] = useState(false);
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [principal, setPrincipal] = useState<Principal | null>(null);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [startDemoSignal, setStartDemoSignal] = useState(0);
  const [workflowSummary, setWorkflowSummary] = useState<WorkflowSummary>({ incident: null, reports: 0, tasks: 0, communications: 0 });

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      try {
        if (window.localStorage.getItem(TUTORIAL_STORAGE_KEY) !== "true") setTutorialOpen(true);
      } catch { setTutorialOpen(true); }
    }, 0);
    return () => window.clearTimeout(timeout);
  }, []);

  useEffect(() => {
    if (!principal) return;
    let cancelled = false;
    async function loadWorkspace() {
      setLoading(true);
      try {
        const [venueResponse, levelResponse, validationResponse, accessibilityResponse, stateResponse, routeResponse] =
          await Promise.all([
            fetchVenue(VENUE_ID),
            fetchLevel(VENUE_ID, activeLevelId),
            fetchValidation(VENUE_ID),
            fetchAccessibilitySummary(VENUE_ID),
            fetchOperationalState(),
            fetchGoldenStepFreeRoute(),
          ]);
        if (cancelled) return;
        setVenue(venueResponse);
        setLevelData(levelResponse);
        setValidation(validationResponse);
        setAccessibility(accessibilityResponse);
        setOperationalState(stateResponse);
        setRoute(routeResponse);
        setError(null);
      } catch (requestError: unknown) {
        if (cancelled) return;
        setError(requestError instanceof Error ? requestError.message : "Venue data is unavailable.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadWorkspace();
    return () => { cancelled = true; };
  }, [activeLevelId, principal]);

  const readOnly = principal?.role !== "CONTROLLER";
  const incident = workflowSummary.incident;
  const awaitingApproval = Boolean(incident && (incident.proposedRevision || (!incident.currentPlan.approvedAt && !incident.tasks.length)));

  const assetTypes = useMemo(
    () => Array.from(new Set(levelData?.assets.map((asset) => asset.type) ?? [])).sort(),
    [levelData],
  );

  const effectiveLevelData = useMemo(() => {
    if (!levelData || !operationalState) return levelData;
    return {
      ...levelData,
      assets: levelData.assets.map((asset) => ({ ...asset, status: operationalState.assetStatusOverrides[asset.id] ?? asset.status })),
      edges: levelData.edges.map((edge) => ({
        ...edge,
        status: operationalState.edgeStatusOverrides[edge.id] ?? edge.status,
        currentCrowdPercent: operationalState.edgeCrowdOverrides[edge.id] ?? edge.currentCrowdPercent,
      })),
    };
  }, [levelData, operationalState]);

  const visibleAssets = useMemo(
    () => effectiveLevelData?.assets.filter((asset) => assetType === "ALL" || asset.type === assetType) ?? [],
    [assetType, effectiveLevelData],
  );

  const currentAccessibilityChecks = useMemo(() => {
    if (!levelData || !accessibility) return [];
    const nodeIds = new Set(levelData.nodes.map((node) => node.id));
    return accessibility.checks.filter((check) => nodeIds.has(check.destinationNodeId));
  }, [accessibility, levelData]);

  const updateWorkflowSummary = useCallback((summary: WorkflowSummary) => setWorkflowSummary(summary), []);

  function changeLevel(levelId: string) {
    setActiveLevelId(levelId);
    setSelectedEntityId(null);
    setAssetType("ALL");
  }

  function startGuidedDemo() {
    setTutorialOpen(false);
    setStartDemoSignal((current) => current + 1);
  }

  async function applyAssetOverride(assetId: string, status: AssetStatus) {
    setMutating(true);
    try {
      const state = await setAssetStatus(assetId, status);
      const nextRoute = await fetchGoldenStepFreeRoute();
      setOperationalState(state);
      setRoute(nextRoute);
      setError(null);
    } catch (mutationError: unknown) {
      setError(mutationError instanceof Error ? mutationError.message : "Operational update failed.");
    } finally { setMutating(false); }
  }

  async function resetScenario() {
    setMutating(true);
    try {
      const state = await resetOperationalState();
      const nextRoute = await fetchGoldenStepFreeRoute();
      setOperationalState(state);
      setRoute(nextRoute);
      setError(null);
    } catch (mutationError: unknown) {
      setError(mutationError instanceof Error ? mutationError.message : "Operational reset failed.");
    } finally { setMutating(false); }
  }

  async function refreshOperationalView() {
    const [state, nextRoute] = await Promise.all([fetchOperationalState(), fetchGoldenStepFreeRoute()]);
    setOperationalState(state);
    setRoute(nextRoute);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <div className="brand-row"><span className="brand-mark" aria-hidden="true">V</span><h1>VenueSignal</h1><span className="synthetic-badge">Synthetic venue</span></div>
          <p>Unity Stadium operations command centre</p>
        </div>
        {principal && <div className="topbar-actions">
          <button type="button" className="tutorial-button" aria-haspopup="dialog" onClick={() => setTutorialOpen(true)}><span aria-hidden="true">?</span> Tutorial</button>
          <div className="venue-health" aria-label={`Unity Stadium status ${venue?.status ?? "loading"}`}><span className="pulse-dot" aria-hidden="true" /><span><strong>Venue online</strong><small>{venue?.status ?? "Loading"}</small></span></div>
          <AuthPanel onPrincipal={setPrincipal} />
        </div>}
      </header>

      {principal && <nav className="area-nav" aria-label="VenueSignal areas">
        <a href="#operations" aria-current="page">Operations</a>
        <a href="#incidents">Incidents</a>
        <a href="#tasks">Tasks</a>
        <a href="#communications">Communications</a>
        <details className="nav-more"><summary>More</summary><div><a href="#reports">Reports</a><a href="#system-details">Venue state</a><a href="#audit">Audit</a><a href="#system-details">System information</a></div></details>
      </nav>}

      <Tutorial open={Boolean(principal) && tutorialOpen} onClose={() => setTutorialOpen(false)} onStartDemo={startGuidedDemo} />

      {!principal ? (
        <main id="main-content" className="auth-gate" tabIndex={-1}>
          <AuthPanel onPrincipal={setPrincipal} />
        </main>
      ) : error ? (
        <main id="main-content" className="error-state" role="alert" tabIndex={-1}>
          <span aria-hidden="true">!</span><div><h2>Venue data could not be loaded</h2><p>{error}</p><p>Confirm that the VenueSignal API is running and try again.</p></div>
        </main>
      ) : (
        <main id="main-content" className="workspace" aria-busy={loading} tabIndex={-1}>
          <section id="operations" className="operations-overview" data-tour="overview">
            <div className="hero-copy">
              <span className="eyebrow">VenueSignal</span>
              <h2>AI-assisted incident intelligence for stadium operations.</h2>
              <p>AI proposes. Deterministic logic verifies. Humans decide.</p>
              <div className="hero-actions">
                <button type="button" className="primary-button" disabled={readOnly} onClick={startGuidedDemo}>Start Guided Demo <span aria-hidden="true">→</span></button>
                <a className="secondary-button" href="#stadium-map">Explore Dashboard</a>
                <button type="button" className="text-button" aria-haspopup="dialog" onClick={() => setTutorialOpen(true)}>Quick Tour</button>
              </div>
            </div>
            <div className="responsibility-key" aria-label="VenueSignal responsibility model">
              <span className="signal-badge signal-ai"><i aria-hidden="true">✦</i> AI insight</span>
              <span className="signal-badge signal-evidence"><i aria-hidden="true">?</i> Unverified evidence</span>
              <span className="signal-badge signal-deterministic"><i aria-hidden="true">◆</i> Deterministic validation</span>
              <span className="signal-badge signal-human"><i aria-hidden="true">●</i> Human decision</span>
            </div>
          </section>

          <section className="status-summary" aria-label="Operations status summary">
            <article><span>Venue status</span><strong>{route?.found ? "Operational" : "Restricted"}</strong><small>{validation?.valid ? "Systems operational" : "Validation attention required"}</small></article>
            <article><span>Active incidents</span><strong>{incident && !["RESOLVED", "REJECTED"].includes(incident.status) ? 1 : 0}</strong><small>{incident ? "Accessibility response" : "No unresolved incidents"}</small></article>
            <article className={awaitingApproval ? "needs-attention" : ""}><span>Awaiting approval</span><strong>{awaitingApproval ? 1 : 0}</strong><small>{awaitingApproval ? "Controller decision required" : "No decisions waiting"}</small></article>
            <article className={route?.found ? "" : "is-danger"}><span>Accessibility disruptions</span><strong>{route?.found ? 0 : 1}</strong><small>{route?.found ? "No verified disruption" : "Containment required"}</small></article>
          </section>

          <div className="operations-layout">
            <section id="stadium-map" className="map-workspace" aria-labelledby="map-workspace-title" data-tour="map">
              <div className="map-toolbar">
                <div><span className="eyebrow">Unity Stadium</span><h2 id="map-workspace-title">{levelData?.level.label ?? "Loading stadium"}</h2></div>
                <div className="map-toolbar-actions">
                  <div className="segmented-control" aria-label="Select stadium level">
                    {["L0", "L1", "L2"].map((levelId) => <button key={levelId} type="button" aria-label={`Level ${levelId.slice(1)}, ${levelId === "L0" ? "Entry" : levelId === "L1" ? "Lower" : "Upper"} concourse`} aria-pressed={activeLevelId === levelId} onClick={() => changeLevel(levelId)}><strong>{levelId}</strong><span>{levelId === "L0" ? "Entry" : levelId === "L1" ? "Lower" : "Upper"}</span></button>)}
                  </div>
                  <button type="button" className="graph-toggle" aria-pressed={showGraphDetails} onClick={() => setShowGraphDetails((current) => !current)}>{showGraphDetails ? "Hide graph details" : "Show graph details"}</button>
                </div>
              </div>
              <div className="map-frame">
                {loading && !levelData ? <div className="loading-state" role="status"><span className="loader" aria-hidden="true" />Loading validated stadium map…</div> : effectiveLevelData ? <MapDisplay levelData={effectiveLevelData} selectedEntityId={selectedEntityId} visibleAssetIds={visibleAssets.map((asset) => asset.id)} routeEdgeIds={route?.edgeIds ?? []} showGraphDetails={showGraphDetails} onSelectEntity={setSelectedEntityId} /> : null}
              </div>
              <div className="map-key" aria-label="Map legend"><span><i className="legend-line route" /> Verified route</span><span><i className="legend-critical" /> Accessibility-critical</span><span><i className="legend-line closed" /> Closed</span></div>
            </section>

            <aside className={`situation-panel ${!route?.found ? "no-route" : ""}`} aria-labelledby="situation-title">
              {!incident ? (
                <>
                  <div className="situation-status"><span aria-hidden="true">✓</span><div><span>Current situation</span><h2 id="situation-title">All systems operational</h2></div></div>
                  <p>No active incidents require controller attention.</p>
                  <ul className="operational-checks"><li><span aria-hidden="true">✓</span> Accessible routes verified</li><li><span aria-hidden="true">✓</span> Critical facilities operational</li><li><span aria-hidden="true">✓</span> No unresolved incidents</li></ul>
                  <button type="button" className="primary-button empty-demo-cta" disabled={readOnly} onClick={startGuidedDemo}>Start Guided Demo <span aria-hidden="true">→</span></button>
                  <small className="empty-demo-note">Run the six-step synthetic stadium scenario to see VenueSignal handle a live accessibility disruption.</small>
                </>
              ) : !route?.found ? (
                <>
                  <div className="situation-status danger"><span aria-hidden="true">!</span><div><span>Accessibility disruption</span><h2 id="situation-title">No verified safe step-free route</h2></div></div>
                  <p>Lift L2 and Corridor W3 are unavailable. VenueSignal will not issue positive route guidance.</p>
                  <div className="no-guidance-mini"><strong>Safe containment</strong><span>Human approval required</span></div>
                  <a className="primary-link" href="#incidents">Review containment plan →</a>
                </>
              ) : (
                <>
                  <span className="priority-badge">High priority</span>
                  <div className="situation-status warning"><span aria-hidden="true">!</span><div><span>Current situation</span><h2 id="situation-title">Lift L2 accessibility disruption</h2></div></div>
                  <p>Lift L2 is confirmed unavailable. Accessible access to Sections 209–218 is affected.</p>
                  <dl className="situation-facts"><div><dt>Verified route</dt><dd>{route.edgeIds.includes("E_W3_FALLBACK_RAMP") ? "W3 fallback" : "Normal path"}</dd></div><div><dt>Distance</dt><dd>{Math.round(route.distanceMeters)} m</dd></div><div><dt>Next action</dt><dd>{awaitingApproval ? "Review plan" : "Monitor response"}</dd></div></dl>
                  <a className="primary-link" href="#incidents">Open incident workspace →</a>
                </>
              )}
            </aside>
          </div>

          <details id="system-details" className="system-details">
            <summary><span><b>Venue and system details</b><small>Facilities, zones, validation, accessibility checks, and evaluator controls</small></span><span aria-hidden="true">＋</span></summary>
            <div className="system-details-grid">
              <section><div className="section-heading"><div><span className="eyebrow">Current level</span><h3>Zones and facilities</h3></div></div><label className="filter-label" htmlFor="asset-filter">Facility filter</label><select id="asset-filter" value={assetType} onChange={(event) => setAssetType(event.target.value)}><option value="ALL">All facility types</option>{assetTypes.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}</select><div className="entity-columns"><div className="entity-list" role="group" aria-label="Zones on current level">{levelData?.zones.map((zone) => <button type="button" key={zone.id} className={selectedEntityId === zone.id ? "selected" : ""} onClick={() => setSelectedEntityId(zone.id)}><span><strong>{zone.label}</strong><small>{zone.type.toLowerCase()} · {zone.occupancyPercent}% synthetic occupancy</small></span><span className="status-symbol" aria-label={zone.status}>{zone.status === "NORMAL" ? "✓" : "!"}</span></button>)}</div><div className="entity-list" role="group" aria-label="Facilities on current level">{visibleAssets.map((asset) => <button type="button" key={asset.id} className={selectedEntityId === asset.id ? "selected" : ""} onClick={() => setSelectedEntityId(asset.id)}><span><strong>{asset.label}</strong><small>{asset.type.replaceAll("_", " ")}{asset.accessibilityCritical ? " · accessibility-critical" : ""}</small></span><span className="status-symbol" aria-label={asset.status}>✓</span></button>)}</div></div></section>
              <section><DetailsPanel entityId={selectedEntityId} levelData={effectiveLevelData} /><div className="validation-callout"><span aria-hidden="true">✓</span><div><strong>{validation?.valid ? "Validated safety graph" : "Graph requires attention"}</strong><small>{validation?.errors.length ?? 0} errors · {validation?.warnings.length ?? 0} warnings</small></div></div><details className="technical-details"><summary>Technical graph and system details</summary><dl className="stat-grid"><div><dt>Nodes</dt><dd>{venue?.statistics.nodes ?? "—"}</dd></div><div><dt>Edges</dt><dd>{venue?.statistics.edges ?? "—"}</dd></div><div><dt>Assets</dt><dd>{venue?.statistics.assets ?? "—"}</dd></div><div><dt>Components</dt><dd>{venue?.statistics.connectedComponents ?? "—"}</dd></div><div><dt>State version</dt><dd>{operationalState?.contextVersion ?? "—"}</dd></div><div><dt>Auth mode</dt><dd>{principal.authMode}</dd></div></dl></details></section>
              <section><div className="section-heading"><div><span className="eyebrow">Accessibility</span><h3>Step-free destinations</h3></div></div><ul className="check-list">{currentAccessibilityChecks.map((check) => <li key={check.destinationNodeId}><span>{check.destinationLabel}</span><strong className={check.reachableStepFree ? "yes" : "no"}>{check.reachableStepFree ? "✓ Available" : "× Not verified"}</strong></li>)}</ul><details className="scenario-controls"><summary>Evaluator scenario controls</summary><p>These controls write real operational overlay events.</p><button type="button" disabled={mutating || readOnly} onClick={() => applyAssetOverride("A_LIFT_2", "OUT_OF_SERVICE")}>1 · Set Lift L2 out of service</button><button type="button" disabled={mutating || readOnly} onClick={() => applyAssetOverride("A_CORRIDOR_W3", "OUT_OF_SERVICE")}>2 · Close Corridor W3</button><button type="button" disabled={mutating || readOnly} onClick={resetScenario}>Reset canonical base state</button></details></section>
            </div>
          </details>

          <IncidentWorkflow onOperationalChange={refreshOperationalView} onSummaryChange={updateWorkflowSummary} readOnly={readOnly} startDemoSignal={startDemoSignal} />
        </main>
      )}

      <footer className="disclosure"><strong>Unity Stadium is synthetic.</strong> It demonstrates incident reasoning, accessibility-impact analysis, and constrained route recovery. It is not an official venue map; all geometry, crowd values, asset states, and operational events are synthetic or evaluator-supplied.</footer>
    </div>
  );
}
