#!/usr/bin/env python3
"""Verify a Firebase ID token against VenueSignal's server-authenticated identity endpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://localhost:8000/api")
    parser.add_argument("--firebase-id-token", default=os.getenv("VENUESIGNAL_FIREBASE_ID_TOKEN"))
    parser.add_argument("--expect-role", choices=("CONTROLLER", "VIEWER"), default="CONTROLLER")
    return parser.parse_args()


def verify_identity(api_base: str, token: str, expected_role: str) -> dict:
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/auth/me",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Identity endpoint returned HTTP {response.status}")
        identity = json.load(response)
    if identity.get("authMode") != "firebase":
        raise RuntimeError("Identity endpoint did not report Firebase authentication")
    if identity.get("role") != expected_role:
        raise RuntimeError(f"Expected role {expected_role}, received {identity.get('role', 'missing')}")
    return identity


def main() -> int:
    args = parse_args()
    if not args.firebase_id_token:
        print("Auth smoke test: FAIL (set VENUESIGNAL_FIREBASE_ID_TOKEN or pass --firebase-id-token)", file=sys.stderr)
        return 2
    try:
        identity = verify_identity(args.api_base, args.firebase_id_token, args.expect_role)
    except urllib.error.HTTPError as error:
        print(f"Auth smoke test: FAIL (HTTP {error.code})", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Auth smoke test: FAIL ({error})", file=sys.stderr)
        return 1
    print("Auth smoke test: PASS")
    print(f"UID: {identity['uid']}")
    print(f"Display name: {identity['displayName']}")
    print(f"Role: {identity['role']}")
    print(f"Auth mode: {identity['authMode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
