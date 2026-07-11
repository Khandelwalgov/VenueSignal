"use client";

import { LevelData } from "@/lib/api";

interface MapDisplayProps {
  levelData: LevelData;
  selectedEntityId: string | null;
  onSelectEntity: (id: string) => void;
}

export default function MapDisplay({ levelData, selectedEntityId, onSelectEntity }: MapDisplayProps) {
  // A simple viewbox to contain 0,0 to 1000,1000 coordinates.
  const viewBox = "0 0 1000 1000";

  const getEdgeStyle = (status: string) => {
    switch (status) {
      case "OPEN":
        return { stroke: "var(--success)", strokeWidth: 4, strokeDasharray: "none" };
      case "RESTRICTED":
        return { stroke: "var(--warning)", strokeWidth: 4, strokeDasharray: "10, 5" };
      case "CLOSED":
        return { stroke: "var(--danger)", strokeWidth: 4, strokeDasharray: "4, 4" };
      default:
        return { stroke: "#9ca3af", strokeWidth: 4 };
    }
  };

  const getNodeStyle = (status: string, isSelected: boolean) => {
    const baseStyle = { stroke: isSelected ? "var(--foreground)" : "white", strokeWidth: isSelected ? 4 : 2 };
    switch (status) {
      case "OPEN":
        return { ...baseStyle, fill: "var(--success)" };
      case "RESTRICTED":
        return { ...baseStyle, fill: "var(--warning)" };
      case "CLOSED":
        return { ...baseStyle, fill: "var(--danger)" };
      default:
        return { ...baseStyle, fill: "var(--primary)" };
    }
  };

  return (
    <svg 
      viewBox={viewBox} 
      style={{ width: "100%", height: "100%", maxHeight: "800px" }}
      aria-label={`Interactive map for ${levelData.level.label}`}
      role="application"
    >
      <title>{levelData.level.label} Map</title>
      <desc>SVG map showing paths and nodes for the selected level. Use Tab to navigate interactive elements.</desc>
      
      {/* Edges */}
      {levelData.edges.map((edge) => {
        const fromNode = levelData.nodes.find(n => n.id === edge.fromNodeId);
        const toNode = levelData.nodes.find(n => n.id === edge.toNodeId);
        
        if (!fromNode || !toNode) return null;
        const style = getEdgeStyle(edge.status);
        const isSelected = selectedEntityId === edge.id;

        return (
          <g key={edge.id}>
            <line
              x1={fromNode.x}
              y1={fromNode.x === fromNode.x ? fromNode.y : fromNode.y} // avoid unused var warning if any
              x2={toNode.x}
              y2={toNode.y}
              style={{ ...style, strokeWidth: isSelected ? 6 : style.strokeWidth }}
              onClick={() => onSelectEntity(edge.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectEntity(edge.id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`Path ${edge.id}, status: ${edge.status}, ${edge.textDescription}`}
              className="svg-interactive"
              cursor="pointer"
            >
              <title>{edge.textDescription}</title>
            </line>
          </g>
        );
      })}

      {/* Nodes */}
      {levelData.nodes.map((node) => {
        const isSelected = selectedEntityId === node.id || (node.assetId && selectedEntityId === node.assetId);
        const style = getNodeStyle(node.status, !!isSelected);
        
        // Let's check if there's a related asset, if so we prefer selecting the asset
        const idToSelect = node.assetId ? node.assetId : node.id;

        return (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={15}
              style={style}
              onClick={() => onSelectEntity(idToSelect)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectEntity(idToSelect);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={`${node.label}, status: ${node.status}`}
              className="svg-interactive"
              cursor="pointer"
            >
              <title>{node.label}</title>
            </circle>
            <text 
              x={node.x} 
              y={node.y - 20} 
              textAnchor="middle" 
              fontSize="12" 
              fill="var(--foreground)"
              pointerEvents="none"
              fontWeight={isSelected ? "bold" : "normal"}
            >
              {node.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
