from __future__ import annotations

from app.domain.operations.models import RouteConstraints, RouteQuery
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.models import Venue
from app.domain.workflow.models import ImpactAnalysis


GOLDEN_ROUTE_START_NODE_ID = "N_L0_W_ACC_ENT"
GOLDEN_ROUTE_DESTINATION_NODE_ID = "N_L2_SEC_209_218"
GOLDEN_FALLBACK_EDGE_ID = "E_W3_FALLBACK_RAMP"


class ImpactAnalyzer:
    """Derive deterministic operational and accessibility impact for a venue asset."""

    def __init__(
        self,
        venue: Venue,
        state_service: OperationalStateService,
        routing_service: RoutingService,
    ) -> None:
        self.venue = venue
        self.state_service = state_service
        self.routing_service = routing_service

    @staticmethod
    def golden_route_query() -> RouteQuery:
        return RouteQuery(
            start_node_id=GOLDEN_ROUTE_START_NODE_ID,
            destination_node_id=GOLDEN_ROUTE_DESTINATION_NODE_ID,
            constraints=RouteConstraints(step_free=True),
        )

    def analyze(self, asset_id: str) -> ImpactAnalysis:
        asset = next(asset for asset in self.venue.assets if asset.id == asset_id)
        state = self.state_service.snapshot()
        route = self.routing_service.find_route(self.golden_route_query(), state)
        served_nodes = set(asset.served_node_ids)
        served_edges = set(asset.served_edge_ids)
        dependent_edges = {
            edge.id
            for edge in self.venue.edges
            if asset_id in edge.dependent_asset_ids
        }
        zones = sorted(
            {
                node.zone_id
                for node in self.venue.nodes
                if node.id in served_nodes and node.zone_id
            }
        )
        consequences = ["Normal step-free access to Sections 209–218 is invalidated"]
        consequences.append(
            "A longer verified Corridor W3 fallback remains available"
            if route.found and GOLDEN_FALLBACK_EDGE_ID in route.edge_ids
            else "No verified safe step-free route remains"
            if not route.found
            else "The normal step-free route remains available"
        )
        crowd_concerns = [
            (
                f"{edge.id} is at "
                f"{state.edge_crowd_overrides.get(edge.id, edge.current_crowd_percent):.0f}% "
                "synthetic crowd"
            )
            for edge in self.venue.edges
            if state.edge_crowd_overrides.get(
                edge.id, edge.current_crowd_percent
            )
            >= 80
        ]
        return ImpactAnalysis(
            affected_node_ids=sorted(served_nodes),
            affected_edge_ids=sorted(served_edges | dependent_edges),
            affected_zone_ids=zones,
            inaccessible_destination_ids=(
                [] if route.found else [GOLDEN_ROUTE_DESTINATION_NODE_ID]
            ),
            accessibility_consequences=consequences,
            route_result=route,
            rejected_route_reasons=route.rejected_reasons,
            crowd_capacity_concerns=crowd_concerns,
            required_capabilities=[
                "ACCESSIBILITY_TEAM",
                "VENUE_OPERATIONS",
                "MAINTENANCE",
            ],
            context_version=state.context_version,
        )
