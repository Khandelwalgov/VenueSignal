from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Protocol

from app.domain.operations.models import OperationalState


class OperationalStateRepository(Protocol):
    def load(self) -> OperationalState | None: ...
    def save(self, state: OperationalState) -> None: ...


class InMemoryOperationalStateRepository:
    def __init__(self) -> None:
        self._state: OperationalState | None = None

    def load(self) -> OperationalState | None:
        return self._state.model_copy(deep=True) if self._state else None

    def save(self, state: OperationalState) -> None:
        self._state = state.model_copy(deep=True)


class SQLiteOperationalStateRepository:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._lock = RLock()
        with self._connection:
            self._connection.execute(
                "CREATE TABLE IF NOT EXISTS operational_state (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), payload TEXT NOT NULL)"
            )

    def load(self) -> OperationalState | None:
        with self._lock:
            row = self._connection.execute("SELECT payload FROM operational_state WHERE singleton = 1").fetchone()
        return OperationalState.model_validate_json(row[0]) if row else None

    def save(self, state: OperationalState) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT OR REPLACE INTO operational_state(singleton, payload) VALUES (1, ?)",
                (state.model_dump_json(),),
            )


class FirestoreOperationalStateRepository:
    def __init__(self, client: Any | None = None, namespace: str = "venuesignal") -> None:
        if client is None:
            from google.cloud import firestore

            client = firestore.Client()
        self.document = client.collection(f"{namespace}_system").document("operational_state")

    def load(self) -> OperationalState | None:
        snapshot = self.document.get()
        return OperationalState.model_validate(snapshot.to_dict()) if snapshot.exists else None

    def save(self, state: OperationalState) -> None:
        self.document.set(json.loads(state.model_dump_json()))
