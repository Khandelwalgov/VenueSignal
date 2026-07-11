export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';

export interface Entity {
  id: string;
}

export interface VenueMetadata {
  id: string;
  name: string;
  description: string;
  synthetic: boolean;
  statistics: Record<string, number>;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  statistics: Record<string, number>;
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
  levelId: string;
  zoneId?: string;
  label: string;
  type: string;
  x: number;
  y: number;
  accessible: boolean;
  staffOnly: boolean;
  capacity: number;
  status: string;
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
  status: string;
  textDescription: string;
}

export interface Zone {
  id: string;
  levelId: string;
  label: string;
  type: string;
  capacity: number;
  occupancyPercent: number;
  status: string;
}

export interface Asset {
  id: string;
  levelId: string;
  zoneId?: string;
  type: string;
  label: string;
  status: string;
  accessibilityCritical: boolean;
  textDescription: string;
}

export interface LevelData {
  level: Level;
  nodes: Node[];
  edges: Edge[];
  zones: Zone[];
  assets: Asset[];
}

export async function fetchVenues(): Promise<VenueMetadata[]> {
  const res = await fetch(`${API_BASE_URL}/venues`);
  if (!res.ok) throw new Error('Failed to fetch venues');
  return res.json();
}

export async function fetchVenue(venueId: string): Promise<VenueMetadata> {
  const res = await fetch(`${API_BASE_URL}/venues/${venueId}`);
  if (!res.ok) throw new Error('Failed to fetch venue metadata');
  return res.json();
}

export async function fetchLevel(venueId: string, levelId: string): Promise<LevelData> {
  const res = await fetch(`${API_BASE_URL}/venues/${venueId}/levels/${levelId}`);
  if (!res.ok) throw new Error(`Failed to fetch level ${levelId}`);
  return res.json();
}

export async function fetchValidation(venueId: string): Promise<ValidationResult> {
  const res = await fetch(`${API_BASE_URL}/venues/${venueId}/validation`);
  if (!res.ok) throw new Error('Failed to fetch validation status');
  return res.json();
}
