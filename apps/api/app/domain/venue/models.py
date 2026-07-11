from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from app.domain.venue.enums import NodeStatus, EdgeStatus, AssetStatus, ZoneStatus

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

class Asset(CamelModel):
    id: str
    venue_id: str
    level_id: str
    zone_id: Optional[str] = None
    type: str
    label: str
    status: AssetStatus
    accessibility_critical: bool
    served_node_ids: List[str] = Field(default_factory=list)
    served_edge_ids: List[str] = Field(default_factory=list)
    text_description: str

class Node(CamelModel):
    id: str
    venue_id: str
    level_id: str
    zone_id: Optional[str] = None
    label: str
    type: str
    x: float
    y: float
    accessible: bool
    staff_only: bool
    capacity: int = Field(ge=0)
    status: NodeStatus
    asset_id: Optional[str] = None
    text_description: str

class Edge(CamelModel):
    id: str
    from_node_id: str
    to_node_id: str
    distance_meters: float = Field(gt=0)
    estimated_seconds: float = Field(gt=0)
    step_free: bool
    contains_stairs: bool
    slope_category: str
    width_class: str
    maximum_capacity: int = Field(ge=0)
    current_crowd_percent: float = Field(ge=0.0, le=100.0)
    staff_only: bool
    status: EdgeStatus
    dependent_asset_ids: List[str] = Field(default_factory=list)
    noise_level: str
    has_rest_point: bool
    text_description: str

class Zone(CamelModel):
    id: str
    venue_id: str
    level_id: str
    label: str
    type: str
    capacity: int = Field(ge=0)
    occupancy_percent: float = Field(ge=0.0, le=100.0)
    status: ZoneStatus
    node_ids: List[str] = Field(default_factory=list)
    asset_ids: List[str] = Field(default_factory=list)

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
    levels: List[Level]
    zones: List[Zone]
    nodes: List[Node]
    edges: List[Edge]
    assets: List[Asset]
