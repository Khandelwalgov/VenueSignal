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

FastAPI lifespan loads and validates the graph before readiness. CORS is allow-listed. The frontend assembles its `/api` base URL exactly once.

## Planned adapters

Firestore repositories, Firebase token verification, and a production Gemini adapter remain planned. These should replace interfaces, not domain rules. Canonical topology must remain separate from Firestore operational records.
