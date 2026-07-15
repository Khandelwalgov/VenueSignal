from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.domain.venue.enums import AssetStatus, EdgeStatus, ZoneStatus
from app.domain.venue.models import CamelModel


class OperationalEventType(str, Enum):
    ASSET_STATUS_CHANGED = "ASSET_STATUS_CHANGED"
    EDGE_STATUS_CHANGED = "EDGE_STATUS_CHANGED"
    EDGE_CROWD_CHANGED = "EDGE_CROWD_CHANGED"
    STATE_RESET = "STATE_RESET"


class OperationalEvent(CamelModel):
    id: str
    event_type: OperationalEventType
    entity_id: str | None = None
    previous_value: str | float | None = None
    new_value: str | float | None = None
    context_version: int
    occurred_at: datetime
    source: str = "EVALUATOR"
    synthetic: bool = True


class OperationalState(CamelModel):
    context_version: int = 1
    asset_status_overrides: dict[str, AssetStatus] = Field(default_factory=dict)
    edge_status_overrides: dict[str, EdgeStatus] = Field(default_factory=dict)
    zone_status_overrides: dict[str, ZoneStatus] = Field(default_factory=dict)
    edge_crowd_overrides: dict[str, float] = Field(default_factory=dict)
    event_history: list[OperationalEvent] = Field(default_factory=list)
    last_updated_at: datetime


class AssetStatusMutation(CamelModel):
    status: AssetStatus
    source: str = Field(default="EVALUATOR", max_length=80)


class EdgeStatusMutation(CamelModel):
    status: EdgeStatus
    source: str = Field(default="EVALUATOR", max_length=80)


class CrowdMutation(CamelModel):
    crowd_percent: float = Field(ge=0, le=100)
    source: str = Field(default="EVALUATOR", max_length=80)


class RouteConstraints(CamelModel):
    step_free: bool = False
    include_staff_only: bool = False
    maximum_distance_meters: float | None = Field(default=None, gt=0)
    maximum_crowd_percent: float | None = Field(default=None, ge=0, le=100)
    require_rest_point: bool = False
    prefer_lower_noise: bool = False


class RouteQuery(CamelModel):
    start_node_id: str
    destination_node_id: str
    constraints: RouteConstraints = Field(default_factory=RouteConstraints)


class RouteResult(CamelModel):
    found: bool
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    distance_meters: float = 0
    estimated_seconds: float = 0
    constraints_satisfied: list[str] = Field(default_factory=list)
    rejected_reasons: list[str] = Field(default_factory=list)
    message: str
    operational_context_version: int
