from typing import Dict, List, Any
from app.domain.venue.models import Venue

class ValidationResult:
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.statistics: Dict[str, int] = {
            "levels": 0,
            "zones": 0,
            "nodes": 0,
            "edges": 0,
            "assets": 0,
            "step_free_edges": 0,
            "staff_only_edges": 0,
            "accessible_destinations": 0,
            "critical_assets": 0
        }

    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False
        
    def add_warning(self, message: str):
        self.warnings.append(message)
        
    def to_dict(self):
        return {
            "isValid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "statistics": self.statistics
        }

def validate_venue_graph(venue: Venue) -> ValidationResult:
    result = ValidationResult()
    
    # 1. Check for duplicate IDs
    all_ids = set()
    def check_duplicate(id_val: str, entity_type: str):
        if id_val in all_ids:
            result.add_error(f"Duplicate ID found across entities: {id_val} ({entity_type})")
        all_ids.add(id_val)
        
    for level in venue.levels:
        check_duplicate(level.id, "Level")
    for zone in venue.zones:
        check_duplicate(zone.id, "Zone")
    for node in venue.nodes:
        check_duplicate(node.id, "Node")
    for edge in venue.edges:
        check_duplicate(edge.id, "Edge")
    for asset in venue.assets:
        check_duplicate(asset.id, "Asset")
        
    # Build fast lookups
    level_ids = {level.id for level in venue.levels}
    zone_ids = {zone.id for zone in venue.zones}
    node_ids = {node.id for node in venue.nodes}
    asset_ids = {asset.id for asset in venue.assets}
    
    # Track accessible nodes to verify they are reachable
    accessible_node_ids = set()
    
    # Statistics
    result.statistics["levels"] = len(level_ids)
    result.statistics["zones"] = len(zone_ids)
    result.statistics["nodes"] = len(node_ids)
    result.statistics["edges"] = len(venue.edges)
    result.statistics["assets"] = len(asset_ids)

    # 2. Validate Entities
    for node in venue.nodes:
        if node.level_id not in level_ids:
            result.add_error(f"Node {node.id} references invalid level {node.level_id}")
        if node.zone_id and node.zone_id not in zone_ids:
            result.add_error(f"Node {node.id} references invalid zone {node.zone_id}")
        if node.asset_id and node.asset_id not in asset_ids:
            result.add_error(f"Node {node.id} references invalid asset {node.asset_id}")
        if node.accessible:
            accessible_node_ids.add(node.id)
            result.statistics["accessible_destinations"] += 1
            
    for asset in venue.assets:
        if asset.level_id not in level_ids:
            result.add_error(f"Asset {asset.id} references invalid level {asset.level_id}")
        if asset.zone_id and asset.zone_id not in zone_ids:
            result.add_error(f"Asset {asset.id} references invalid zone {asset.zone_id}")
        for served_node in asset.served_node_ids:
            if served_node not in node_ids:
                result.add_error(f"Asset {asset.id} serves invalid node {served_node}")
        for served_edge in asset.served_edge_ids:
            if served_edge not in [e.id for e in venue.edges]:
                result.add_error(f"Asset {asset.id} serves invalid edge {served_edge}")
        if asset.accessibility_critical:
            result.statistics["critical_assets"] += 1
                
    for zone in venue.zones:
        if zone.level_id not in level_ids:
            result.add_error(f"Zone {zone.id} references invalid level {zone.level_id}")
        for zn in zone.node_ids:
            if zn not in node_ids:
                result.add_error(f"Zone {zone.id} references invalid node {zn}")
        for za in zone.asset_ids:
            if za not in asset_ids:
                result.add_error(f"Zone {zone.id} references invalid asset {za}")
                
    for edge in venue.edges:
        if edge.from_node_id not in node_ids:
            result.add_error(f"Edge {edge.id} references invalid fromNode {edge.from_node_id}")
        if edge.to_node_id not in node_ids:
            result.add_error(f"Edge {edge.id} references invalid toNode {edge.to_node_id}")
        if edge.from_node_id == edge.to_node_id:
            result.add_error(f"Edge {edge.id} is a self-edge from/to {edge.from_node_id}")
            
        for da in edge.dependent_asset_ids:
            if da not in asset_ids:
                result.add_error(f"Edge {edge.id} references invalid dependent asset {da}")
                
        if edge.step_free and edge.contains_stairs:
            result.add_error(f"Edge {edge.id} is marked both step-free and contains_stairs")
            
        if edge.step_free:
            result.statistics["step_free_edges"] += 1
        if edge.staff_only:
            result.statistics["staff_only_edges"] += 1

    return result
