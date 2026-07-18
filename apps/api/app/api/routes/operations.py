from fastapi import APIRouter, Depends, HTTPException, Request

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
from app.security.auth import Principal, current_principal, require_controller


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
def get_state(request: Request, _principal: Principal = Depends(current_principal)) -> OperationalState:
    return _state_service(request).snapshot()


@router.get(
    "/events",
    response_model=list[OperationalEvent],
    summary="Read operational overlay event history",
)
def get_events(request: Request, _principal: Principal = Depends(current_principal)) -> list[OperationalEvent]:
    return _state_service(request).snapshot().event_history


@router.post(
    "/assets/{asset_id}/status",
    response_model=OperationalState,
    summary="Apply a validated asset-status override",
)
def set_asset_status(
    request: Request,
    asset_id: str,
    mutation: AssetStatusMutation,
    principal: Principal = Depends(require_controller),
) -> OperationalState:
    try:
        result = _state_service(request).set_asset_status(
            asset_id, mutation.status, f"{principal.uid}:{mutation.source}"
        )
        request.app.state.workflow_service.reassess_changed_incidents()
        return result
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/edges/{edge_id}/status",
    response_model=OperationalState,
    summary="Apply a validated edge-status override",
)
def set_edge_status(
    request: Request,
    edge_id: str,
    mutation: EdgeStatusMutation,
    principal: Principal = Depends(require_controller),
) -> OperationalState:
    try:
        result = _state_service(request).set_edge_status(
            edge_id, mutation.status, f"{principal.uid}:{mutation.source}"
        )
        request.app.state.workflow_service.reassess_changed_incidents()
        return result
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/edges/{edge_id}/crowd",
    response_model=OperationalState,
    summary="Apply a bounded synthetic crowd override",
)
def set_edge_crowd(
    request: Request,
    edge_id: str,
    mutation: CrowdMutation,
    principal: Principal = Depends(require_controller),
) -> OperationalState:
    try:
        result = _state_service(request).set_edge_crowd(
            edge_id, mutation.crowd_percent, f"{principal.uid}:{mutation.source}"
        )
        request.app.state.workflow_service.reassess_changed_incidents()
        return result
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/reset",
    response_model=OperationalState,
    summary="Reset mutable overrides to the canonical base state",
)
def reset_state(
    request: Request, principal: Principal = Depends(require_controller)
) -> OperationalState:
    if not request.app.state.settings.demo_reset_enabled:
        raise HTTPException(status_code=403, detail="Demo reset is disabled in this environment")
    return _state_service(request).reset(f"{principal.uid}:RESET")


@router.post(
    "/routes/query",
    response_model=RouteResult,
    summary="Find a deterministic route under current operational constraints",
)
def query_route(
    request: Request,
    query: RouteQuery,
    _principal: Principal = Depends(current_principal),
) -> RouteResult:
    state = _state_service(request).snapshot()
    return _routing_service(request).find_route(query, state)
