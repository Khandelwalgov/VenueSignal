import pytest
from fastapi.testclient import TestClient

from app.domain.operations.models import RouteConstraints, RouteQuery
from app.domain.operations.repository import InMemoryOperationalStateRepository
from app.domain.operations.routing import NO_STEP_FREE_ROUTE, RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.enums import AssetStatus, EdgeStatus
from app.domain.venue.service import VenueService
from app.main import create_app


@pytest.fixture
def venue():
    service = VenueService()
    return service.load_canonical_venue()


@pytest.fixture
def operations(venue):
    return OperationalStateService(venue)


@pytest.fixture
def route_query():
    return RouteQuery(
        start_node_id="N_L0_W_ACC_ENT",
        destination_node_id="N_L2_SEC_209_218",
        constraints=RouteConstraints(step_free=True),
    )


def test_operational_mutations_increment_context_and_preserve_canonical(venue, operations):
    original = next(asset for asset in venue.assets if asset.id == "A_LIFT_2")
    first = operations.set_asset_status("A_LIFT_2", AssetStatus.OUT_OF_SERVICE)
    second = operations.set_edge_status("E_L2_WCEN_TO_W3", EdgeStatus.RESTRICTED)
    third = operations.set_edge_crowd("E_L1_PUBLIC_CROSS", 88)
    assert (first.context_version, second.context_version, third.context_version) == (2, 3, 4)
    assert original.status == AssetStatus.OPERATIONAL
    assert len(third.event_history) == 3


def test_separate_service_instances_refresh_shared_operational_state(venue):
    repository = InMemoryOperationalStateRepository()
    first = OperationalStateService(venue, repository)
    second = OperationalStateService(venue, repository)

    first.set_asset_status("A_LIFT_2", AssetStatus.OUT_OF_SERVICE)
    refreshed = second.snapshot()

    assert refreshed.context_version == 2
    assert refreshed.asset_status_overrides["A_LIFT_2"] == AssetStatus.OUT_OF_SERVICE

    first.reset("OPERATOR_RESET")
    restored = second.snapshot()
    assert restored.context_version == 3
    assert restored.asset_status_overrides == {}


def test_golden_route_state_sequence(venue, operations, route_query):
    routing = RoutingService(venue)
    base = routing.find_route(route_query, operations.snapshot())
    assert base.found is True
    assert "E_LIFT2_L1_L2" in base.edge_ids
    assert base.operational_context_version == 1

    operations.set_asset_status("A_LIFT_2", AssetStatus.OUT_OF_SERVICE)
    fallback = routing.find_route(route_query, operations.snapshot())
    assert fallback.found is True
    assert "E_W3_FALLBACK_RAMP" in fallback.edge_ids
    assert "E_LIFT2_L1_L2" not in fallback.edge_ids
    assert fallback.distance_meters > base.distance_meters

    operations.set_asset_status("A_CORRIDOR_W3", AssetStatus.OUT_OF_SERVICE)
    unavailable = routing.find_route(route_query, operations.snapshot())
    assert unavailable.found is False
    assert unavailable.message == NO_STEP_FREE_ROUTE
    assert unavailable.operational_context_version == 3

    reset = operations.reset()
    restored = routing.find_route(route_query, reset)
    assert restored.found is True
    assert "E_LIFT2_L1_L2" in restored.edge_ids
    assert reset.context_version == 4


def test_staff_only_route_is_never_used_without_permission(venue, operations):
    query = RouteQuery(
        start_node_id="N_L1_E_CEN",
        destination_node_id="N_L1_W_CEN",
        constraints=RouteConstraints(step_free=True),
    )
    public = RoutingService(venue).find_route(query, operations.snapshot())
    assert public.found is True
    assert "E_STAFF_SHORTCUT" not in public.edge_ids

    query.constraints.include_staff_only = True
    query.constraints.maximum_distance_meters = 160
    authorised = RoutingService(venue).find_route(query, operations.snapshot())
    assert authorised.edge_ids == ["E_STAFF_SHORTCUT"]


def test_walking_and_crowd_constraints_return_rejection_reasons(venue, operations):
    query = RouteQuery(
        start_node_id="N_L0_W_ACC_ENT",
        destination_node_id="N_L2_SEC_209_218",
        constraints=RouteConstraints(
            step_free=True,
            maximum_distance_meters=100,
            maximum_crowd_percent=5,
        ),
    )
    result = RoutingService(venue).find_route(query, operations.snapshot())
    assert result.found is False
    assert "MAXIMUM_WALKING_DISTANCE_EXCEEDED" in result.rejected_reasons
    assert "CROWD_LIMIT_EXCEEDED" in result.rejected_reasons


def test_rest_point_constraint_is_satisfied(venue, operations):
    query = RouteQuery(
        start_node_id="N_L0_W_ACC_ENT",
        destination_node_id="N_L2_SEC_209_218",
        constraints=RouteConstraints(step_free=True, require_rest_point=True),
    )
    result = RoutingService(venue).find_route(query, operations.snapshot())
    assert result.found is True
    assert "REST_POINT" in result.constraints_satisfied


def test_unknown_entities_are_rejected(operations):
    with pytest.raises(KeyError, match="Unknown asset"):
        operations.set_asset_status("UNKNOWN", AssetStatus.OUT_OF_SERVICE)
    with pytest.raises(KeyError, match="Unknown edge"):
        operations.set_edge_status("UNKNOWN", EdgeStatus.CLOSED)


def test_operations_api_golden_sequence():
    with TestClient(create_app()) as client:
        initial = client.get("/api/operations/state").json()
        assert initial["contextVersion"] == 1

        route_payload = {
            "startNodeId": "N_L0_W_ACC_ENT",
            "destinationNodeId": "N_L2_SEC_209_218",
            "constraints": {"stepFree": True},
        }
        base = client.post("/api/operations/routes/query", json=route_payload).json()
        assert base["found"] is True

        lift_state = client.post(
            "/api/operations/assets/A_LIFT_2/status",
            json={"status": "OUT_OF_SERVICE", "source": "GOLDEN_TEST"},
        )
        assert lift_state.status_code == 200
        fallback = client.post("/api/operations/routes/query", json=route_payload).json()
        assert "E_W3_FALLBACK_RAMP" in fallback["edgeIds"]

        corridor_state = client.post(
            "/api/operations/assets/A_CORRIDOR_W3/status",
            json={"status": "OUT_OF_SERVICE", "source": "GOLDEN_TEST"},
        )
        assert corridor_state.json()["contextVersion"] == 3
        unavailable = client.post("/api/operations/routes/query", json=route_payload).json()
        assert unavailable["found"] is False
        assert unavailable["message"] == NO_STEP_FREE_ROUTE
        assert len(client.get("/api/operations/events").json()) == 2

        reset = client.post("/api/operations/reset").json()
        assert reset["assetStatusOverrides"] == {}
        assert reset["contextVersion"] == 4


def test_operations_api_validates_bounds_and_unknown_asset():
    with TestClient(create_app()) as client:
        invalid_crowd = client.post(
            "/api/operations/edges/E_L1_PUBLIC_CROSS/crowd",
            json={"crowdPercent": 101},
        )
        unknown_asset = client.post(
            "/api/operations/assets/UNKNOWN/status",
            json={"status": "OUT_OF_SERVICE"},
        )
        assert invalid_crowd.status_code == 422
        assert unknown_asset.status_code == 404
