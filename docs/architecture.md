# Architecture

## Implemented local architecture

The Next.js client renders the operational workspace and sends typed requests. FastAPI owns venue loading, validation, mutable operational overlays, routing, workflow state, plan validation, and audit records. Canonical JSON is immutable; mutable state lives in a separate thread-safe in-memory service and every mutation advances `contextVersion`.

The dependency direction is:

`UI → API routes → workflow services → deterministic state/routing → canonical venue`

AI is behind an `AIProvider` protocol. The credential-free local provider produces structured advisory output; domain services validate every identifier and consequential action. The graph, never the SVG or AI, is operational truth.

## State and safety boundaries

- Canonical: levels, zones, nodes, edges, assets, dependencies.
- Operational overlay: statuses, crowd overrides, version, timestamps, event history.
- Evidence: raw reports and unverified extraction, retained with provenance.
- Incident: controller-verified facts, impact, plans, tasks, drafts, audit events.
- Approval boundary: plan proposals create no work until controller approval.
- Reassessment boundary: changed context invalidates the old plan; it is never silently rewritten.
- Recovery boundary: generated plan → structured deterministic validation → at most one Gemini repair → validation → deterministic containment if still invalid. Only the final valid proposal is exposed for approval; invalid attempts remain audit metadata.

FastAPI lifespan loads and validates the graph before readiness. CORS is allow-listed. The frontend assembles its `/api` base URL exactly once.

## Repository and provider adapters

Workflow and operational-state protocols have memory, SQLite, and Firestore implementations. Configuration selects one at startup. The Firestore Admin SDK stores mutable state while canonical topology remains version-controlled JSON. SQLite provides durable single-process local operation.

Authentication supports local development, deterministic tests, and Firebase Admin ID-token verification with controller/viewer claims. AI supports the deterministic local provider and the official Google Gen AI structured-output adapter. External adapters are lazy and credential-dependent, so tests remain isolated.

Plan provenance is part of the domain model: `GEMINI`, `GEMINI_REPAIRED`, `DETERMINISTIC_CONTAINMENT`, or `LOCAL_DETERMINISTIC`. The memory, SQLite, and Firestore repositories serialize the same complete incident model, including recovery records, tasks, drafts, reassessment, and audit events; none depends on a hidden process-only cache beyond the selected repository.

## Production request path

`Firebase client sign-in → bearer ID token → security/rate middleware → Firebase Admin verification → controller/viewer dependency → typed route → domain validation → repository/provider adapter → audit`

Vercel hosts the browser application and Render hosts FastAPI. Render supplies the Gemini key and Firebase Admin credentials, Firestore client rules deny direct access, and production disables OpenAPI UI.
