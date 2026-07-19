import { requestJson } from "./client";
import {
  AccessibilitySummary,
  LevelData,
  ValidationResult,
  VenueMetadata,
} from "./types";


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
