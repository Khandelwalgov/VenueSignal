from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from app.domain.venue.enums import AssetStatus, EdgeStatus, NodeStatus
from app.domain.venue.models import Edge, ValidationResult, Venue


SUPPORTED_NODE_TYPES = {
    "AMENITY",
    "CHECKPOINT",
    "CORRIDOR",
    "ESCALATOR",
    "GATE",
    "HUB",
    "LIFT",
    "RESTROOM",
    "SEATING",
    "STAIRS",
}
SUPPORTED_ZONE_TYPES = {"CONCOURSE", "SEATING", "SECURITY"}
SUPPORTED_ASSET_TYPES = {
    "CORRIDOR",
    "ESCALATOR",
    "LIFT",
    "RESTROOM",
    "SCANNER_BANK",
    "STAIRS",
}
VERTICAL_ASSET_TYPES = {"CORRIDOR", "ESCALATOR", "LIFT", "STAIRS"}


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _edge_is_available(edge: Edge, asset_statuses: dict[str, AssetStatus]) -> bool:
    return edge.status != EdgeStatus.CLOSED and all(
        asset_statuses.get(asset_id) in {AssetStatus.OPERATIONAL, AssetStatus.DEGRADED}
        for asset_id in edge.dependent_asset_ids
    )


def reachable_nodes(
    venue: Venue,
    start_node_ids: Iterable[str],
    *,
    step_free: bool = False,
    allow_staff_only: bool = False,
    disabled_asset_ids: set[str] | None = None,
) -> set[str]:
    """Return nodes reachable under base-state deterministic constraints."""

    nodes = {node.id: node for node in venue.nodes}
    disabled = disabled_asset_ids or set()
    asset_statuses = {
        asset.id: (
            AssetStatus.OUT_OF_SERVICE if asset.id in disabled else asset.status
        )
        for asset in venue.assets
    }
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in venue.edges:
        if edge.from_node_id not in nodes or edge.to_node_id not in nodes:
            continue
        if not _edge_is_available(edge, asset_statuses):
            continue
        if not allow_staff_only and edge.staff_only:
            continue
        if step_free and (not edge.step_free or edge.contains_stairs):
            continue
        adjacency[edge.from_node_id].add(edge.to_node_id)
        adjacency[edge.to_node_id].add(edge.from_node_id)

    starts = {
        node_id
        for node_id in start_node_ids
        if node_id in nodes
        and nodes[node_id].status != NodeStatus.CLOSED
        and (allow_staff_only or not nodes[node_id].staff_only)
    }
    reached = set(starts)
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        for candidate in adjacency[current] - reached:
            node = nodes[candidate]
            if node.status == NodeStatus.CLOSED:
                continue
            if not allow_staff_only and node.staff_only:
                continue
            if step_free and not node.accessible:
                continue
            reached.add(candidate)
            queue.append(candidate)
    return reached


def _connected_components(venue: Venue) -> list[set[str]]:
    nodes = {node.id for node in venue.nodes}
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in venue.edges:
        if edge.from_node_id in nodes and edge.to_node_id in nodes:
            adjacency[edge.from_node_id].add(edge.to_node_id)
            adjacency[edge.to_node_id].add(edge.from_node_id)

    remaining = set(nodes)
    components: list[set[str]] = []
    while remaining:
        start = next(iter(remaining))
        component = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for candidate in adjacency[current] - component:
                component.add(candidate)
                queue.append(candidate)
        remaining -= component
        components.append(component)
    return components


