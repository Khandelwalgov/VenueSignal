from __future__ import annotations

from app.domain.operations.state import OperationalStateService
from app.domain.venue.models import Venue
from app.domain.workflow.models import (
    ImpactAnalysis,
    PlanValidationError,
    PlanValidity,
    ResponsePlan,
)


ALLOWED_ACTION_TYPES = {
    "INSPECT_ASSET",
    "DISPATCH_ACCESSIBILITY_TEAM",
    "STAFF_VERIFIED_ROUTE",
    "ESTABLISH_WAITING_POINT",
    "VERIFY_ROUTE_STATUS",
}
KNOWN_TEAMS = {"MAINTENANCE", "ACCESSIBILITY_TEAM", "VENUE_OPERATIONS"}


class PlanValidator:
    """Validate tolerant AI plan output against authoritative domain state."""

    def __init__(
        self, venue: Venue, state_service: OperationalStateService
    ) -> None:
        self.state_service = state_service
        self.known_locations = {
            item.id
            for collection in (venue.assets, venue.nodes, venue.zones)
            for item in collection
        }

    def validate(
        self, plan: ResponsePlan, impact: ImpactAnalysis
    ) -> list[PlanValidationError]:
        errors: list[PlanValidationError] = []
        state = self.state_service.snapshot()
        if plan.context_version != state.context_version:
            errors.append(
                PlanValidationError(
                    code="STALE_CONTEXT_VERSION",
                    message=(
                        f"Plan context v{plan.context_version} is stale; "
                        f"current context is v{state.context_version}"
                    ),
                )
            )
        if plan.approved_at is not None or plan.approved_by is not None:
            errors.append(
                PlanValidationError(
                    code="MODEL_SELF_APPROVAL",
                    message="AI proposals cannot mark themselves approved",
                )
            )
        if not plan.actions:
            errors.append(
                PlanValidationError(
                    code="EMPTY_PLAN",
                    message="A response plan must contain at least one action",
                )
            )
        for index, action in enumerate(plan.actions):
            if action.action_type not in ALLOWED_ACTION_TYPES:
                errors.append(
                    PlanValidationError(
                        code="DISALLOWED_ACTION_TYPE",
                        message=f"Disallowed action type: {action.action_type}",
                        action_index=index,
                    )
                )
            if action.assigned_team not in KNOWN_TEAMS:
                errors.append(
                    PlanValidationError(
                        code="UNKNOWN_TEAM",
                        message=f"Unknown team: {action.assigned_team}",
                        action_index=index,
                    )
                )
            if action.location_id not in self.known_locations:
                errors.append(
                    PlanValidationError(
                        code="UNKNOWN_LOCATION",
                        message=f"Unknown action location: {action.location_id}",
                        action_index=index,
                    )
                )
            if any(
                dependency < 0 or dependency >= index
                for dependency in action.depends_on_action_indexes
            ):
                errors.append(
                    PlanValidationError(
                        code="INVALID_ACTION_DEPENDENCY",
                        message=(
                            "Action dependencies must reference an earlier action index"
                        ),
                        action_index=index,
                    )
                )
            if (
                action.action_type == "STAFF_VERIFIED_ROUTE"
                and not impact.route_result.found
            ):
                errors.append(
                    PlanValidationError(
                        code="NO_VERIFIED_ROUTE",
                        message=(
                            "A route action cannot be approved when no verified route exists"
                        ),
                        action_index=index,
                    )
                )
        if (
            not impact.route_result.found
            and plan.validity != PlanValidity.AWAITING_VERIFICATION
        ):
            errors.append(
                PlanValidationError(
                    code="INVALID_NO_ROUTE_VALIDITY",
                    message="A no-route plan must remain AWAITING_VERIFICATION",
                )
            )
        return errors
