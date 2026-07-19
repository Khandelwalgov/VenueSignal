#!/usr/bin/env python3
"""Perform an isolated write/read/delete check against live Firestore."""

from __future__ import annotations

import argparse
import os
import sys
from uuid import uuid4


COLLECTION = "venuesignal_smoke_tests"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        default=os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "venuesignal",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    document = None
    failure: Exception | None = None
    cleanup_failed = False
    try:
        from google.cloud import firestore

        client = firestore.Client(project=args.project)
        nonce = uuid4().hex
        document = client.collection(COLLECTION).document(f"smoke-{nonce}")
        expected = {"purpose": "venuesignal-live-smoke", "nonce": nonce}
        document.set(expected)
        snapshot = document.get()
        if not snapshot.exists or snapshot.to_dict() != expected:
            raise RuntimeError("Firestore read-back validation failed")
    except Exception as error:
        failure = error
    finally:
        if document is not None:
            try:
                document.delete()
            except Exception:
                cleanup_failed = True

    if failure is not None or cleanup_failed:
        reason = type(failure).__name__ if failure is not None else "CleanupError"
        print(f"Firestore smoke test: FAIL ({reason})", file=sys.stderr)
        return 1

    print("Firestore smoke test: PASS")
    print(f"Project: {args.project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
