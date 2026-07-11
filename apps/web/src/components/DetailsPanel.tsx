"use client";

import { LevelData } from "@/lib/api";

interface DetailsPanelProps {
  entityId: string | null;
  levelData: LevelData | null;
}

export default function DetailsPanel({ entityId, levelData }: DetailsPanelProps) {
  if (!entityId || !levelData) {
    return (
      <div>
        <h2 className="details-title">Details</h2>
        <p>Select an asset, node, or path on the map to view details.</p>
      </div>
    );
  }

  // Find what was selected
  const asset = levelData.assets.find(a => a.id === entityId);
  const node = levelData.nodes.find(n => n.id === entityId);
  const edge = levelData.edges.find(e => e.id === entityId);
  const zone = levelData.zones.find(z => z.id === entityId);

  return (
    <div>
      <h2 className="details-title">Details</h2>
      
      {asset && (
        <div>
          <h3>{asset.label}</h3>
          <p><strong>Type:</strong> {asset.type}</p>
          <p><strong>Status:</strong> <span className={`status-badge ${asset.status}`}>{asset.status}</span></p>
          <p><strong>Accessibility Critical:</strong> {asset.accessibilityCritical ? 'Yes' : 'No'}</p>
          <p><strong>Description:</strong> {asset.textDescription}</p>
        </div>
      )}

      {node && !asset && (
        <div>
          <h3>{node.label}</h3>
          <p><strong>Type:</strong> {node.type}</p>
          <p><strong>Status:</strong> <span className={`status-badge ${node.status}`}>{node.status}</span></p>
          <p><strong>Accessible:</strong> {node.accessible ? 'Yes' : 'No'}</p>
          <p><strong>Staff Only:</strong> {node.staffOnly ? 'Yes' : 'No'}</p>
          <p><strong>Description:</strong> {node.textDescription}</p>
        </div>
      )}

      {edge && (
        <div>
          <h3>Path: {edge.id}</h3>
          <p><strong>Status:</strong> <span className={`status-badge ${edge.status}`}>{edge.status}</span></p>
          <p><strong>Distance:</strong> {edge.distanceMeters}m ({edge.estimatedSeconds}s)</p>
          <p><strong>Step-free:</strong> {edge.stepFree ? 'Yes' : 'No'}</p>
          <p><strong>Stairs:</strong> {edge.containsStairs ? 'Yes' : 'No'}</p>
          <p><strong>Staff Only:</strong> {edge.staffOnly ? 'Yes' : 'No'}</p>
          <p><strong>Description:</strong> {edge.textDescription}</p>
        </div>
      )}

      {zone && (
        <div>
          <h3>{zone.label}</h3>
          <p><strong>Type:</strong> {zone.type}</p>
          <p><strong>Status:</strong> <span className={`status-badge ${zone.status}`}>{zone.status}</span></p>
          <p><strong>Capacity:</strong> {zone.capacity} ({zone.occupancyPercent}% full)</p>
        </div>
      )}

      {!asset && !node && !edge && !zone && (
        <p>Details not available for the selected item on this level.</p>
      )}
    </div>
  );
}
