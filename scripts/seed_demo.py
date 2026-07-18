#!/usr/bin/env python3
"""Seed the golden evaluator scenario through the same authenticated HTTP APIs as the UI."""

from __future__ import annotations

import json
import os
import urllib.request


API_BASE = os.getenv("VENUESIGNAL_API_BASE", "http://127.0.0.1:8000/api").rstrip("/")
TOKEN = os.getenv("VENUESIGNAL_TOKEN")
HTTP_TIMEOUT_SECONDS = float(os.getenv("VENUESIGNAL_HTTP_TIMEOUT_SECONDS", "90"))
REPORTS = [
    "Lift near Section 214 is stuck again. Two wheelchair users are waiting.",
    "Upper west accessible path is blocked, sending people toward Corridor W3.",
    "Crowd building near the west stairs after halftime.",
]


def post(path: str, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(payload or {}).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)


def main() -> None:
    post("/workflow/reset")
    created = [post("/workflow/reports", {"rawText": text, "source": "GOLDEN_SEED"}) for text in REPORTS]
    incident = post(
        "/workflow/incidents",
        {"reportIds": [created[0]["id"], created[1]["id"]], "confirmedAssetId": "A_LIFT_2"},
    )
    print(json.dumps({"reports": [item["id"] for item in created], "incident": incident["id"]}, indent=2))


if __name__ == "__main__":
    main()
