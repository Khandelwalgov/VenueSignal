# Live Deployment Runbook

VenueSignal's final deployment is:

- Next.js frontend on Vercel
- FastAPI backend on Render
- Firebase Authentication
- Firestore persistence
- Gemini API

The browser uses Firebase only for email/password authentication and ID-token acquisition. It never receives Firebase Admin credentials, reads Firestore directly, or receives the Gemini key. Render verifies the Firebase bearer token and owns all Firestore and Gemini access.

The exact deployment settings and environment-variable split are in [DEPLOY.md](../DEPLOY.md).

## Firebase controller role

Assign the server-authoritative claim with human Application Default Credentials:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/set_firebase_role.py \
  --email YOUR_DEMO_EMAIL \
  --role CONTROLLER
```

After a claim change, sign out and sign in again so Firebase issues a fresh ID token. `GET /api/auth/me` must report `CONTROLLER`; the frontend does not select or assert its own role.

## Firestore validation

Run the isolated smoke test:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/firestore_smoke_test.py
```

The application collections are:

- `venuesignal_system`
- `venuesignal_reports`
- `venuesignal_incidents`

Deploy the checked-in deny-all client rules so Firestore remains server-only.

## Public judge access

Public demo credentials are optional and intentionally exposed in the browser bundle when enabled. Configure their three `NEXT_PUBLIC_*` values only in Vercel Production. Do not commit them to Git, place them in Render, persist them in local storage, or expose them through an API.

Firebase authentication remains real. The judge presses **Sign in**, Firebase validates the account, and FastAPI verifies the resulting ID token and `CONTROLLER` claim. The account must contain only synthetic demonstration data and must be rotated or removed after judging.

## Base-scenario reset

Production HTTP reset routes stay disabled. Preview and execute the operator reset with:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/reset_live_demo.py
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/reset_live_demo.py \
  --execute --confirm-project venuesignal
```

The reset removes persisted demo reports/incidents and restores canonical operational state without changing Firebase accounts.

## Final hosted acceptance

Verify in a fresh private browser window:

1. Render `/health` and `/ready` succeed.
2. Firebase sign-in succeeds.
3. `/api/auth/me` returns the server-verified `CONTROLLER` role.
4. The first-visit tutorial appears.
5. The six-step guided demo completes.
6. Lift L2 produces the unchanged 530 m Corridor W3 fallback.
7. W3 closure produces the explicit no-route state.
8. No positive route communication is generated during containment.
9. A second human approval remains required.
10. Firestore state survives a Render restart.
