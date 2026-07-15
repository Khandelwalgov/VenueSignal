from __future__ import annotations

import heapq
from collections import defaultdict
from math import inf

from app.domain.operations.models import (
    OperationalState,
    RouteConstraints,
    RouteQuery,
    RouteResult,
)
from app.domain.venue.enums import AssetStatus, EdgeStatus, NodeStatus
from app.domain.venue.models import Edge, Venue


NO_STEP_FREE_ROUTE = "No verified safe step-free route currently exists."


class RoutingService:
    def __init__(self, venue: Venue) -> None:
        self.venue = venue
        self.nodes = {node.id: node for node in venue.nodes}
        self.assets = {asset.id: asset for asset in venue.assets}

    def _edge_rejection(
        self,
        edge: Edge,
        state: OperationalState,
        constraints: RouteConstraints,
    ) -> str | None:
        status = state.edge_status_overrides.get(edge.id, edge.status)
        if status == EdgeStatus.CLOSED:
            return "CLOSED_EDGE"
        if edge.staff_only and not constraints.include_staff_only:
            return "STAFF_ONLY_EDGE"
        if constraints.step_free and (not edge.step_free or edge.contains_stairs):
            return "NOT_STEP_FREE"
        crowd = state.edge_crowd_overrides.get(edge.id, edge.current_crowd_percent)
        if constraints.maximum_crowd_percent is not None and crowd > constraints.maximum_crowd_percent:
            return "CROWD_LIMIT_EXCEEDED"
        for asset_id in edge.dependent_asset_ids:
            asset = self.assets.get(asset_id)
            if asset is None:
                return "UNKNOWN_DEPENDENCY"
            asset_status = state.asset_status_overrides.get(asset_id, asset.status)
            if asset_status not in {AssetStatus.OPERATIONAL, AssetStatus.DEGRADED}:
                return f"DEPENDENT_ASSET_UNAVAILABLE:{asset_id}"
        return None

    def find_route(self, query: RouteQuery, state: OperationalState) -> RouteResult:
        constraints = query.constraints
        if query.start_node_id not in self.nodes or query.destination_node_id not in self.nodes:
            unknown = query.start_node_id if query.start_node_id not in self.nodes else query.destination_node_id
            return RouteResult(
                found=False,
                rejected_reasons=[f"UNKNOWN_NODE:{unknown}"],
                message="Route cannot be evaluated because a graph node is unknown.",
                operational_context_version=state.context_version,
            )

        adjacency: dict[str, list[tuple[str, Edge]]] = defaultdict(list)
        rejected: set[str] = set()
        for edge in self.venue.edges:
            reason = self._edge_rejection(edge, state, constraints)
            if reason:
                rejected.add(reason)
                continue
            from_node = self.nodes[edge.from_node_id]
            to_node = self.nodes[edge.to_node_id]
            if from_node.status == NodeStatus.CLOSED or to_node.status == NodeStatus.CLOSED:
                rejected.add("CLOSED_NODE")
                continue
            if constraints.step_free and (not from_node.accessible or not to_node.accessible):
                rejected.add("INACCESSIBLE_NODE")
                continue
            adjacency[edge.from_node_id].append((edge.to_node_id, edge))
            adjacency[edge.to_node_id].append((edge.from_node_id, edge))

        start_state = (query.start_node_id, False)
        distances: dict[tuple[str, bool], float] = {start_state: 0}
        walked: dict[tuple[str, bool], float] = {start_state: 0}
        previous: dict[tuple[str, bool], tuple[tuple[str, bool], Edge]] = {}
        queue: list[tuple[float, str, bool]] = [(0, query.start_node_id, False)]
        target_state: tuple[str, bool] | None = None

        while queue:
            score, node_id, has_rest = heapq.heappop(queue)
            current_state = (node_id, has_rest)
            if score != distances.get(current_state, inf):
                continue
            if node_id == query.destination_node_id and (
                not constraints.require_rest_point or has_rest
            ):
                target_state = current_state
                break
            for candidate_id, edge in adjacency[node_id]:
                candidate_rest = has_rest or edge.has_rest_point
                candidate_state = (candidate_id, candidate_rest)
                candidate_walked = walked[current_state] + edge.distance_meters
                if (
                    constraints.maximum_distance_meters is not None
                    and candidate_walked > constraints.maximum_distance_meters
                ):
                    rejected.add("MAXIMUM_WALKING_DISTANCE_EXCEEDED")
                    continue
                crowd = state.edge_crowd_overrides.get(
                    edge.id, edge.current_crowd_percent
                )
                weight = edge.distance_meters * (1 + crowd / 250)
                if constraints.prefer_lower_noise:
                    weight *= {"LOW": 0.9, "MEDIUM": 1.05, "HIGH": 1.3}.get(
                        edge.noise_level, 1.1
                    )
                candidate_score = score + weight
                if candidate_score < distances.get(candidate_state, inf):
                    distances[candidate_state] = candidate_score
                    walked[candidate_state] = candidate_walked
                    previous[candidate_state] = (current_state, edge)
                    heapq.heappush(
                        queue, (candidate_score, candidate_id, candidate_rest)
                    )

        if target_state is None:
            if constraints.require_rest_point:
                rejected.add("REST_POINT_REQUIREMENT_UNSATISFIED")
            return RouteResult(
                found=False,
                rejected_reasons=sorted(rejected),
                message=NO_STEP_FREE_ROUTE if constraints.step_free else "No feasible route satisfies the requested constraints.",
                operational_context_version=state.context_version,
            )

        edge_path: list[Edge] = []
        node_path = [target_state[0]]
        cursor = target_state
        while cursor != start_state:
            prior, edge = previous[cursor]
            edge_path.append(edge)
            node_path.append(prior[0])
            cursor = prior
        edge_path.reverse()
        node_path.reverse()
        satisfied = []
        if constraints.step_free:
            satisfied.append("STEP_FREE")
        if not constraints.include_staff_only:
            satisfied.append("PUBLIC_ONLY")
        if constraints.maximum_distance_meters is not None:
            satisfied.append("MAXIMUM_WALKING_DISTANCE")
        if constraints.maximum_crowd_percent is not None:
            satisfied.append("CROWD_THRESHOLD")
        if constraints.require_rest_point:
            satisfied.append("REST_POINT")
        if constraints.prefer_lower_noise:
            satisfied.append("LOWER_NOISE_PREFERENCE")
        return RouteResult(
            found=True,
            node_ids=node_path,
            edge_ids=[edge.id for edge in edge_path],
            distance_meters=sum(edge.distance_meters for edge in edge_path),
            estimated_seconds=sum(edge.estimated_seconds for edge in edge_path),
            constraints_satisfied=satisfied,
            rejected_reasons=sorted(rejected),
            message="Verified route found using deterministic graph constraints.",
            operational_context_version=state.context_version,
        )
