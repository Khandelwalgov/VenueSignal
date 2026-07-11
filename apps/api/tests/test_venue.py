import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.venue.service import venue_service

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_venues():
    response = client.get("/api/venues/")
    assert response.status_code == 200
    venues = response.json()
    assert len(venues) == 1
    assert venues[0]["id"] == "unity-stadium"

def test_get_venue_metadata():
    response = client.get("/api/venues/unity-stadium")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "unity-stadium"
    assert "statistics" in data

def test_get_venue_graph():
    response = client.get("/api/venues/unity-stadium/graph")
    assert response.status_code == 200
    data = response.json()
    assert "levels" in data
    assert "nodes" in data
    assert "edges" in data

def test_get_venue_validation():
    response = client.get("/api/venues/unity-stadium/validation")
    assert response.status_code == 200
    data = response.json()
    assert data["isValid"] is True

def test_get_invalid_venue():
    response = client.get("/api/venues/unknown-venue")
    assert response.status_code == 404

def test_get_level():
    response = client.get("/api/venues/unity-stadium/levels/L0")
    assert response.status_code == 200
    data = response.json()
    assert data["level"]["id"] == "L0"
    assert len(data["nodes"]) > 0

def test_get_invalid_level():
    response = client.get("/api/venues/unity-stadium/levels/UNKNOWN")
    assert response.status_code == 404

def test_get_asset():
    response = client.get("/api/venues/unity-stadium/assets/A_LIFT_1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "A_LIFT_1"

def test_get_invalid_asset():
    response = client.get("/api/venues/unity-stadium/assets/UNKNOWN")
    assert response.status_code == 404
