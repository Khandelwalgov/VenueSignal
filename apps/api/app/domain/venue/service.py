from __future__ import annotations

import json
import os
from pathlib import Path

from app.domain.venue.models import (
    AccessibilityCheck,
    AccessibilitySummary,
    Asset,
    AssetDetails,
    Edge,
    LevelView,
    Venue,
    VenueSummary,
)
from app.domain.venue.validator import reachable_nodes, validate_venue_graph


DEFAULT_VENUE_PATH = (
    Path(__file__).resolve().parents[5]
    / "data"
    / "venues"
    / "unity-stadium.json"
)


class VenueService:
    """Own canonical venue loading and graph-derived read operations."""

    def __init__(
        self,
        venue_path: Path | str | None = None,
        venue: Venue | None = None,
    ) -> None:
        configured_path = os.getenv("VENUE_DATA_PATH")
        self.venue_path = Path(venue_path or configured_path or DEFAULT_VENUE_PATH)
        self._venue = venue
        self._validation_result = validate_venue_graph(venue) if venue else None

    @property
    def loaded(self) -> bool:
        return self._venue is not None and self._validation_result is not None

    def load_canonical_venue(self) -> Venue:
        if not self.venue_path.exists():
            raise FileNotFoundError(
                f"Canonical venue file not found: {self.venue_path}"
            )
        with self.venue_path.open("r", encoding="utf-8") as venue_file:
            data = json.load(venue_file)

        venue = Venue.model_validate(data)
        validation_result = validate_venue_graph(venue)
        if not validation_result.valid:
            summary = "; ".join(
                f"{issue.code}: {issue.message}" for issue in validation_result.errors
            )
            raise ValueError(f"Canonical venue failed graph validation: {summary}")

        self._venue = venue
        self._validation_result = validation_result
        return venue

    def ensure_loaded(self) -> None:
        if not self.loaded:
            self.load_canonical_venue()
        elif self._validation_result and not self._validation_result.valid:
            summary = "; ".join(
                f"{issue.code}: {issue.message}"
                for issue in self._validation_result.errors
            )
            raise ValueError(f"Canonical venue failed graph validation: {summary}")

    def get_venue(self) -> Venue:
        self.ensure_loaded()
        assert self._venue is not None
        return self._venue

    def get_validation_status(self):
        self.ensure_loaded()
        assert self._validation_result is not None
        return self._validation_result

    def get_summary(self) -> VenueSummary:
        venue = self.get_venue()
        validation = self.get_validation_status()
        return VenueSummary(
            id=venue.id,
            name=venue.name,
            description=venue.description,
            synthetic=venue.synthetic,
            schema_version=venue.schema_version,
            venue_version=venue.venue_version,
            status="OPERATIONAL" if validation.valid else "INVALID",
            statistics=validation.statistics,
        )

    def get_level(self, level_id: str) -> LevelView | None:
        venue = self.get_venue()
        level = next((item for item in venue.levels if item.id == level_id), None)
        if level is None:
            return None

        nodes = [node for node in venue.nodes if node.level_id == level_id]
        node_ids = {node.id for node in nodes}
        edges = [
            edge
            for edge in venue.edges
            if edge.from_node_id in node_ids or edge.to_node_id in node_ids
        ]
        edge_ids = {edge.id for edge in edges}
        assets = [
            asset
            for asset in venue.assets
            if asset.level_id == level_id
            or bool(node_ids.intersection(asset.served_node_ids))
            or bool(edge_ids.intersection(asset.served_edge_ids))
        ]
        return LevelView(
            level=level,
            zones=[zone for zone in venue.zones if zone.level_id == level_id],
            nodes=nodes,
            edges=edges,
            assets=assets,
        )

    def get_asset(self, asset_id: str) -> Asset | None:
        return next(
            (asset for asset in self.get_venue().assets if asset.id == asset_id),
            None,
        )

    def get_asset_details(self, asset_id: str) -> AssetDetails | None:
        venue = self.get_venue()
        asset = self.get_asset(asset_id)
        if asset is None:
            return None
        served_nodes = [
            node for node in venue.nodes if node.id in asset.served_node_ids
        ]
        served_edges = [
            edge for edge in venue.edges if edge.id in asset.served_edge_ids
        ]
        served_level_ids = sorted({node.level_id for node in served_nodes})
        served_zone_ids = sorted(
            {node.zone_id for node in served_nodes if node.zone_id is not None}
        )
        dependent_edge_ids = sorted(
            edge.id
            for edge in venue.edges
            if asset.id in edge.dependent_asset_ids
        )
        return AssetDetails(
            asset=asset,
            served_nodes=served_nodes,
            served_edges=served_edges,
            served_level_ids=served_level_ids,
            served_zone_ids=served_zone_ids,
            dependent_edge_ids=dependent_edge_ids,
        )

    def get_zone(self, zone_id: str):
        return next(
            (zone for zone in self.get_venue().zones if zone.id == zone_id),
            None,
        )

    def get_node(self, node_id: str):
        return next(
            (node for node in self.get_venue().nodes if node.id == node_id),
            None,
        )

    def get_accessibility_summary(self) -> AccessibilitySummary:
        venue = self.get_venue()
        nodes = {node.id: node for node in venue.nodes}
        reachable = reachable_nodes(
            venue,
            venue.configuration.accessible_entrance_node_ids,
            step_free=True,
        )
        checks = [
            AccessibilityCheck(
                destination_node_id=node_id,
                destination_label=nodes[node_id].label,
                reachable_step_free=node_id in reachable,
            )
            for node_id in venue.configuration.accessible_destination_node_ids
            if node_id in nodes
        ]
        return AccessibilitySummary(
            entrance_node_ids=venue.configuration.accessible_entrance_node_ids,
            checks=checks,
            all_designated_destinations_reachable=all(
                check.reachable_step_free for check in checks
            ),
        )
