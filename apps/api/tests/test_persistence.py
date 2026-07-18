from app.ai.local import LocalDemoAIProvider
from app.domain.operations.repository import (
    FirestoreOperationalStateRepository,
    SQLiteOperationalStateRepository,
)
from app.domain.operations.routing import RoutingService
from app.domain.operations.state import OperationalStateService
from app.domain.venue.enums import AssetStatus
from app.domain.venue.service import VenueService
from app.domain.workflow.models import IncidentCreate, ReportCreate
from app.domain.workflow.repository import FirestoreWorkflowRepository, SQLiteWorkflowRepository
from app.domain.workflow.service import WorkflowService


def test_sqlite_repositories_survive_service_recreation(tmp_path):
    database = tmp_path / "venuesignal.db"
    venue = VenueService().load_canonical_venue()
    state = OperationalStateService(venue, SQLiteOperationalStateRepository(database))
    workflow = WorkflowService(
        venue,
        state,
        RoutingService(venue),
        LocalDemoAIProvider(),
        SQLiteWorkflowRepository(database),
    )
    report = workflow.create_report(
        ReportCreate(raw_text="Lift L2 is stuck", idempotency_key="persistent-report-1")
    )
    incident = workflow.create_incident(
        IncidentCreate(report_ids=[report.id], confirmed_asset_id="A_LIFT_2")
    )

    restored_state = OperationalStateService(venue, SQLiteOperationalStateRepository(database))
    restored_workflow = WorkflowService(
        venue,
        restored_state,
        RoutingService(venue),
        LocalDemoAIProvider(),
        SQLiteWorkflowRepository(database),
    )
    assert restored_state.effective_asset_status("A_LIFT_2") == AssetStatus.OUT_OF_SERVICE
    assert restored_workflow.get_incident(incident.id).report_ids == [report.id]
    assert restored_workflow.create_report(
        ReportCreate(raw_text="different text", idempotency_key="persistent-report-1")
    ).id == report.id


def test_content_fingerprint_deduplicates_manual_reports(tmp_path):
    venue = VenueService().load_canonical_venue()
    state = OperationalStateService(venue)
    workflow = WorkflowService(venue, state, RoutingService(venue), LocalDemoAIProvider())
    first = workflow.create_report(ReportCreate(raw_text="  Lift L2 IS stuck  "))
    second = workflow.create_report(ReportCreate(raw_text="lift l2 is   stuck"))
    assert second.id == first.id
    assert len(workflow.list_reports()) == 1


class FakeSnapshot:
    def __init__(self, document):
        self.reference = document
        self.exists = document.document_id in document.collection.data

    def to_dict(self):
        return self.reference.collection.data.get(self.reference.document_id)


class FakeDocument:
    def __init__(self, collection, document_id):
        self.collection = collection
        self.document_id = document_id

    def get(self):
        return FakeSnapshot(self)

    def set(self, payload):
        self.collection.data[self.document_id] = payload

    def delete(self):
        self.collection.data.pop(self.document_id, None)


class FakeQuery:
    def __init__(self, collection, field, value):
        self.collection = collection
        self.field = field
        self.value = value
        self.maximum = None

    def limit(self, maximum):
        self.maximum = maximum
        return self

    def stream(self):
        snapshots = [
            FakeSnapshot(FakeDocument(self.collection, document_id))
            for document_id, payload in self.collection.data.items()
            if payload.get(self.field) == self.value
        ]
        return iter(snapshots[:self.maximum] if self.maximum else snapshots)


class FakeCollection:
    def __init__(self):
        self.data = {}

    def document(self, document_id):
        return FakeDocument(self, document_id)

    def stream(self):
        return iter(FakeSnapshot(FakeDocument(self, document_id)) for document_id in list(self.data))

    def where(self, field, operator, value):
        assert operator == "=="
        return FakeQuery(self, field, value)


class FakeFirestoreClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        return self.collections.setdefault(name, FakeCollection())


def test_firestore_adapters_round_trip_without_live_credentials():
    client = FakeFirestoreClient()
    venue = VenueService().load_canonical_venue()
    state_repository = FirestoreOperationalStateRepository(client)
    workflow_repository = FirestoreWorkflowRepository(client)
    state = OperationalStateService(venue, state_repository)
    workflow = WorkflowService(
        venue, state, RoutingService(venue), LocalDemoAIProvider(), workflow_repository
    )
    report = workflow.create_report(ReportCreate(raw_text="Lift L2 is stuck"))
    incident = workflow.create_incident(
        IncidentCreate(report_ids=[report.id], confirmed_asset_id="A_LIFT_2")
    )

    restored_state = OperationalStateService(venue, FirestoreOperationalStateRepository(client))
    restored_repository = FirestoreWorkflowRepository(client)
    assert restored_state.effective_asset_status("A_LIFT_2") == AssetStatus.OUT_OF_SERVICE
    assert restored_repository.get_report(report.id).fingerprint == report.fingerprint
    assert restored_repository.find_report_by_fingerprint(report.fingerprint).id == report.id
    assert restored_repository.get_incident(incident.id).report_ids == [report.id]

    restored_repository.clear()
    assert restored_repository.list_reports() == []
    assert restored_repository.list_incidents() == []
