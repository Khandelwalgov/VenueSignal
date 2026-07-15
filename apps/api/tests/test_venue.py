import json

import pytest
from fastapi.testclient import TestClient

from app.domain.venue.models import Venue
from app.domain.venue.service import DEFAULT_VENUE_PATH, VenueService
from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_and_readiness(client):
    assert client.get("/health").json()["status"] == "ok"
    readiness = client.get("/ready")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready", "venueGraphValid": True}


def test_get_venues(client):
    response = client.get("/api/venues")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "unity-stadium"


def test_get_venue_metadata(client):
    response = client.get("/api/venues/unity-stadium")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert data["statistics"]["connectedComponents"] == 1
    assert data["statistics"]["isolatedNodes"] == 0


def test_get_graph_and_validation(client):
    graph = client.get("/api/venues/unity-stadium/graph")
    validation = client.get("/api/venues/unity-stadium/validation")
    assert graph.status_code == 200
    assert len(graph.json()["levels"]) == 3
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert validation.json()["errors"] == []


def test_level_two_includes_multi_level_lift(client):
    response = client.get("/api/venues/unity-stadium/levels/L2")
    assert response.status_code == 200
    asset_ids = {asset["id"] for asset in response.json()["assets"]}
    assert "A_LIFT_2" in asset_ids
    assert "A_LIFT_3" in asset_ids


def test_asset_details_expose_relationships(client):
    response = client.get("/api/venues/unity-stadium/assets/A_LIFT_2")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"]["id"] == "A_LIFT_2"
    assert data["servedLevelIds"] == ["L0", "L1", "L2"]
    assert "E_LIFT2_L1_L2" in data["dependentEdgeIds"]
    assert "Z_L2_W_CONCOURSE" in data["servedZoneIds"]


def test_zone_node_and_accessibility_endpoints(client):
    zone = client.get("/api/venues/unity-stadium/zones/Z_L2_W_CONCOURSE")
    node = client.get("/api/venues/unity-stadium/nodes/N_L2_W3")
    summary = client.get("/api/venues/unity-stadium/accessibility-summary")
    assert zone.status_code == 200
    assert node.status_code == 200
    assert summary.status_code == 200
    assert summary.json()["allDesignatedDestinationsReachable"] is True
    checks = {
        item["destinationNodeId"]: item["reachableStepFree"]
        for item in summary.json()["checks"]
    }
    assert checks["N_L2_SEC_209_218"] is True
    assert checks["N_L2_WAIT_2"] is True


@pytest.mark.parametrize(
    ("path", "expected_detail"),
    [
        ("/api/venues/unknown", "Venue not found"),
        ("/api/venues/unity-stadium/levels/UNKNOWN", "Level not found"),
        ("/api/venues/unity-stadium/assets/UNKNOWN", "Asset not found"),
        ("/api/venues/unity-stadium/zones/UNKNOWN", "Zone not found"),
        ("/api/venues/unity-stadium/nodes/UNKNOWN", "Node not found"),
    ],
)
def test_not_found_responses(client, path, expected_detail):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["detail"] == expected_detail


def test_missing_canonical_file_blocks_startup(tmp_path):
    application = create_app(VenueService(venue_path=tmp_path / "missing.json"))
    with pytest.raises(FileNotFoundError, match="Canonical venue file not found"):
        with TestClient(application):
            pass


def test_malformed_json_blocks_startup(tmp_path):
    venue_path = tmp_path / "malformed.json"
    venue_path.write_text("{not-json", encoding="utf-8")
    application = create_app(VenueService(venue_path=venue_path))
    with pytest.raises(json.JSONDecodeError):
        with TestClient(application):
            pass


def test_invalid_graph_blocks_startup():
    venue = Venue.model_validate_json(DEFAULT_VENUE_PATH.read_text(encoding="utf-8"))
    venue.nodes[0].x = -1
    application = create_app(VenueService(venue=venue))
    with pytest.raises(ValueError, match="INVALID_COORDINATE"):
        with TestClient(application):
            pass
