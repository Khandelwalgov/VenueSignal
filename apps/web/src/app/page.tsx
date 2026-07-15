"use client";

import { useEffect, useMemo, useState } from "react";

import DetailsPanel from "@/components/DetailsPanel";
import IncidentWorkflow from "@/components/IncidentWorkflow";
import MapDisplay from "@/components/MapDisplay";
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
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
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
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Venue data is unavailable.",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [activeLevelId]);

  const assetTypes = useMemo(
    () => Array.from(new Set(levelData?.assets.map((asset) => asset.type) ?? [])).sort(),
    [levelData],
  );
  const effectiveLevelData = useMemo(() => {
    if (!levelData || !operationalState) return levelData;
    return {
      ...levelData,
      assets: levelData.assets.map((asset) => ({
        ...asset,
        status: operationalState.assetStatusOverrides[asset.id] ?? asset.status,
      })),
      edges: levelData.edges.map((edge) => ({
        ...edge,
        status: operationalState.edgeStatusOverrides[edge.id] ?? edge.status,
        currentCrowdPercent: operationalState.edgeCrowdOverrides[edge.id] ?? edge.currentCrowdPercent,
      })),
    };
  }, [levelData, operationalState]);
  const visibleAssets = useMemo(
    () =>
      effectiveLevelData?.assets.filter(
        (asset) => assetType === "ALL" || asset.type === assetType,
      ) ?? [],
    [assetType, effectiveLevelData],
  );
  const currentAccessibilityChecks = useMemo(() => {
    if (!levelData || !accessibility) return [];
    const nodeIds = new Set(levelData.nodes.map((node) => node.id));
    return accessibility.checks.filter((check) =>
      nodeIds.has(check.destinationNodeId),
    );
  }, [accessibility, levelData]);

  function changeLevel(levelId: string) {
    setActiveLevelId(levelId);
    setSelectedEntityId(null);
    setAssetType("ALL");
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
    } finally {
      setMutating(false);
    }
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
    } finally {
      setMutating(false);
    }
  }

  async function refreshOperationalView() {
    const [state, nextRoute] = await Promise.all([fetchOperationalState(), fetchGoldenStepFreeRoute()]);
    setOperationalState(state);
    setRoute(nextRoute);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <div className="brand-row">
            <h1>VenueSignal</h1>
            <span className="synthetic-badge">◇ Synthetic venue</span>
          </div>
          <p>Deterministic venue-state and accessibility inspection</p>
        </div>
        <div className="venue-health" aria-label={`Unity Stadium status ${venue?.status ?? "loading"}`}>
          <span className="pulse-dot" aria-hidden="true" />
          <span><strong>Unity Stadium</strong><small>{venue?.status ?? "Loading venue"}</small></span>
        </div>
      </header>

      <div className="prototype-banner">
        <strong>Implemented now:</strong> validated venue graph, versioned operational
        overlays, deterministic constrained routing, human-verified incident plans,
        multilingual draft generation, and live plan reassessment.
      </div>

      {error ? (
        <main id="main-content" className="error-state" role="alert">
          <span aria-hidden="true">!</span>
          <div>
            <h2>Venue data could not be loaded</h2>
            <p>{error}</p>
            <p>Confirm that the VenueSignal API is running and try again.</p>
          </div>
        </main>
      ) : (
        <main id="main-content" className="workspace" aria-busy={loading}>
          <aside className="control-rail" aria-label="Venue controls">
            <section>
              <div className="section-heading">
                <div><span className="eyebrow">Venue view</span><h2>Levels</h2></div>
                <span className="count-pill">3</span>
              </div>
              <div className="segmented-control" aria-label="Select stadium level">
                {["L0", "L1", "L2"].map((levelId) => (
                  <button
                    key={levelId}
                    type="button"
                    aria-label={`Level ${levelId.slice(1)}, ${levelId === "L0" ? "Entry" : levelId === "L1" ? "Lower" : "Upper"} concourse`}
                    aria-pressed={activeLevelId === levelId}
                    onClick={() => changeLevel(levelId)}
                  >
                    <strong>{levelId}</strong>
                    <span>{levelId === "L0" ? "Entry" : levelId === "L1" ? "Lower" : "Upper"}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="scenario-controls" aria-labelledby="scenario-title">
              <div className="section-heading"><div><span className="eyebrow">Synthetic evaluator controls</span><h2 id="scenario-title">Golden route state</h2></div><span className="count-pill">v{operationalState?.contextVersion ?? "—"}</span></div>
              <p className="muted">Each action writes a real operational overlay event and reruns deterministic route validation.</p>
              <div className="scenario-buttons">
                <button type="button" disabled={mutating} onClick={() => applyAssetOverride("A_LIFT_2", "OUT_OF_SERVICE")}>1 · Set Lift L2 out of service</button>
                <button type="button" disabled={mutating} onClick={() => applyAssetOverride("A_CORRIDOR_W3", "OUT_OF_SERVICE")}>2 · Close Corridor W3</button>
                <button type="button" disabled={mutating} onClick={resetScenario}>Reset canonical base state</button>
              </div>
            </section>

            <section>
              <div className="section-heading"><div><span className="eyebrow">Structured controls</span><h2>Zones</h2></div></div>
              <div className="entity-list" role="group" aria-label="Zones on current level">
                {levelData?.zones.map((zone) => (
                  <button
                    type="button"
                    key={zone.id}
                    className={selectedEntityId === zone.id ? "selected" : ""}
                    onClick={() => setSelectedEntityId(zone.id)}
                  >
                    <span><strong>{zone.label}</strong><small>{zone.type.toLowerCase()} · {zone.occupancyPercent}% synthetic occupancy</small></span>
                    <span className="status-symbol" aria-label={zone.status}>{zone.status === "NORMAL" ? "✓" : "!"}</span>
                  </button>
                ))}
              </div>
            </section>

            <section>
              <label className="filter-label" htmlFor="asset-filter">Facility filter</label>
              <select id="asset-filter" value={assetType} onChange={(event) => setAssetType(event.target.value)}>
                <option value="ALL">All facility types</option>
                {assetTypes.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}
              </select>
              <div className="entity-list asset-list" role="group" aria-label="Facilities on current level">
                {visibleAssets.map((asset) => (
                  <button
                    type="button"
                    key={asset.id}
                    className={selectedEntityId === asset.id ? "selected" : ""}
                    onClick={() => setSelectedEntityId(asset.id)}
                  >
                    <span><strong>{asset.label}</strong><small>{asset.type.replaceAll("_", " ")}{asset.accessibilityCritical ? " · accessibility-critical" : ""}</small></span>
                    <span className="status-symbol" aria-label={asset.status}>✓</span>
                  </button>
                ))}
              </div>
            </section>
          </aside>

          <section className="map-workspace" aria-labelledby="map-workspace-title">
            <div className="map-toolbar">
              <div><span className="eyebrow">Live canonical definition</span><h2 id="map-workspace-title">{levelData?.level.label ?? "Loading level"}</h2></div>
              <div className="map-key" aria-label="Map legend">
                <span><i className="legend-line open" /> ✓ Open</span>
                <span><i className="legend-line restricted" /> ! Restricted</span>
                <span><i className="legend-line closed" /> × Closed</span>
                <span><i className="legend-critical" /> Accessibility-critical</span>
              </div>
            </div>
            <div className="map-frame">
              {loading && !levelData ? (
                <div className="loading-state" role="status"><span className="loader" aria-hidden="true" />Loading validated stadium graph…</div>
              ) : effectiveLevelData ? (
                <MapDisplay
                  levelData={effectiveLevelData}
                  selectedEntityId={selectedEntityId}
                  visibleAssetIds={visibleAssets.map((asset) => asset.id)}
                  routeEdgeIds={route?.edgeIds ?? []}
                  onSelectEntity={setSelectedEntityId}
                />
              ) : null}
            </div>
            <div className="map-caption">
              <span>Visual geometry is synthetic presentation.</span>
              <strong>The machine-readable graph remains operational truth.</strong>
            </div>
          </section>

          <aside className="intelligence-rail">
            <DetailsPanel entityId={selectedEntityId} levelData={effectiveLevelData} />

            <section className="insight-card" aria-labelledby="route-title" aria-live="polite">
              <div className="section-heading"><div><span className="eyebrow">Context v{route?.operationalContextVersion ?? "—"}</span><h2 id="route-title">Sections 209–218 step-free route</h2></div></div>
              <div className={`route-callout ${route?.found ? "available" : "unavailable"}`}>
                <span aria-hidden="true">{route?.found ? "✓" : "×"}</span>
                <div>
                  <strong>{route?.found ? (route.edgeIds.includes("E_W3_FALLBACK_RAMP") ? "W3 fallback verified" : "Normal route verified") : "No verified route"}</strong>
                  <small>{route?.message ?? "Evaluating current operational context…"}</small>
                </div>
              </div>
              {route?.found && <p className="route-metrics">{Math.round(route.distanceMeters)} m · {Math.round(route.estimatedSeconds / 60)} min · public step-free path</p>}
              {!route?.found && <p className="containment-copy">Do not publish route guidance. Dispatch accessibility assistance, establish a staffed waiting point, and verify alternate conditions.</p>}
            </section>

            <section className="insight-card" aria-labelledby="validation-title">
              <div className="section-heading"><div><span className="eyebrow">Integrity gate</span><h2 id="validation-title">Graph validation</h2></div></div>
              <div className={`validation-callout ${validation?.valid ? "valid" : "invalid"}`}>
                <span aria-hidden="true">{validation?.valid ? "✓" : "×"}</span>
                <div><strong>{validation?.valid ? "Validated canonical graph" : "Graph requires attention"}</strong><small>{validation?.errors.length ?? 0} errors · {validation?.warnings.length ?? 0} warnings</small></div>
              </div>
              <dl className="stat-grid">
                <div><dt>Nodes</dt><dd>{venue?.statistics.nodes ?? "—"}</dd></div>
                <div><dt>Edges</dt><dd>{venue?.statistics.edges ?? "—"}</dd></div>
                <div><dt>Assets</dt><dd>{venue?.statistics.assets ?? "—"}</dd></div>
                <div><dt>Components</dt><dd>{venue?.statistics.connectedComponents ?? "—"}</dd></div>
                <div><dt>Isolated</dt><dd>{venue?.statistics.isolatedNodes ?? "—"}</dd></div>
                <div><dt>Step-free edges</dt><dd>{venue?.statistics.stepFreeEdges ?? "—"}</dd></div>
              </dl>
            </section>

            <section className="insight-card" aria-labelledby="accessibility-title">
              <div className="section-heading"><div><span className="eyebrow">Deterministic check</span><h2 id="accessibility-title">Step-free availability</h2></div></div>
              <p className="summary-line"><span aria-hidden="true">♿</span><strong>From West Accessible Entrance</strong></p>
              <ul className="check-list">
                {currentAccessibilityChecks.map((check) => (
                  <li key={check.destinationNodeId}>
                    <span>{check.destinationLabel}</span>
                    <strong className={check.reachableStepFree ? "yes" : "no"}>{check.reachableStepFree ? "✓ Available" : "× Not verified"}</strong>
                  </li>
                ))}
              </ul>
              {currentAccessibilityChecks.length === 0 && <p className="muted">No designated accessibility destinations on this level.</p>}
            </section>
          </aside>
          <IncidentWorkflow onOperationalChange={refreshOperationalView} />
        </main>
      )}

      <footer className="disclosure">
        <strong>Unity Stadium is synthetic.</strong> It was created to demonstrate
        operational incident reasoning, accessibility-impact analysis, and constrained
        route recovery. It is not an official FIFA venue map. All geometry, crowd
        telemetry, asset status, and operational events are synthetic or evaluator-supplied.
      </footer>
    </div>
  );
}
