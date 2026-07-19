import { requestJson } from "./client";
import { AssetStatus, OperationalState, RouteResult } from "./types";


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
