"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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

export function useVenueOperations(principal: Principal | null) {
  const [venue, setVenue] = useState<VenueMetadata | null>(null);
  const [levelData, setLevelData] = useState<LevelData | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [accessibility, setAccessibility] = useState<AccessibilitySummary | null>(null);
  const [operationalState, setOperationalState] = useState<OperationalState | null>(null);
  const [route, setRoute] = useState<RouteResult | null>(null);
  const [activeLevelId, setActiveLevelId] = useState("L0");
  const [loading, setLoading] = useState(true);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!principal) return;
    let cancelled = false;
    async function loadWorkspace() {
      setLoading(true);
      try {
        const responses = await Promise.all([
          fetchVenue(VENUE_ID),
          fetchLevel(VENUE_ID, activeLevelId),
          fetchValidation(VENUE_ID),
          fetchAccessibilitySummary(VENUE_ID),
          fetchOperationalState(),
          fetchGoldenStepFreeRoute(),
        ]);
        if (cancelled) return;
        const [
          venueResponse,
          levelResponse,
          validationResponse,
          accessibilityResponse,
          stateResponse,
          routeResponse,
        ] = responses;
        setVenue(venueResponse);
        setLevelData(levelResponse);
        setValidation(validationResponse);
        setAccessibility(accessibilityResponse);
        setOperationalState(stateResponse);
        setRoute(routeResponse);
        setError(null);
      } catch (requestError: unknown) {
        if (!cancelled) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Venue data is unavailable.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void loadWorkspace();
    return () => { cancelled = true; };
  }, [activeLevelId, principal]);

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
        currentCrowdPercent:
          operationalState.edgeCrowdOverrides[edge.id] ?? edge.currentCrowdPercent,
      })),
    };
  }, [levelData, operationalState]);

  const currentAccessibilityChecks = useMemo(() => {
    if (!levelData || !accessibility) return [];
    const nodeIds = new Set(levelData.nodes.map((node) => node.id));
    return accessibility.checks.filter((check) =>
      nodeIds.has(check.destinationNodeId)
    );
  }, [accessibility, levelData]);

  const refreshOperationalView = useCallback(async () => {
    const [state, nextRoute] = await Promise.all([
      fetchOperationalState(),
      fetchGoldenStepFreeRoute(),
    ]);
    setOperationalState(state);
    setRoute(nextRoute);
  }, []);

  const applyAssetOverride = useCallback(
    async (assetId: string, status: AssetStatus) => {
      setMutating(true);
      try {
        const state = await setAssetStatus(assetId, status);
        const nextRoute = await fetchGoldenStepFreeRoute();
        setOperationalState(state);
        setRoute(nextRoute);
        setError(null);
      } catch (mutationError: unknown) {
        setError(
          mutationError instanceof Error
            ? mutationError.message
            : "Operational update failed.",
        );
      } finally {
        setMutating(false);
      }
    },
    [],
  );

  const resetScenario = useCallback(async () => {
    setMutating(true);
    try {
      const state = await resetOperationalState();
      const nextRoute = await fetchGoldenStepFreeRoute();
      setOperationalState(state);
      setRoute(nextRoute);
      setError(null);
    } catch (mutationError: unknown) {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : "Operational reset failed.",
      );
    } finally {
      setMutating(false);
    }
  }, []);

  return {
    accessibility,
    activeLevelId,
    applyAssetOverride,
    currentAccessibilityChecks,
    effectiveLevelData,
    error,
    levelData,
    loading,
    mutating,
    operationalState,
    refreshOperationalView,
    resetScenario,
    route,
    setActiveLevelId,
    validation,
    venue,
  };
}
