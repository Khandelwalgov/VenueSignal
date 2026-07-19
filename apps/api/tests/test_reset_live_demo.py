from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[3] / "scripts" / "reset_live_demo.py"
SPEC = spec_from_file_location("reset_live_demo", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
RESET_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(RESET_MODULE)
inspect_demo = RESET_MODULE.inspect_demo
reset_demo = RESET_MODULE.reset_demo


class FakeReference:
    def __init__(self):
        self.deleted = False

    def delete(self):
        self.deleted = True


class FakeSnapshot:
    def __init__(self, exists=True):
        self.exists = exists
        self.reference = FakeReference()


class FakeDocument:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.payload = None

    def get(self):
        return self.snapshot

    def set(self, payload):
        self.payload = payload


class FakeCollection:
    def __init__(self, snapshots=None, document=None):
        self.snapshots = snapshots or []
        self._document = document

    def stream(self):
        return iter(self.snapshots)

    def document(self, document_id):
        assert document_id == "operational_state"
        return self._document


class FakeClient:
    def __init__(self):
        self.reports = FakeCollection([FakeSnapshot(), FakeSnapshot()])
        self.incidents = FakeCollection([FakeSnapshot()])
        self.state_document = FakeDocument(FakeSnapshot())
        self.system = FakeCollection(document=self.state_document)

    def collection(self, name):
        return {
            "venuesignal_reports": self.reports,
            "venuesignal_incidents": self.incidents,
            "venuesignal_system": self.system,
        }[name]


def test_operator_reset_clears_workflow_and_writes_canonical_state():
    client = FakeClient()
    reports, incidents, state_exists = inspect_demo(client, "venuesignal")

    assert len(reports) == 2
    assert len(incidents) == 1
    assert state_exists is True

    reset_demo(client, "venuesignal", reports, incidents)

    assert all(snapshot.reference.deleted for snapshot in [*reports, *incidents])
    payload = client.state_document.payload
    assert payload["context_version"] == 1
    assert payload["asset_status_overrides"] == {}
    assert payload["edge_status_overrides"] == {}
    assert payload["event_history"] == []
    assert isinstance(payload["last_updated_at"], datetime)
