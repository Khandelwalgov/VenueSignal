"use client";

import { Asset, LevelData, Node, Zone } from "@/lib/api";

interface MapDisplayProps {
  levelData: LevelData;
  selectedEntityId: string | null;
  visibleAssetIds: string[];
  routeEdgeIds?: string[];
  onSelectEntity: (id: string) => void;
}

const assetSymbols: Record<string, string> = {
  LIFT: "L",
  STAIRS: "S",
  ESCALATOR: "E",
  RESTROOM: "AR",
  SCANNER_BANK: "SB",
  CORRIDOR: "W3",
};

function zoneBounds(zone: Zone, nodes: Node[]) {
  const zoneNodes = nodes.filter((node) => zone.nodeIds.includes(node.id));
  if (zoneNodes.length === 0) return null;
  const xs = zoneNodes.map((node) => node.x);
  const ys = zoneNodes.map((node) => node.y);
  const left = Math.max(20, Math.min(...xs) - 55);
  const top = Math.max(20, Math.min(...ys) - 55);
  const right = Math.min(980, Math.max(...xs) + 55);
  const bottom = Math.min(980, Math.max(...ys) + 55);
  return {
    x: left,
    y: top,
    width: Math.max(110, right - left),
    height: Math.max(90, bottom - top),
  };
}

function nodeAsset(node: Node, assets: Asset[]) {
  return node.assetId ? assets.find((asset) => asset.id === node.assetId) : undefined;
}

export default function MapDisplay({
  levelData,
  selectedEntityId,
  visibleAssetIds,
  routeEdgeIds = [],
  onSelectEntity,
}: MapDisplayProps) {
  const visibleAssets = new Set(visibleAssetIds);

  return (
    <svg
      viewBox="0 0 1000 1000"
      className="stadium-map"
      aria-labelledby="map-title map-description"
      role="group"
    >
      <title id="map-title">{levelData.level.label} operations map</title>
      <desc id="map-description">
        Synthetic stadium map with selectable zones and facilities. Equivalent
        zone and asset controls are provided beside the map.
      </desc>

      <rect className="map-surface" x="8" y="8" width="984" height="984" rx="42" />
      <ellipse className="stadium-bowl" cx="500" cy="500" rx="245" ry="190" />
      <rect className="stadium-field" x="375" y="405" width="250" height="190" rx="18" />
      <text className="field-label" x="500" y="505" textAnchor="middle">
        UNITY FIELD
      </text>

      <g aria-label="Operational zones">
        {levelData.zones.map((zone) => {
          const bounds = zoneBounds(zone, levelData.nodes);
          if (!bounds) return null;
          const selected = selectedEntityId === zone.id;
          return (
            <g
              key={zone.id}
              role="button"
              tabIndex={0}
              aria-label={`${zone.label}, zone status ${zone.status}`}
              aria-pressed={selected}
              data-entity-id={zone.id}
              className={`map-zone status-${zone.status.toLowerCase()} ${selected ? "is-selected" : ""}`}
              onClick={() => onSelectEntity(zone.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEntity(zone.id);
                }
              }}
            >
              <rect {...bounds} rx="24" />
              <text x={bounds.x + 14} y={bounds.y + 24}>
                {zone.label}
              </text>
            </g>
          );
        })}
      </g>

      <g aria-hidden="true">
        {levelData.edges.map((edge) => {
          const fromNode = levelData.nodes.find((node) => node.id === edge.fromNodeId);
          const toNode = levelData.nodes.find((node) => node.id === edge.toNodeId);
          if (!fromNode || !toNode) return null;
          return (
            <line
              key={edge.id}
              x1={fromNode.x}
              y1={fromNode.y}
              x2={toNode.x}
              y2={toNode.y}
              className={`map-edge status-${edge.status.toLowerCase()} ${edge.stepFree ? "is-step-free" : "contains-stairs"} ${routeEdgeIds.includes(edge.id) ? "is-route" : ""}`}
            />
          );
        })}
      </g>

      <g aria-label="Map facilities and destinations">
        {levelData.nodes.map((node) => {
          const asset = nodeAsset(node, levelData.assets);
          if (asset && !visibleAssets.has(asset.id)) return null;
          const entityId = asset?.id ?? node.id;
          const selected = selectedEntityId === entityId;
          const symbol = asset ? assetSymbols[asset.type] ?? "A" : node.type === "GATE" ? "G" : "•";
          return (
            <g
              key={node.id}
              role="button"
              tabIndex={0}
              aria-label={`${asset?.label ?? node.label}, ${asset ? `asset status ${asset.status}` : `node status ${node.status}`}${asset?.accessibilityCritical ? ", accessibility critical" : ""}`}
              aria-pressed={selected}
              data-entity-id={entityId}
              className={`map-entity ${asset ? "is-asset" : "is-node"} ${asset?.accessibilityCritical ? "is-critical" : ""} ${selected ? "is-selected" : ""}`}
              onClick={() => onSelectEntity(entityId)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEntity(entityId);
                }
              }}
            >
              <circle cx={node.x} cy={node.y} r={asset ? 22 : 14} />
              <text className="entity-symbol" x={node.x} y={node.y + 5} textAnchor="middle">
                {symbol}
              </text>
              <text className="entity-label" x={node.x} y={node.y - 30} textAnchor="middle">
                {node.label}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
