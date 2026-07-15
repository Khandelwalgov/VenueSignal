from copy import deepcopy

import pytest

from app.domain.venue.models import Venue
from app.domain.venue.service import DEFAULT_VENUE_PATH
from app.domain.venue.validator import validate_venue_graph


@pytest.fixture
def canonical() -> Venue:
    return Venue.model_validate_json(DEFAULT_VENUE_PATH.read_text(encoding="utf-8"))


def error_codes(venue: Venue) -> set[str]:
    return {issue.code for issue in validate_venue_graph(venue).errors}


def test_canonical_graph_is_connected_and_valid(canonical):
    result = validate_venue_graph(canonical)
    assert result.valid is True
    assert result.errors == []
    assert result.warnings == []
    assert result.statistics["connectedComponents"] == 1
    assert result.statistics["isolatedNodes"] == 0


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (lambda venue: venue.nodes.append(deepcopy(venue.nodes[0])), "DUPLICATE_ID"),
        (lambda venue: venue.assets.append(deepcopy(venue.assets[0])), "DUPLICATE_ID"),
        (lambda venue: setattr(venue.edges[0], "to_node_id", "UNKNOWN"), "UNKNOWN_EDGE_ENDPOINT"),
        (lambda venue: venue.assets[0].served_node_ids.append("UNKNOWN"), "UNKNOWN_SERVED_NODE"),
        (lambda venue: venue.assets[0].served_edge_ids.append("UNKNOWN"), "UNKNOWN_SERVED_EDGE"),
        (lambda venue: setattr(venue.nodes[0], "zone_id", "UNKNOWN"), "UNKNOWN_ZONE"),
        (lambda venue: setattr(venue.edges[0], "current_crowd_percent", 101), "INVALID_CROWD_PERCENT"),
        (lambda venue: setattr(venue.edges[0], "distance_meters", -1), "INVALID_DISTANCE"),
        (lambda venue: setattr(venue.edges[0], "estimated_seconds", 0), "INVALID_ESTIMATED_TIME"),
        (lambda venue: setattr(next(edge for edge in venue.edges if edge.contains_stairs), "step_free", True), "STAIRS_MARKED_STEP_FREE"),
        (lambda venue: setattr(venue.nodes[0], "x", 1001), "INVALID_COORDINATE"),
        (lambda venue: venue.zones[0].node_ids.remove(venue.nodes[0].id), "NODE_ZONE_MEMBERSHIP_MISMATCH"),
        (lambda venue: venue.zones[0].asset_ids.remove("A_SCANNER_N2"), "ASSET_ZONE_MEMBERSHIP_MISMATCH"),
    ],
)
def test_validator_mutations(canonical, mutation, expected_code):
    mutation(canonical)
    assert expected_code in error_codes(canonical)


def test_isolated_public_node_is_rejected(canonical):
    target = "N_L0_MED_1"
    canonical.edges = [
        edge
        for edge in canonical.edges
        if target not in {edge.from_node_id, edge.to_node_id}
    ]
    assert {"ISOLATED_NODE", "UNREACHABLE_PUBLIC_NODE"}.issubset(error_codes(canonical))


def test_inaccessible_destination_is_rejected(canonical):
    target = next(node for node in canonical.nodes if node.id == "N_L2_WAIT_2")
    target.accessible = False
    assert "INACCESSIBLE_DESTINATION" in error_codes(canonical)


@pytest.mark.parametrize("asset_id", ["A_LIFT_2", "A_STAIR_2", "A_STAIR_3"])
def test_disconnected_transition_asset_is_rejected(canonical, asset_id):
    asset = next(asset for asset in canonical.assets if asset.id == asset_id)
    removed_edges = set(asset.served_edge_ids)
    canonical.edges = [edge for edge in canonical.edges if edge.id not in removed_edges]
    asset.served_edge_ids = []
    assert "DISCONNECTED_TRANSITION_ASSET" in error_codes(canonical)


def test_duplicate_undirected_edge_is_rejected(canonical):
    duplicate = deepcopy(canonical.edges[0])
    duplicate.id = "E_DUPLICATE"
    duplicate.from_node_id, duplicate.to_node_id = duplicate.to_node_id, duplicate.from_node_id
    canonical.edges.append(duplicate)
    assert "DUPLICATE_UNDIRECTED_EDGE" in error_codes(canonical)


def test_missing_asset_dependency_is_rejected(canonical):
    canonical.edges[0].dependent_asset_ids = ["UNKNOWN"]
    assert "UNKNOWN_DEPENDENT_ASSET" in error_codes(canonical)
