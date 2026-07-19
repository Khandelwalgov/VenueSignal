#!/usr/bin/env python3
"""Reset persisted VenueSignal demo data with human ADC credentials."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any


DEFAULT_PROJECT = "venuesignal"
DEFAULT_NAMESPACE = "venuesignal"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        default=os.getenv("FIREBASE_PROJECT_ID")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or DEFAULT_PROJECT,
    )
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Delete workflow documents and restore canonical operational state.",
    )
    parser.add_argument(
        "--confirm-project",
        help="Required with --execute; must exactly match --project.",
    )
    return parser.parse_args()


def inspect_demo(client: Any, namespace: str) -> tuple[list[Any], list[Any], bool]:
    reports = list(client.collection(f"{namespace}_reports").stream())
    incidents = list(client.collection(f"{namespace}_incidents").stream())
    operational = (
        client.collection(f"{namespace}_system")
        .document("operational_state")
        .get()
    )
    return reports, incidents, bool(operational.exists)


def reset_demo(
    client: Any,
    namespace: str,
    reports: list[Any],
    incidents: list[Any],
) -> None:
    for snapshot in (*reports, *incidents):
        snapshot.reference.delete()
    client.collection(f"{namespace}_system").document("operational_state").set(
        {
            "context_version": 1,
            "asset_status_overrides": {},
            "edge_status_overrides": {},
            "zone_status_overrides": {},
            "edge_crowd_overrides": {},
            "event_history": [],
            "last_updated_at": datetime.now(timezone.utc),
        }
    )


def main() -> int:
    args = parse_args()
    if args.execute and args.confirm_project != args.project:
        print(
            "Reset refused: --confirm-project must exactly match --project.",
            file=sys.stderr,
        )
        return 2

    try:
        from google.cloud import firestore

        client = firestore.Client(project=args.project)
        reports, incidents, state_exists = inspect_demo(client, args.namespace)
        print(f"Project: {args.project}")
        print(f"Reports: {len(reports)}")
        print(f"Incidents: {len(incidents)}")
        print(f"Operational state: {'present' if state_exists else 'absent'}")
        if not args.execute:
            print("Dry run only. Re-run with --execute and --confirm-project to reset.")
            return 0
        reset_demo(client, args.namespace, reports, incidents)
    except Exception as error:
        print(f"VenueSignal demo reset: FAIL ({type(error).__name__})", file=sys.stderr)
        return 1

    print("VenueSignal demo reset: PASS")
    print("The next API request will load the canonical base scenario.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
