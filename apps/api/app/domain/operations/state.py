from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from app.domain.operations.models import (
    OperationalEvent,
    OperationalEventType,
    OperationalState,
)
from app.domain.venue.enums import AssetStatus, EdgeStatus
from app.domain.venue.models import Venue
from app.domain.operations.repository import (
    InMemoryOperationalStateRepository,
    OperationalStateRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OperationalStateService:
    """Thread-safe in-memory overlay; canonical venue definitions remain immutable."""

    def __init__(
        self,
        venue: Venue,
        repository: OperationalStateRepository | None = None,
    ) -> None:
        self._venue = venue
        self._lock = RLock()
        self._repository = repository or InMemoryOperationalStateRepository()
        self._state = self._repository.load() or OperationalState(last_updated_at=_now())
        self._repository.save(self._state)

    def snapshot(self) -> OperationalState:
        with self._lock:
            return self._state.model_copy(deep=True)

    def _record(
        self,
        event_type: OperationalEventType,
        *,
        entity_id: str | None,
        previous_value: str | float | None,
        new_value: str | float | None,
        source: str,
    ) -> None:
        self._state.context_version += 1
        self._state.last_updated_at = _now()
        self._state.event_history.append(
            OperationalEvent(
                id=f"EVT-{uuid4().hex[:10].upper()}",
                event_type=event_type,
                entity_id=entity_id,
                previous_value=previous_value,
                new_value=new_value,
                context_version=self._state.context_version,
                occurred_at=self._state.last_updated_at,
                source=source,
            )
        )
        self._repository.save(self._state)

    def set_asset_status(
        self, asset_id: str, status: AssetStatus, source: str = "EVALUATOR"
    ) -> OperationalState:
        asset = next((item for item in self._venue.assets if item.id == asset_id), None)
        if asset is None:
            raise KeyError(f"Unknown asset: {asset_id}")
        with self._lock:
            previous = self._state.asset_status_overrides.get(asset_id, asset.status)
            self._state.asset_status_overrides[asset_id] = status
            self._record(
                OperationalEventType.ASSET_STATUS_CHANGED,
                entity_id=asset_id,
                previous_value=previous.value,
                new_value=status.value,
                source=source,
            )
            return self.snapshot()

    def set_edge_status(
        self, edge_id: str, status: EdgeStatus, source: str = "EVALUATOR"
    ) -> OperationalState:
        edge = next((item for item in self._venue.edges if item.id == edge_id), None)
        if edge is None:
            raise KeyError(f"Unknown edge: {edge_id}")
        with self._lock:
            previous = self._state.edge_status_overrides.get(edge_id, edge.status)
            self._state.edge_status_overrides[edge_id] = status
            self._record(
                OperationalEventType.EDGE_STATUS_CHANGED,
                entity_id=edge_id,
                previous_value=previous.value,
                new_value=status.value,
                source=source,
            )
            return self.snapshot()

    def set_edge_crowd(
        self, edge_id: str, crowd_percent: float, source: str = "EVALUATOR"
    ) -> OperationalState:
        if not 0 <= crowd_percent <= 100:
            raise ValueError("Crowd percent must be between 0 and 100")
        edge = next((item for item in self._venue.edges if item.id == edge_id), None)
        if edge is None:
            raise KeyError(f"Unknown edge: {edge_id}")
        with self._lock:
            previous = self._state.edge_crowd_overrides.get(
                edge_id, edge.current_crowd_percent
            )
            self._state.edge_crowd_overrides[edge_id] = crowd_percent
            self._record(
                OperationalEventType.EDGE_CROWD_CHANGED,
                entity_id=edge_id,
                previous_value=previous,
                new_value=crowd_percent,
                source=source,
            )
            return self.snapshot()

    def reset(self, source: str = "EVALUATOR") -> OperationalState:
        with self._lock:
            previous_version = self._state.context_version
            history = list(self._state.event_history)
            self._state = OperationalState(
                context_version=previous_version,
                event_history=history,
                last_updated_at=_now(),
            )
            self._record(
                OperationalEventType.STATE_RESET,
                entity_id=None,
                previous_value=previous_version,
                new_value="BASE_STATE",
                source=source,
            )
            return self.snapshot()

    def effective_asset_status(self, asset_id: str) -> AssetStatus:
        state = self.snapshot()
        asset = next(item for item in self._venue.assets if item.id == asset_id)
        return state.asset_status_overrides.get(asset_id, asset.status)

    def effective_edge_status(self, edge_id: str) -> EdgeStatus:
        state = self.snapshot()
        edge = next(item for item in self._venue.edges if item.id == edge_id)
        return state.edge_status_overrides.get(edge_id, edge.status)
