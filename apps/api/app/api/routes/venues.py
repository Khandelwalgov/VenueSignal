from fastapi import APIRouter, HTTPException, Request

from app.domain.venue.models import (
    AccessibilitySummary,
    AssetDetails,
    LevelView,
    Node,
    ValidationResult,
    Venue,
    VenueListItem,
    VenueSummary,
    Zone,
)
from app.domain.venue.service import VenueService


router = APIRouter()


def _service(request: Request) -> VenueService:
    return request.app.state.venue_service


def _require_venue(request: Request, venue_id: str) -> VenueService:
    service = _service(request)
    if service.get_venue().id != venue_id:
        raise HTTPException(status_code=404, detail="Venue not found")
    return service


@router.get(
    "",
    response_model=list[VenueListItem],
    summary="List available canonical venues",
)
def list_venues(request: Request) -> list[VenueListItem]:
    venue = _service(request).get_venue()
    return [
        VenueListItem(
            id=venue.id,
            name=venue.name,
            description=venue.description,
            synthetic=venue.synthetic,
        )
    ]


@router.get(
    "/{venue_id}",
    response_model=VenueSummary,
    summary="Get venue metadata and validated graph statistics",
)
def get_venue_metadata(request: Request, venue_id: str) -> VenueSummary:
    return _require_venue(request, venue_id).get_summary()


@router.get(
    "/{venue_id}/graph",
    response_model=Venue,
    summary="Get the complete validated canonical graph",
)
def get_venue_graph(request: Request, venue_id: str) -> Venue:
    return _require_venue(request, venue_id).get_venue()


@router.get(
    "/{venue_id}/levels/{level_id}",
    response_model=LevelView,
    summary="Get nodes, edges, zones, and multi-level assets for one level",
)
def get_level(request: Request, venue_id: str, level_id: str) -> LevelView:
    level_data = _require_venue(request, venue_id).get_level(level_id)
    if level_data is None:
        raise HTTPException(status_code=404, detail="Level not found")
    return level_data


@router.get(
    "/{venue_id}/assets/{asset_id}",
    response_model=AssetDetails,
    summary="Get an asset and its graph relationships",
)
def get_asset(request: Request, venue_id: str, asset_id: str) -> AssetDetails:
    asset = _require_venue(request, venue_id).get_asset_details(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get(
    "/{venue_id}/zones/{zone_id}",
    response_model=Zone,
    summary="Get one operational zone",
)
def get_zone(request: Request, venue_id: str, zone_id: str) -> Zone:
    zone = _require_venue(request, venue_id).get_zone(zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone


@router.get(
    "/{venue_id}/nodes/{node_id}",
    response_model=Node,
    summary="Get one graph node",
)
def get_node(request: Request, venue_id: str, node_id: str) -> Node:
    node = _require_venue(request, venue_id).get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.get(
    "/{venue_id}/validation",
    response_model=ValidationResult,
    summary="Get structured canonical graph validation results",
)
def get_validation(request: Request, venue_id: str) -> ValidationResult:
    return _require_venue(request, venue_id).get_validation_status()


@router.get(
    "/{venue_id}/accessibility-summary",
    response_model=AccessibilitySummary,
    summary="Get base-state step-free reachability for designated destinations",
)
def get_accessibility_summary(
    request: Request, venue_id: str
) -> AccessibilitySummary:
    return _require_venue(request, venue_id).get_accessibility_summary()