def validate_venue_graph(venue: Venue) -> ValidationResult:
    result = ValidationResult()

    entity_groups = {
        "level": venue.levels,
        "zone": venue.zones,
        "node": venue.nodes,
        "edge": venue.edges,
        "asset": venue.assets,
    }
    for entity_type, entities in entity_groups.items():
        for duplicate_id in sorted(_duplicates(entity.id for entity in entities)):
            result.add_error(
                "DUPLICATE_ID",
                f"Duplicate {entity_type} ID: {duplicate_id}",
                entity_type,
                duplicate_id,
            )

    id_owners: dict[str, list[str]] = defaultdict(list)
    for entity_type, entities in entity_groups.items():
        for entity in entities:
            id_owners[entity.id].append(entity_type)
    for entity_id, owners in id_owners.items():
        if len(set(owners)) > 1:
            result.add_error(
                "CROSS_ENTITY_DUPLICATE_ID",
                f"ID {entity_id} is reused across entity types.",
                entity_id=entity_id,
                related_ids=sorted(set(owners)),
            )

    levels = {level.id: level for level in venue.levels}
    zones = {zone.id: zone for zone in venue.zones}
    nodes = {node.id: node for node in venue.nodes}
    edges = {edge.id: edge for edge in venue.edges}
    assets = {asset.id: asset for asset in venue.assets}

    for level in venue.levels:
        if level.venue_id != venue.id:
            result.add_error("VENUE_ID_MISMATCH", "Level venueId does not match venue.", "level", level.id)

    for zone in venue.zones:
        if zone.venue_id != venue.id:
            result.add_error("VENUE_ID_MISMATCH", "Zone venueId does not match venue.", "zone", zone.id)
        if zone.level_id not in levels:
            result.add_error("UNKNOWN_LEVEL", f"Unknown level {zone.level_id}.", "zone", zone.id, [zone.level_id])
        if zone.type not in SUPPORTED_ZONE_TYPES:
            result.add_error("UNSUPPORTED_ZONE_TYPE", f"Unsupported zone type {zone.type}.", "zone", zone.id)
        if zone.capacity < 0:
            result.add_error("INVALID_CAPACITY", "Zone capacity cannot be negative.", "zone", zone.id)
        if not 0 <= zone.occupancy_percent <= 100:
            result.add_error("INVALID_OCCUPANCY_PERCENT", "Zone occupancy must be between 0 and 100.", "zone", zone.id)
        for node_id in zone.node_ids:
            node = nodes.get(node_id)
            if node is None:
                result.add_error("UNKNOWN_NODE", f"Zone references unknown node {node_id}.", "zone", zone.id, [node_id])
            elif node.zone_id != zone.id:
                result.add_error("ZONE_NODE_MEMBERSHIP_MISMATCH", f"Node {node_id} does not point back to zone {zone.id}.", "zone", zone.id, [node_id])
        for asset_id in zone.asset_ids:
            asset = assets.get(asset_id)
            if asset is None:
                result.add_error("UNKNOWN_ASSET", f"Zone references unknown asset {asset_id}.", "zone", zone.id, [asset_id])
            elif asset.zone_id != zone.id and not any(
                nodes.get(node_id) and nodes[node_id].zone_id == zone.id
                for node_id in asset.served_node_ids
            ):
                result.add_error("ZONE_ASSET_MEMBERSHIP_MISMATCH", f"Asset {asset_id} does not serve zone {zone.id}.", "zone", zone.id, [asset_id])

    coordinate_min = venue.configuration.coordinate_min
    coordinate_max = venue.configuration.coordinate_max
    if coordinate_min >= coordinate_max:
        result.add_error("INVALID_COORDINATE_BOUNDS", "coordinateMin must be less than coordinateMax.", "venue", venue.id)

    for node in venue.nodes:
        if node.venue_id != venue.id:
            result.add_error("VENUE_ID_MISMATCH", "Node venueId does not match venue.", "node", node.id)
        if node.level_id not in levels:
            result.add_error("UNKNOWN_LEVEL", f"Unknown level {node.level_id}.", "node", node.id, [node.level_id])
        if node.zone_id is None or node.zone_id not in zones:
            result.add_error("UNKNOWN_ZONE", f"Unknown or missing zone {node.zone_id}.", "node", node.id, [node.zone_id or ""])
        else:
            zone = zones[node.zone_id]
            if node.id not in zone.node_ids:
                result.add_error("NODE_ZONE_MEMBERSHIP_MISMATCH", f"Node is absent from zone {zone.id} nodeIds.", "node", node.id, [zone.id])
            if zone.level_id != node.level_id:
                result.add_error("NODE_ZONE_LEVEL_MISMATCH", "Node and zone are on different levels.", "node", node.id, [zone.id])
        if node.type not in SUPPORTED_NODE_TYPES:
            result.add_error("UNSUPPORTED_NODE_TYPE", f"Unsupported node type {node.type}.", "node", node.id)
        if node.capacity < 0:
            result.add_error("INVALID_CAPACITY", "Node capacity cannot be negative.", "node", node.id)
        if not coordinate_min <= node.x <= coordinate_max or not coordinate_min <= node.y <= coordinate_max:
            result.add_error("INVALID_COORDINATE", f"Node coordinates must be within {coordinate_min}–{coordinate_max}.", "node", node.id)
        if node.asset_id:
            asset = assets.get(node.asset_id)
            if asset is None:
                result.add_error("UNKNOWN_ASSET", f"Node references unknown asset {node.asset_id}.", "node", node.id, [node.asset_id])
            elif node.id not in asset.served_node_ids:
                result.add_error("NODE_ASSET_MEMBERSHIP_MISMATCH", "Node asset does not list this node as served.", "node", node.id, [asset.id])

    for asset in venue.assets:
        if asset.venue_id != venue.id:
            result.add_error("VENUE_ID_MISMATCH", "Asset venueId does not match venue.", "asset", asset.id)
        if asset.level_id not in levels:
            result.add_error("UNKNOWN_LEVEL", f"Unknown level {asset.level_id}.", "asset", asset.id, [asset.level_id])
        if asset.zone_id is None or asset.zone_id not in zones:
            result.add_error("UNKNOWN_ZONE", f"Unknown or missing zone {asset.zone_id}.", "asset", asset.id, [asset.zone_id or ""])
        elif asset.id not in zones[asset.zone_id].asset_ids:
            result.add_error("ASSET_ZONE_MEMBERSHIP_MISMATCH", "Asset is absent from its home zone assetIds.", "asset", asset.id, [asset.zone_id])
        if asset.type not in SUPPORTED_ASSET_TYPES:
            result.add_error("UNSUPPORTED_ASSET_TYPE", f"Unsupported asset type {asset.type}.", "asset", asset.id)
        for node_id in asset.served_node_ids:
            if node_id not in nodes:
                result.add_error("UNKNOWN_SERVED_NODE", f"Asset serves unknown node {node_id}.", "asset", asset.id, [node_id])
        for edge_id in asset.served_edge_ids:
            if edge_id not in edges:
                result.add_error("UNKNOWN_SERVED_EDGE", f"Asset serves unknown edge {edge_id}.", "asset", asset.id, [edge_id])

    undirected_edges: dict[tuple[str, str], list[Edge]] = defaultdict(list)
    vertical_edges: list[Edge] = []
    for edge in venue.edges:
        from_node = nodes.get(edge.from_node_id)
        to_node = nodes.get(edge.to_node_id)
        if from_node is None:
            result.add_error("UNKNOWN_EDGE_ENDPOINT", f"Unknown from-node {edge.from_node_id}.", "edge", edge.id, [edge.from_node_id])
        if to_node is None:
            result.add_error("UNKNOWN_EDGE_ENDPOINT", f"Unknown to-node {edge.to_node_id}.", "edge", edge.id, [edge.to_node_id])
        if edge.from_node_id == edge.to_node_id:
            result.add_error("SELF_EDGE", "Self-edges are not supported.", "edge", edge.id, [edge.from_node_id])
        if edge.distance_meters <= 0:
            result.add_error("INVALID_DISTANCE", "Edge distance must be positive.", "edge", edge.id)
        if edge.estimated_seconds <= 0:
            result.add_error("INVALID_ESTIMATED_TIME", "Edge estimated time must be positive.", "edge", edge.id)
        if edge.maximum_capacity < 0:
            result.add_error("INVALID_CAPACITY", "Edge capacity cannot be negative.", "edge", edge.id)
        if not 0 <= edge.current_crowd_percent <= 100:
            result.add_error("INVALID_CROWD_PERCENT", "Edge crowd percent must be between 0 and 100.", "edge", edge.id)
        if edge.step_free and edge.contains_stairs:
            result.add_error("STAIRS_MARKED_STEP_FREE", "An edge cannot contain stairs and be step-free.", "edge", edge.id)
        for asset_id in edge.dependent_asset_ids:
            asset = assets.get(asset_id)
            if asset is None:
                result.add_error("UNKNOWN_DEPENDENT_ASSET", f"Unknown dependent asset {asset_id}.", "edge", edge.id, [asset_id])

        key = tuple(sorted((edge.from_node_id, edge.to_node_id)))
        undirected_edges[key].append(edge)
        if from_node and to_node and from_node.level_id != to_node.level_id:
            vertical_edges.append(edge)
            transition_assets = [assets[asset_id] for asset_id in edge.dependent_asset_ids if asset_id in assets and assets[asset_id].type in VERTICAL_ASSET_TYPES]
            if not transition_assets:
                result.add_error("CROSS_LEVEL_EDGE_WITHOUT_TRANSITION", "Cross-level edge requires a valid transition asset.", "edge", edge.id, [from_node.level_id, to_node.level_id])
            for asset in transition_assets:
                if edge.id not in asset.served_edge_ids:
                    result.add_error("TRANSITION_ASSET_EDGE_MISMATCH", "Transition asset does not list the edge as served.", "edge", edge.id, [asset.id])
                if not {edge.from_node_id, edge.to_node_id}.issubset(set(asset.served_node_ids)):
                    result.add_error("TRANSITION_ASSET_NODE_MISMATCH", "Transition asset does not list both endpoint nodes.", "edge", edge.id, [asset.id])

    for edge_group in undirected_edges.values():
        if len(edge_group) > 1 and len({edge.staff_only for edge in edge_group}) == 1:
            result.add_error(
                "DUPLICATE_UNDIRECTED_EDGE",
                "Multiple edges connect the same endpoints without a distinct staff-only policy.",
                "edge",
                edge_group[0].id,
                [edge.id for edge in edge_group[1:]],
            )

    for asset in venue.assets:
        served_nodes = [nodes[node_id] for node_id in asset.served_node_ids if node_id in nodes]
        served_levels = {node.level_id for node in served_nodes}
        if len(served_levels) > 1 and asset.type in VERTICAL_ASSET_TYPES:
            level_adjacency: dict[str, set[str]] = defaultdict(set)
            for edge_id in asset.served_edge_ids:
                edge = edges.get(edge_id)
                if not edge or edge.from_node_id not in nodes or edge.to_node_id not in nodes:
                    continue
                from_level = nodes[edge.from_node_id].level_id
                to_level = nodes[edge.to_node_id].level_id
                if from_level != to_level:
                    level_adjacency[from_level].add(to_level)
                    level_adjacency[to_level].add(from_level)
            first_level = next(iter(served_levels))
            connected_levels = {first_level}
            queue = deque([first_level])
            while queue:
                current_level = queue.popleft()
                for candidate in level_adjacency[current_level] - connected_levels:
                    connected_levels.add(candidate)
                    queue.append(candidate)
            if not served_levels.issubset(connected_levels):
                result.add_error("DISCONNECTED_TRANSITION_ASSET", "Transition asset does not connect all served levels.", "asset", asset.id, sorted(served_levels - connected_levels))

    configured_node_lists = {
        "primary gate": venue.configuration.primary_gate_node_ids,
        "accessible entrance": venue.configuration.accessible_entrance_node_ids,
        "accessible destination": venue.configuration.accessible_destination_node_ids,
        "critical public node": venue.configuration.critical_public_node_ids,
    }
    for list_name, node_ids in configured_node_lists.items():
        for node_id in node_ids:
            if node_id not in nodes:
                result.add_error("UNKNOWN_CONFIGURED_NODE", f"Unknown configured {list_name} {node_id}.", "venue", venue.id, [node_id])

    components = _connected_components(venue)
    isolated = [node.id for node in venue.nodes if all(node.id not in {edge.from_node_id, edge.to_node_id} for edge in venue.edges)]
    for node_id in isolated:
        result.add_error("ISOLATED_NODE", "Node has no graph edges.", "node", node_id)

    public_reachable = reachable_nodes(venue, venue.configuration.primary_gate_node_ids)
    for node in venue.nodes:
        if not node.staff_only and node.id not in public_reachable:
            result.add_error("UNREACHABLE_PUBLIC_NODE", "Public node is unreachable from the primary gates.", "node", node.id)

    for gate_id in venue.configuration.primary_gate_node_ids:
        gate_reachable = reachable_nodes(venue, [gate_id])
        if "N_L0_CEN" in nodes and "N_L0_CEN" not in gate_reachable:
            result.add_error("UNREACHABLE_PRIMARY_GATE", "Primary gate cannot reach the main concourse.", "node", gate_id, ["N_L0_CEN"])

    step_free_reachable = reachable_nodes(
        venue,
        venue.configuration.accessible_entrance_node_ids,
        step_free=True,
    )
    for destination_id in venue.configuration.accessible_destination_node_ids:
        if destination_id in nodes and destination_id not in step_free_reachable:
            result.add_error("INACCESSIBLE_DESTINATION", "Designated destination is not step-free reachable.", "node", destination_id, venue.configuration.accessible_entrance_node_ids)

    lift_only_disabled = reachable_nodes(
        venue,
        venue.configuration.accessible_entrance_node_ids,
        step_free=True,
        disabled_asset_ids={"A_LIFT_2"},
    )
    both_disabled = reachable_nodes(
        venue,
        venue.configuration.accessible_entrance_node_ids,
        step_free=True,
        disabled_asset_ids={"A_LIFT_2", "A_CORRIDOR_W3"},
    )
    if "N_L2_SEC_209_218" not in lift_only_disabled:
        result.add_error("SCENARIO_W3_FALLBACK_MISSING", "Corridor W3 must preserve a step-free fallback when Lift L2 is unavailable.", "venue", venue.id)
    if "N_L2_SEC_209_218" in both_disabled:
        result.add_error("SCENARIO_NO_ROUTE_NOT_POSSIBLE", "Lift L2 and Corridor W3 outages must remove the verified step-free route to Sections 209–218.", "venue", venue.id)
    scanner = assets.get("A_SCANNER_N2")
    if not scanner or "E_N_GATE_TO_SEC" not in scanner.served_edge_ids:
        result.add_error("SCENARIO_SCANNER_N2_NOT_READY", "Scanner Bank N2 must influence North Gate throughput.", "venue", venue.id)

    result.statistics = {
        "levels": len(venue.levels),
        "zones": len(venue.zones),
        "nodes": len(venue.nodes),
        "edges": len(venue.edges),
        "assets": len(venue.assets),
        "connectedComponents": len(components),
        "isolatedNodes": len(isolated),
        "accessibleDestinations": len(venue.configuration.accessible_destination_node_ids),
        "stepFreeEdges": sum(edge.step_free and not edge.contains_stairs for edge in venue.edges),
        "staffOnlyEdges": sum(edge.staff_only for edge in venue.edges),
        "verticalTransitions": len(vertical_edges),
        "criticalAssets": sum(asset.accessibility_critical for asset in venue.assets),
        "reachableNodesPerEntrance": {
            entrance_id: len(reachable_nodes(venue, [entrance_id]))
            for entrance_id in venue.configuration.primary_gate_node_ids
            if entrance_id in nodes
        },
        "stepFreeReachableNodesFromWestAccessibleEntrance": len(step_free_reachable),
    }
    return result
