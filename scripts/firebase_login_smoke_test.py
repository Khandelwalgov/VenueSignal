#!/usr/bin/env python3
"""Sign in locally with Firebase email/password and verify VenueSignal identity without printing tokens."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from auth_smoke_test import verify_identity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://localhost:8000/api")
    parser.add_argument("--expect-role", choices=("CONTROLLER", "VIEWER"), default="CONTROLLER")
    parser.add_argument(
        "--auth-only",
        action="store_true",
        help="Verify Firebase email/password sign-in without calling VenueSignal",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.getenv("NEXT_PUBLIC_FIREBASE_API_KEY") or os.getenv("VENUESIGNAL_FIREBASE_WEB_API_KEY")
    email = os.getenv("VENUESIGNAL_DEMO_ADMIN_EMAIL", "admin@venuesignal.com")
    password = os.getenv("VENUESIGNAL_DEMO_ADMIN_PASSWORD")
    if not api_key or not password:
        print(
            "Firebase login smoke test: FAIL (set NEXT_PUBLIC_FIREBASE_API_KEY and VENUESIGNAL_DEMO_ADMIN_PASSWORD)",
            file=sys.stderr,
        )
        return 2
    endpoint = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?" + urllib.parse.urlencode(
        {"key": api_key}
    )
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"email": email, "password": password, "returnSecureToken": True}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            login = json.load(response)
            token = login.get("idToken")
        if not token:
            raise RuntimeError("Firebase did not return an ID token")
        if args.auth_only:
            print("Firebase login smoke test: PASS")
            print(f"Email: {login.get('email', email)}")
            return 0
        identity = verify_identity(args.api_base, token, args.expect_role)
    except urllib.error.HTTPError as error:
        print(f"Firebase login smoke test: FAIL (HTTP {error.code})", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Firebase login smoke test: FAIL ({error})", file=sys.stderr)
        return 1
    print("Firebase login smoke test: PASS")
    print(f"UID: {identity['uid']}")
    print(f"Display name: {identity['displayName']}")
    print(f"Role: {identity['role']}")
    print(f"Auth mode: {identity['authMode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
