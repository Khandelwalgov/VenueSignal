import { requestJson } from "./client";
import { Principal } from "./types";


export function fetchPrincipal(): Promise<Principal> {
  return requestJson("/auth/me");
}
