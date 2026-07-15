from fastapi import APIRouter, HTTPException, Request

from app.domain.operations.models import (
    AssetStatusMutation,
    CrowdMutation,
    EdgeStatusMutation,
    OperationalEvent,
    OperationalState,
    RouteQuery,
    RouteResult,
)
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService


router = APIRouter()


def _state_service(request: Request) -> OperationalStateService:
    return request.app.state.operational_state_service


def _routing_service(request: Request) -> RoutingService:
    return request.app.state.routing_service


@router.get(
    "/state",
    response_model=OperationalState,
    summary="Read the current versioned operational overlay",
)
def get_state(request: Request) -> OperationalState:
    return _state_service(request).snapshot()


@router.get(
    "/events",
    response_model=list[OperationalEvent],
    summary="Read operational overlay event history",
)
def get_events(request: Request) -> list[OperationalEvent]:
    return _state_service(request).snapshot().event_history


@router.post(
    "/assets/{asset_id}/status",
    response_model=OperationalState,
    summary="Apply a validated asset-status override",
)
def set_asset_status(
    request: Request, asset_id: str, mutation: AssetStatusMutation
) -> OperationalState:
    try:
        return _state_service(request).set_asset_status(
            asset_id, mutation.status, mutation.source
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/edges/{edge_id}/status",
    response_model=OperationalState,
    summary="Apply a validated edge-status override",
)
def set_edge_status(
    request: Request, edge_id: str, mutation: EdgeStatusMutation
) -> OperationalState:
    try:
        return _state_service(request).set_edge_status(
            edge_id, mutation.status, mutation.source
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/edges/{edge_id}/crowd",
    response_model=OperationalState,
    summary="Apply a bounded synthetic crowd override",
)
def set_edge_crowd(
    request: Request, edge_id: str, mutation: CrowdMutation
) -> OperationalState:
    try:
        return _state_service(request).set_edge_crowd(
            edge_id, mutation.crowd_percent, mutation.source
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/reset",
    response_model=OperationalState,
    summary="Reset mutable overrides to the canonical base state",
)
def reset_state(request: Request) -> OperationalState:
    return _state_service(request).reset()


@router.post(
    "/routes/query",
    response_model=RouteResult,
    summary="Find a deterministic route under current operational constraints",
)
def query_route(request: Request, query: RouteQuery) -> RouteResult:
    state = _state_service(request).snapshot()
    return _routing_service(request).find_route(query, state)
