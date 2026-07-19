#!/usr/bin/env python3
"""Assign a supported VenueSignal role using Firebase Admin and ADC."""

from __future__ import annotations

import argparse
import os
import sys


SUPPORTED_ROLES = ("CONTROLLER", "VIEWER")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="Existing Firebase user email")
    parser.add_argument("--role", required=True, choices=SUPPORTED_ROLES, type=str.upper)
    return parser.parse_args()


def project_id() -> str:
    value = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not value:
        raise RuntimeError("Set FIREBASE_PROJECT_ID or GOOGLE_CLOUD_PROJECT before running this script")
    return value


def initialize_firebase(project: str):
    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(
            credentials.ApplicationDefault(),
            {"projectId": project},
        )


def main() -> int:
    args = parse_args()
    try:
        initialize_firebase(project_id())
        from firebase_admin import auth

        user = auth.get_user_by_email(args.email)
        claims = dict(user.custom_claims or {})
        claims["role"] = args.role
        auth.set_custom_user_claims(user.uid, claims)
        updated = auth.get_user(user.uid)
        resulting_role = str((updated.custom_claims or {}).get("role", "VIEWER")).upper()
        if resulting_role != args.role:
            raise RuntimeError("Firebase did not return the requested role claim")
    except Exception as error:
        print(f"Firebase role assignment: FAIL ({type(error).__name__})", file=sys.stderr)
        return 1

    print(f"Email: {updated.email}")
    print(f"UID: {updated.uid}")
    print(f"Role: {resulting_role}")
    print("Sign out and sign in again to obtain a fresh Firebase ID token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
