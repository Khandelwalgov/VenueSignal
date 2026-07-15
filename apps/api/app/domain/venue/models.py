from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.venue.enums import AssetStatus, EdgeStatus, NodeStatus, ZoneStatus


class CamelModel(BaseModel):
    """Use snake_case internally and camelCase at JSON/API boundaries."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class VenueConfiguration(CamelModel):
    coordinate_min: float = 0
    coordinate_max: float = 1000
    primary_gate_node_ids: list[str] = Field(default_factory=list)
    accessible_entrance_node_ids: list[str] = Field(default_factory=list)
    accessible_destination_node_ids: list[str] = Field(default_factory=list)
    critical_public_node_ids: list[str] = Field(default_factory=list)


class Asset(CamelModel):
    id: str
    venue_id: str
    level_id: str
    zone_id: str | None = None
    type: str
    label: str
    status: AssetStatus
    accessibility_critical: bool
    served_node_ids: list[str] = Field(default_factory=list)
    served_edge_ids: list[str] = Field(default_factory=list)
    last_updated_at: datetime | None = None
    text_description: str


class Node(CamelModel):
    id: str
    venue_id: str
    level_id: str
    zone_id: str | None = None
    label: str
    type: str
    x: float
    y: float
    accessible: bool
    staff_only: bool
    capacity: int
    status: NodeStatus
    asset_id: str | None = None
    text_description: str


class Edge(CamelModel):
    id: str
    from_node_id: str
    to_node_id: str
    distance_meters: float
    estimated_seconds: float
    step_free: bool
    contains_stairs: bool
    slope_category: str
    width_class: str
    maximum_capacity: int
    current_crowd_percent: float
    staff_only: bool
    status: EdgeStatus
    dependent_asset_ids: list[str] = Field(default_factory=list)
    noise_level: str
    has_rest_point: bool
    text_description: str


class Zone(CamelModel):
    id: str
    venue_id: str
    level_id: str
    label: str
    type: str
    capacity: int
    occupancy_percent: float
    status: ZoneStatus
    node_ids: list[str] = Field(default_factory=list)
    asset_ids: list[str] = Field(default_factory=list)


class Level(CamelModel):
    id: str
    venue_id: str
    label: str
    index: int
    description: str


class Venue(CamelModel):
    id: str
    name: str
    description: str
    synthetic: bool
    schema_version: str = "1.0"
    venue_version: str = "1.0"
    configuration: VenueConfiguration = Field(default_factory=VenueConfiguration)
    levels: list[Level]
    zones: list[Zone]
    nodes: list[Node]
    edges: list[Edge]
    assets: list[Asset]


class ValidationIssue(CamelModel):
    code: str
    message: str
    severity: str
    entity_type: str | None = None
    entity_id: str | None = None
    related_ids: list[str] = Field(default_factory=list)


class ValidationResult(CamelModel):
    valid: bool = True
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Compatibility alias for the original service API."""

        return self.valid

    def add_error(
        self,
        code: str,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        related_ids: list[str] | None = None,
    ) -> None:
        self.valid = False
        self.errors.append(
            ValidationIssue(
                code=code,
                message=message,
                severity="ERROR",
                entity_type=entity_type,
                entity_id=entity_id,
                related_ids=related_ids or [],
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        related_ids: list[str] | None = None,
    ) -> None:
        self.warnings.append(
            ValidationIssue(
                code=code,
                message=message,
                severity="WARNING",
                entity_type=entity_type,
                entity_id=entity_id,
                related_ids=related_ids or [],
            )
        )


class VenueListItem(CamelModel):
    id: str
    name: str
    description: str
    synthetic: bool


class VenueSummary(VenueListItem):
    schema_version: str
    venue_version: str
    status: str
    statistics: dict[str, Any]


class LevelView(CamelModel):
    level: Level
    zones: list[Zone]
    nodes: list[Node]
    edges: list[Edge]
    assets: list[Asset]


class AssetDetails(CamelModel):
    asset: Asset
    served_nodes: list[Node]
    served_edges: list[Edge]
    served_level_ids: list[str]
    served_zone_ids: list[str]
    dependent_edge_ids: list[str]


class AccessibilityCheck(CamelModel):
    destination_node_id: str
    destination_label: str
    reachable_step_free: bool


class AccessibilitySummary(CamelModel):
    entrance_node_ids: list[str]
    checks: list[AccessibilityCheck]
    all_designated_destinations_reachable: bool
