"use client";

import { LevelData } from "@/lib/api";

interface DetailsPanelProps {
  entityId: string | null;
  levelData: LevelData | null;
}

function Status({ value }: { value: string }) {
  const positive = ["OPEN", "OPERATIONAL", "NORMAL"].includes(value);
  const symbol = positive ? "✓" : value === "CLOSED" || value === "OUT_OF_SERVICE" ? "×" : "!";
  return (
    <span className={`status-badge status-${value.toLowerCase()}`}>
      <span aria-hidden="true">{symbol}</span> {value.replaceAll("_", " ")}
    </span>
  );
}

export default function DetailsPanel({ entityId, levelData }: DetailsPanelProps) {
  if (!entityId || !levelData) {
    return (
      <section className="details-content" aria-labelledby="details-title">
        <h2 id="details-title">Selected item</h2>
        <p className="muted">Choose a zone or facility from the map or the structured controls.</p>
      </section>
    );
  }

  const asset = levelData.assets.find((item) => item.id === entityId);
  const node = levelData.nodes.find((item) => item.id === entityId);
  const edge = levelData.edges.find((item) => item.id === entityId);
  const zone = levelData.zones.find((item) => item.id === entityId);

  return (
    <section className="details-content" aria-labelledby="details-title" aria-live="polite">
      <div className="eyebrow">Selected intelligence</div>
      <h2 id="details-title">{asset?.label ?? node?.label ?? zone?.label ?? edge?.id ?? "Selected item"}</h2>

      {asset && (
        <dl className="detail-list">
          <div><dt>Status</dt><dd><Status value={asset.status} /></dd></div>
          <div><dt>Facility type</dt><dd>{asset.type.replaceAll("_", " ")}</dd></div>
          <div><dt>Accessibility-critical</dt><dd>{asset.accessibilityCritical ? "Yes — route validation must account for this asset" : "No"}</dd></div>
          <div><dt>Served nodes</dt><dd>{asset.servedNodeIds.length}</dd></div>
          <div><dt>Served edges</dt><dd>{asset.servedEdgeIds.length}</dd></div>
        </dl>
      )}

      {node && !asset && (
        <dl className="detail-list">
          <div><dt>Status</dt><dd><Status value={node.status} /></dd></div>
          <div><dt>Node type</dt><dd>{node.type}</dd></div>
          <div><dt>Step-free compatible</dt><dd>{node.accessible ? "Yes" : "No"}</dd></div>
          <div><dt>Staff only</dt><dd>{node.staffOnly ? "Yes" : "No"}</dd></div>
        </dl>
      )}

      {edge && (
        <dl className="detail-list">
          <div><dt>Status</dt><dd><Status value={edge.status} /></dd></div>
          <div><dt>Distance</dt><dd>{edge.distanceMeters} m · {edge.estimatedSeconds} sec</dd></div>
          <div><dt>Step-free</dt><dd>{edge.stepFree ? "Yes" : "No"}</dd></div>
          <div><dt>Staff only</dt><dd>{edge.staffOnly ? "Yes" : "No"}</dd></div>
        </dl>
      )}

      {zone && (
        <dl className="detail-list">
          <div><dt>Status</dt><dd><Status value={zone.status} /></dd></div>
          <div><dt>Zone type</dt><dd>{zone.type}</dd></div>
          <div><dt>Capacity</dt><dd>{zone.capacity.toLocaleString()}</dd></div>
          <div><dt>Synthetic occupancy</dt><dd>{zone.occupancyPercent}%</dd></div>
        </dl>
      )}

      <p className="detail-description">
        {asset?.textDescription ?? node?.textDescription ?? edge?.textDescription ??
          (zone ? `${zone.label} contains ${zone.nodeIds.length} graph nodes and ${zone.assetIds.length} facilities.` : "No details are available.")}
      </p>
    </section>
  );
}

export { Status };
