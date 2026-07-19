import { getAuthToken } from "@/lib/auth";


export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api"
).replace(/\/$/, "");

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
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
